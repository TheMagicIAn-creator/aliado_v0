"""Reanálise do GPVS com o início observado das falhas (lote 24).

Reaproveita os escores gravados na avaliação oficial de 27/09 (`gpvs-avaliacao-001`) e os
limiares do treino, sem rodar os modelos. Os ensaios com mudança clara nos sinais
(`estimativa.estimate`) são rotulados de novo, pela decisão do pesquisador de 30/09/2026:
- a detecção começa no início nominal, como na avaliação oficial;
- o trecho entre o início nominal e a mudança fica fora das métricas por janela;
- as janelas com falha começam na mudança, e o atraso é medido dela, podendo ser negativo.
Os ensaios sem mudança clara ficam no início nominal. As métricas saem das mesmas funções da
avaliação oficial (`avaliacao/decisao.run_metrics` e `avaliacao/resumo.summarize`), sobre uma cópia rotulada
de novo de `PreparedGPVS`. Exige o extra `ml`, como a avaliação.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np

from aliado.science.deteccao.alarmes.taxa import markov_alarm_rate
from aliado.science.deteccao.limiar.calibracao import calibrate_threshold, false_alarm_interval
from aliado.science.deteccao.redes.autoencoders import MODELS
from aliado.specializations.mestrado.atributos import extracao
from aliado.specializations.mestrado.avaliacao.configuracao import EvaluationConfig
from aliado.specializations.mestrado.avaliacao.decisao import run_metrics
from aliado.specializations.mestrado.avaliacao.incerteza import _seed
from aliado.specializations.mestrado.avaliacao.resumo import _grid_row, summarize
from aliado.specializations.mestrado.avaliacao.treino_congelado import (
    TrainedDetectors,
    load_thresholds,
)
from aliado.specializations.mestrado.base import ensaios
from aliado.specializations.mestrado.inicio_das_falhas import estimativa
from aliado.specializations.mestrado.preparo import preparacao
from aliado.specializations.mestrado.preparo.inicio_nominal import nominal_onset
from aliado.specializations.mestrado.reanalise.artefatos import export_reanalysis
from aliado.specializations.mestrado.reanalise.relatorio import _notice

PERCENTILES = (95.0, 97.5, 99.0)


def evaluation_config(folder: str | Path) -> tuple[EvaluationConfig, dict]:
    """A configuração congelada da avaliação de origem, conferida pelo hash."""
    frozen = json.loads((Path(folder) / "configuracao.json").read_text(encoding="utf-8"))
    raw = frozen["avaliacao"]
    config = EvaluationConfig(**(raw | {"confirmation_grid": tuple(raw["confirmation_grid"])}))
    if config.digest() != frozen["sha256"]:
        raise ValueError("A configuração da avaliação não confere com o hash gravado.")
    return config, frozen


def load_scores(path: str | Path, trained: TrainedDetectors) -> dict:
    """Os escores de `escores.npz` no formato de `avaliacao/pontuacao.score_all`."""
    scores = {}
    with np.load(path, allow_pickle=False) as stored:
        for kind in MODELS:
            for seed in trained.config.seeds:
                for k in trained.config.sensitivity_k:
                    prefix = f"{kind}_s{seed}_k{k}_"
                    scores[(kind, seed, int(k))] = {
                        "saudavel": [stored[f"{prefix}saudavel_{name}"] for name in ensaios.HEALTHY],
                        "ensaios": {name: stored[prefix + name] for name in ensaios.FAULTY}}
    return scores


def relabel(prepared: preparacao.PreparedGPVS, trials: dict) -> preparacao.PreparedGPVS:
    """Cópia com os ensaios de mudança clara rotulados pela mudança; os outros ficam como estão.

    O trecho entre os dois inícios vai para `transicao`, que fica fora das métricas por janela, e a
    detecção começa no mais cedo deles. A fronteira passa a ser a mudança, de onde sai o atraso.
    """
    faults, extraction = dict(prepared.faults), {name: dict(meta) for name, meta in prepared.extraction.items()}
    for name, trial in trials.items():
        if trial["classe"] != "clara":
            continue
        item, observed = prepared.faults[name], int(trial["observado_janela"])
        windows = len(item["scaled"])
        start = min(nominal_onset(item), observed)
        pre = item["pre_teste"][item["pre_teste"] < start]
        if not len(pre) or observed >= windows:
            continue
        faults[name] = item | {"pre_teste": pre, "transicao": np.arange(start, observed),
                               "pos_falha": np.arange(observed, windows)}
        extraction[name]["fronteira_falha_amostra"] = observed * ensaios.WINDOW
    return dataclasses.replace(prepared, faults=faults, extraction=extraction)


def _only(prepared: preparacao.PreparedGPVS, names) -> preparacao.PreparedGPVS:
    return dataclasses.replace(prepared, faults={name: prepared.faults[name] for name in names})


def healthy_flags(run_scores: dict, threshold: float, prepared: preparacao.PreparedGPVS) -> list[np.ndarray]:
    """Janelas acima do limiar nos trechos saudáveis: o teste saudável e o pré-teste de cada ensaio."""
    return ([values > threshold for values in run_scores["saudavel"]]
            + [run_scores["ensaios"][name][item["pre_teste"]] > threshold for name, item in prepared.faults.items()])


def _nominal_delays(summary: dict, prepared: preparacao.PreparedGPVS, relabeled: preparacao.PreparedGPVS) -> None:
    """Acrescenta a cada ensaio o atraso desde o início nominal, ao lado do atraso desde a mudança."""
    for item in summary["modelos"].values():
        for name, result in item["referencia"]["ensaios"].items():
            original = prepared.extraction[name]
            shift = (relabeled.extraction[name]["fronteira_falha_amostra"] - original["fronteira_falha_amostra"])
            result["atraso_desde_o_meio_ms"] = (None if result["atraso_ms"] is None else
                                                result["atraso_ms"] + shift / original["fs_hz"] * 1000)


def _analysis(evaluation_dir: str | Path, training_dir: str | Path, gpvs_dir: str | Path, *,
              cache: str | Path | None, onset_config: estimativa.OnsetConfig | None) -> tuple[dict, dict]:
    evaluation_dir, training_dir = Path(evaluation_dir), Path(training_dir)
    trained, training_summary = load_thresholds(training_dir)
    config, frozen = evaluation_config(evaluation_dir)
    if frozen["treino"]["configuracao_sha256"] != trained.frozen["sha256"]:
        raise ValueError("A avaliação de origem não é deste treino.")
    experiments, hashes = extracao.extract_all(gpvs_dir, cache=cache)
    if hashes != trained.frozen["dados"]["hashes"] or hashes != frozen["dados"]["hashes"]:
        raise ValueError("Os dados do GPVS não são os do treino e da avaliação.")
    prepared = preparacao.prepare(gpvs_dir, cache=cache, purge=trained.config.purge, fractions=trained.config.fractions)
    onset_config = onset_config or estimativa.OnsetConfig()
    onsets = estimativa.estimate(experiments, onset_config)
    scores = load_scores(evaluation_dir / "escores.npz", trained)
    relabeled = relabel(prepared, onsets["ensaios"])
    summary = summarize(scores, trained, relabeled, config)
    _nominal_delays(summary, prepared, relabeled)
    clear = [name for name, trial in onsets["ensaios"].items() if trial["classe"] == "clara"]
    subset = summarize(scores, trained, _only(relabeled, clear), config)
    subset_nominal = summarize(scores, trained, _only(prepared, clear), config)
    k, reference = trained.config.top_k, trained.config.reference_seed
    estimates, spread = {}, {}
    for kind in MODELS:
        threshold = trained.thresholds[(kind, reference, k)]
        estimates[kind] = markov_alarm_rate(healthy_flags(scores[(kind, reference, k)], threshold, relabeled),
                                            config.confirmations, resamples=config.resamples,
                                            seed=_seed(config.seed, kind, "markov"),
                                            windows_per_hour=ensaios.WINDOWS_PER_HOUR)
        limit = training_summary["modelos"][kind]["sementes"][str(reference)]["limiar"]
        alarms = summary["modelos"][kind]["referencia"]["falsos_alarmes"]
        spread[kind] = false_alarm_interval(limit["posicao"], limit["n_calibracao"]) | {
            "observado": {part: {"fracao": alarms[part]["fracao_janelas_acima"],
                                 "ic95": alarms[part]["fracao_janelas_acima_ic95"]}
                          for part in ("teste_saudavel", "pre_falha")}}
    summary["sensibilidade"]["percentil"] = _percentile_grid(training_dir, scores, trained, relabeled, config)
    summary["aviso"] = _notice(evaluation_dir, frozen.get("executado_em"))
    runs = {(kind, seed): run_metrics(scores[(kind, seed, k)], trained.thresholds[(kind, seed, k)], relabeled,
                                      config.confirmations)
            for kind in MODELS for seed in trained.config.seeds}
    return summary | {
        "origem": {"avaliacao": evaluation_dir.name, "avaliacao_sha256": frozen["sha256"],
                   "avaliacao_executada_em": frozen.get("executado_em"), "treino": training_dir.name,
                   "treino_configuracao_sha256": trained.frozen["sha256"]},
        "inicio": onsets,
        "regras": {
            "inicio": "mudança observada nos ensaios de mudança clara; início nominal nos demais",
            "trecho_entre_os_inicios": "fora das métricas por janela",
            "deteccao": "primeiro alarme a partir do mais cedo dos dois inícios, como na avaliação de 27/09",
            "atraso": "desde a mudança observada; pode ser negativo",
        },
        "so_mudanca_clara": {"ensaios": clear, **_brief(subset), "meio": _brief(subset_nominal)},
        "alarmes_estimados": estimates,
        "limiar_incerteza": spread,
    }, runs


def _brief(summary: dict) -> dict:
    return {"comparacao": summary["comparacao"],
            "modelos": {kind: {"resumo": item["referencia"]["resumo"], "faixa_sementes": item["faixa_sementes"]}
                        for kind, item in summary["modelos"].items()}}


def reanalyze(evaluation_dir: str | Path, training_dir: str | Path, gpvs_dir: str | Path, *,
              cache: str | Path | None = None, onset_config: estimativa.OnsetConfig | None = None) -> dict:
    """Início observado, métricas com ele (14 ensaios e só os de mudança clara) e as estimativas novas."""
    return _analysis(evaluation_dir, training_dir, gpvs_dir, cache=cache, onset_config=onset_config)[0]


def _percentile_grid(training_dir: Path, scores: dict, trained: TrainedDetectors,
                     prepared: preparacao.PreparedGPVS, config: EvaluationConfig) -> dict:
    """Detecção e alarmes com limiares p95, p97,5 e p99 dos mesmos escores de calibração (só relatada)."""
    k, reference = trained.config.top_k, trained.config.reference_seed
    grid = {}
    with np.load(training_dir / "escores_calibracao.npz", allow_pickle=False) as calibration:
        for percentile in PERCENTILES:
            row = {}
            for kind in MODELS:
                limit = calibrate_threshold(calibration[f"{kind}_s{reference}_k{k}"], percentile, strict=False)
                metrics = run_metrics(scores[(kind, reference, k)], limit.value, prepared, config.confirmations)
                row[kind] = _grid_row(metrics) | {
                    "limiar": limit.value, "posicao": limit.rank, "n_calibracao": limit.n,
                    "sensibilidade_media": metrics["resumo"]["sensibilidade_media"],
                    "especificidade_media": metrics["resumo"]["especificidade_media"],
                    "faixa_esperada_por_janela": false_alarm_interval(limit.rank, limit.n)["ic95"]}
            grid[f"{percentile:g}"] = row
    return grid


def run(evaluation_dir: str | Path, training_dir: str | Path, gpvs_dir: str | Path, output: str | Path, *,
        cache: str | Path | None = None, onset_config: estimativa.OnsetConfig | None = None) -> dict[str, str]:
    """Reanálise completa numa pasta nova, com as métricas por ensaio de todos os treinamentos no CSV."""
    if Path(output).exists():
        raise FileExistsError("A pasta de saída já existe; escolha uma pasta nova.")
    report, runs = _analysis(evaluation_dir, training_dir, gpvs_dir, cache=cache, onset_config=onset_config)
    return export_reanalysis(report, evaluation_dir, output, runs)
