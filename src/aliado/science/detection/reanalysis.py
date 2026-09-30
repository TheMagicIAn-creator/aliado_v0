"""Reanálise do GPVS com o início observado das falhas (lote 24).

Reaproveita os escores gravados na avaliação oficial de 27/09 (`gpvs-avaliacao-001`) e os
limiares do treino, sem rodar os modelos. Os ensaios com mudança clara nos sinais
(`onset.estimate`) são rotulados de novo, pela decisão do pesquisador de 30/09/2026:
- a detecção começa no início nominal, como na avaliação oficial;
- o trecho entre o início nominal e a mudança fica fora das métricas por janela;
- as janelas com falha começam na mudança, e o atraso é medido dela, podendo ser negativo.
Os ensaios sem mudança clara ficam no início nominal. As métricas saem das mesmas funções da
avaliação oficial (`evaluation.run_metrics` e `evaluation.summarize`), sobre uma cópia rotulada
de novo de `PreparedGPVS`. Exige o extra `ml`, como a avaliação.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import date
from pathlib import Path

import numpy as np

from aliado.science.detection import gpvs, onset
from aliado.science.detection.evaluation import (
    PAIRED_NAMES,
    EvaluationConfig,
    TrainedDetectors,
    _csv,
    _grid_row,
    _seed,
    load_thresholds,
    run_metrics,
    summarize,
)
from aliado.science.detection.metrics import markov_alarm_rate
from aliado.science.detection.models import MODEL_NAMES, MODELS
from aliado.science.detection.threshold import calibrate_threshold, false_alarm_interval
from aliado.science.detection.training import environment

EVALUATION = "gpvs-avaliacao-001"
PERCENTILES = (95.0, 97.5, 99.0)
NOTICE = ("Reanálise dos mesmos escores da avaliação de 27/09, sem rodar os modelos de novo. A avaliação de "
          "27/09 continua sendo a oficial.")


def evaluation_config(folder: str | Path) -> tuple[EvaluationConfig, dict]:
    """A configuração congelada da avaliação de origem, conferida pelo hash."""
    frozen = json.loads((Path(folder) / "configuracao.json").read_text(encoding="utf-8"))
    raw = frozen["avaliacao"]
    config = EvaluationConfig(**(raw | {"confirmation_grid": tuple(raw["confirmation_grid"])}))
    if config.digest() != frozen["sha256"]:
        raise ValueError("A configuração da avaliação não confere com o hash gravado.")
    return config, frozen


def load_scores(path: str | Path, trained: TrainedDetectors) -> dict:
    """Os escores de `escores.npz` no formato de `evaluation.score_all`."""
    scores = {}
    with np.load(path, allow_pickle=False) as stored:
        for kind in MODELS:
            for seed in trained.config.seeds:
                for k in trained.config.sensitivity_k:
                    prefix = f"{kind}_s{seed}_k{k}_"
                    scores[(kind, seed, int(k))] = {
                        "saudavel": [stored[f"{prefix}saudavel_{name}"] for name in gpvs.HEALTHY],
                        "ensaios": {name: stored[prefix + name] for name in gpvs.FAULTY}}
    return scores


def _nominal(item: dict) -> int:
    return int(item["transicao"][0]) if len(item["transicao"]) else int(item["pos_falha"][0])


def relabel(prepared: gpvs.PreparedGPVS, trials: dict) -> gpvs.PreparedGPVS:
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
        start = min(_nominal(item), observed)
        pre = item["pre_teste"][item["pre_teste"] < start]
        if not len(pre) or observed >= windows:
            continue
        faults[name] = item | {"pre_teste": pre, "transicao": np.arange(start, observed),
                               "pos_falha": np.arange(observed, windows)}
        extraction[name]["fronteira_falha_amostra"] = observed * gpvs.WINDOW
    return dataclasses.replace(prepared, faults=faults, extraction=extraction)


def _only(prepared: gpvs.PreparedGPVS, names) -> gpvs.PreparedGPVS:
    return dataclasses.replace(prepared, faults={name: prepared.faults[name] for name in names})


def healthy_flags(run_scores: dict, threshold: float, prepared: gpvs.PreparedGPVS) -> list[np.ndarray]:
    """Janelas acima do limiar nos trechos saudáveis: o teste saudável e o pré-teste de cada ensaio."""
    return ([values > threshold for values in run_scores["saudavel"]]
            + [run_scores["ensaios"][name][item["pre_teste"]] > threshold for name, item in prepared.faults.items()])


def _nominal_delays(summary: dict, prepared: gpvs.PreparedGPVS, relabeled: gpvs.PreparedGPVS) -> None:
    """Acrescenta a cada ensaio o atraso desde o início nominal, ao lado do atraso desde a mudança."""
    for item in summary["modelos"].values():
        for name, result in item["referencia"]["ensaios"].items():
            original = prepared.extraction[name]
            shift = (relabeled.extraction[name]["fronteira_falha_amostra"] - original["fronteira_falha_amostra"])
            result["atraso_desde_o_meio_ms"] = (None if result["atraso_ms"] is None else
                                                result["atraso_ms"] + shift / original["fs_hz"] * 1000)


def _analysis(evaluation_dir: str | Path, training_dir: str | Path, gpvs_dir: str | Path, *,
              cache: str | Path | None, onset_config: onset.OnsetConfig | None) -> tuple[dict, dict]:
    evaluation_dir, training_dir = Path(evaluation_dir), Path(training_dir)
    trained, training_summary = load_thresholds(training_dir)
    config, frozen = evaluation_config(evaluation_dir)
    if frozen["treino"]["configuracao_sha256"] != trained.frozen["sha256"]:
        raise ValueError("A avaliação de origem não é deste treino.")
    experiments, hashes = gpvs.extract_all(gpvs_dir, cache=cache)
    if hashes != trained.frozen["dados"]["hashes"] or hashes != frozen["dados"]["hashes"]:
        raise ValueError("Os dados do GPVS não são os do treino e da avaliação.")
    prepared = gpvs.prepare(gpvs_dir, cache=cache, purge=trained.config.purge, fractions=trained.config.fractions)
    onset_config = onset_config or onset.OnsetConfig()
    onsets = onset.estimate(experiments, onset_config)
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
                                            seed=_seed(config.seed, kind, "markov"))
        limit = training_summary["modelos"][kind]["sementes"][str(reference)]["limiar"]
        alarms = summary["modelos"][kind]["referencia"]["falsos_alarmes"]
        spread[kind] = false_alarm_interval(limit["posicao"], limit["n_calibracao"]) | {
            "observado": {part: {"fracao": alarms[part]["fracao_janelas_acima"],
                                 "ic95": alarms[part]["fracao_janelas_acima_ic95"]}
                          for part in ("teste_saudavel", "pre_falha")}}
    summary["sensibilidade"]["percentil"] = _percentile_grid(training_dir, scores, trained, relabeled, config)
    summary["aviso"] = NOTICE
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
              cache: str | Path | None = None, onset_config: onset.OnsetConfig | None = None) -> dict:
    """Início observado, métricas com ele (14 ensaios e só os de mudança clara) e as estimativas novas."""
    return _analysis(evaluation_dir, training_dir, gpvs_dir, cache=cache, onset_config=onset_config)[0]


def _percentile_grid(training_dir: Path, scores: dict, trained: TrainedDetectors,
                     prepared: gpvs.PreparedGPVS, config: EvaluationConfig) -> dict:
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


def _number(value, digits: int = 1) -> str:
    return "—" if value is None else f"{value:.{digits}f}".replace(".", ",")


def _markdown(report: dict, official: dict) -> str:
    trials = report["inicio"]["ensaios"]
    lines = [
        "# Reanálise do GPVS com o início observado das falhas", "",
        f"{NOTICE} Origem: `{report['origem']['avaliacao']}` (avaliação de {report['origem']['avaliacao_executada_em']}) "
        f"e o treino `{report['origem']['treino']}`.", "",
        "## Quando cada falha aparece nos sinais", "",
        "O início nominal é o meio do registro, porque os arquivos não marcam o disparo. A mudança observada é a "
        "primeira mudança na média das 24 variáveis depois do comissionamento, achada pelo PELT (Killick, Fearnhead "
        f"e Eckley, 2012) com penalidade c · 24 · ln n. O c = {report['inicio']['penalidade_c']:g} é o menor da grade "
        "sem mudança nenhuma nos dois ensaios saudáveis. Clara: a mesma mudança em todos os c maiores; fraca: some "
        "com um c maior. Os escores dos detectores não entram.", "",
        "| Ensaio | Falha | Meio (s) | Mudança (s) | Diferença (s) | Classe |", "|---|---|---:|---:|---:|---|",
    ]
    for name, trial in trials.items():
        observed = trial["observado_s"]
        lines.append(f"| {name} | {gpvs.FAULTS[int(name[1])][0]} | {_number(trial['nominal_s'], 2)} | "
                     f"{_number(observed, 2)} | "
                     f"{'—' if observed is None else _number(observed - trial['nominal_s'], 2)} | {trial['classe']} |")
    lines += ["", "Nos ensaios de mudança clara, o trecho entre os dois inícios fica fora das métricas por janela; "
              "a detecção começa no início nominal, e o atraso é medido da mudança. Os demais ficam no meio.", "",
              "## Indicadores com cada início (treino de referência)", "",
              "| Modelo | Indicador | 14 ensaios, meio (27/09) | 14 ensaios, mudança | 8 de mudança clara, meio | "
              "8 de mudança clara, mudança |", "|---|---|---:|---:|---:|---:|"]
    names = {"detectados": ("Ensaios detectados", 0), "atraso_mediano_ms": ("Atraso mediano (ms)", 1),
             "sensibilidade_media": ("Sensibilidade", 3), "especificidade_media": ("Especificidade", 3),
             **{f"{metric}_media": (label, 3) for metric, label in (
                 ("precisao", "Precisão"), ("f1", "F1"), ("mcc", "MCC"), ("auc_roc", "AUC-ROC"), ("auc_pr", "AUC-PR"))}}
    for kind in MODELS:
        before = official["modelos"][kind]["referencia"]["resumo"]
        after = report["modelos"][kind]["referencia"]["resumo"]
        clear = report["so_mudanca_clara"]["modelos"][kind]["resumo"]
        clear_before = report["so_mudanca_clara"]["meio"]["modelos"][kind]["resumo"]
        for key, (label, places) in names.items():
            lines.append(f"| {MODEL_NAMES[kind]} | {label} | {_number(before[key], places)} | "
                         f"{_number(after[key], places)} | {_number(clear_before[key], places)} | "
                         f"{_number(clear[key], places)} |")
    for kind in MODELS:
        lines += ["", f"## Por ensaio — {MODEL_NAMES[kind]}", "",
                  "| Ensaio | Detectado | Atraso desde o meio (ms) | Atraso desde a mudança (ms) | "
                  "Sensibilidade no meio | Sensibilidade com a mudança |", "|---|---|---:|---:|---:|---:|"]
        for name, result in report["modelos"][kind]["referencia"]["ensaios"].items():
            before = official["modelos"][kind]["referencia"]["ensaios"][name]
            lines.append(f"| {name} | {'sim' if result['detectado'] else 'não'} | "
                         f"{_number(result['atraso_desde_o_meio_ms'])} | {_number(result['atraso_ms'])} | "
                         f"{_number(before['sensibilidade'], 3)} | {_number(result['sensibilidade'], 3)} |")
    lines += ["", "## Comparação por objetivo (Denso − AE-LSTM, com a mudança observada)", "",
              "| Objetivo | Métrica | 14 ensaios: diferença [IC 95%] | Leitura | 8 de mudança clara: diferença [IC 95%] | Leitura |",
              "|---|---|---|---|---|---|"]
    for row, clear in zip(report["comparacao"], report["so_mudanca_clara"]["comparacao"]):
        def cell(item):
            if item["media"] is None:
                return "—"
            return f"{_number(item['media'], 3)} [{_number(item['ic95'][0], 3)}; {_number(item['ic95'][1], 3)}]"
        lines.append(f"| {row['objetivo']} | {PAIRED_NAMES[row['metrica']]} | {cell(row)} | {row['leitura']} | {cell(clear)} | "
                     f"{clear['leitura']} |")
    lines += ["", "## Alarmes falsos por hora, estimados", "",
              "Cadeia de Markov de dois estados (abaixo e acima do limiar), ajustada às janelas saudáveis: o teste "
              "saudável e o trecho antes da falha dos 14 ensaios. Abordagem de cadeia de Markov para o tempo até o "
              "alarme (Brook e Evans, 1972); intervalo de 95% sorteando os trechos.", "",
              "| Modelo | Janelas | Acima do limiar | Estimados por hora [IC 95%] | Sequências de 2: previstas / vistas | "
              "Alarmes: previstos / vistos |", "|---|---:|---:|---|---|---|"]
    for kind, item in report["alarmes_estimados"].items():
        lines.append(f"| {MODEL_NAMES[kind]} | {item['janelas']} | {item['janelas_acima']} | "
                     f"{_number(item['alarmes_por_hora'])} [{_number(item['ic95'][0])}; {_number(item['ic95'][1])}] | "
                     f"{_number(item['previsto']['sequencias_de_2'])} / {item['observado']['sequencias_de_2']} | "
                     f"{_number(item['previsto']['alarmes'], 2)} / {item['observado']['alarmes']} |")
    lines += ["", "## Quanto o limiar pode variar", "",
              "Com o limiar na posição r de n escores de calibração, a chance de uma janela saudável nova passar dele "
              "segue uma Beta(n + 1 − r, r) (Vovk, 2012).", "",
              "| Modelo | Posição | Faixa esperada por janela (95%) | Observado no teste saudável | Observado antes da falha |",
              "|---|---|---|---|---|"]
    for kind, item in report["limiar_incerteza"].items():
        seen = item["observado"]
        lines.append(f"| {MODEL_NAMES[kind]} | {item['posicao']} de {item['n']} | "
                     f"{_number(100 * item['ic95'][0], 2)}% a {_number(100 * item['ic95'][1], 2)}% | "
                     f"{_number(100 * seen['teste_saudavel']['fracao'], 2)}% | {_number(100 * seen['pre_falha']['fracao'], 2)}% |")
    lines += ["", "## Limiar em outros percentis (só relatado)", "",
              "| Percentil | Modelo | Posição | Alarmes no teste saudável | Alarmes antes da falha | Detectados | "
              "Atraso mediano (ms) | Sensibilidade |", "|---|---|---|---:|---:|---:|---:|---:|"]
    for percentile, row in report["sensibilidade"]["percentil"].items():
        for kind, item in row.items():
            lines.append(f"| p{percentile.replace('.', ',')} | {MODEL_NAMES[kind]} | {item['posicao']} de {item['n_calibracao']} | "
                         f"{item['alarmes_teste_saudavel']} | {item['alarmes_pre_falha']} | {item['detectados']} | "
                         f"{_number(item['atraso_mediano_ms'])} | {_number(item['sensibilidade_media'], 3)} |")
    lines += ["", "## Limites", "",
              "- A mudança observada é onde a falha aparece nas variáveis, não o instante do disparo, que os arquivos "
              "não registram. A resolução é de uma janela (20 ms).",
              "- A mudança e os detectores olham as mesmas 24 variáveis. Uma sensibilidade alta nos ensaios de mudança "
              "clara mostra que, quando a falha aparece nas variáveis, os modelos a veem logo; ela não mede a "
              "capacidade de ver falhas que não mudam as variáveis.",
              "- F4 não muda as variáveis, e F6 e F7 mudam pouco: para eles, nenhum início é confiável, e a falta de "
              "detecção é, em boa parte, dos dados e das variáveis.",
              "- A estimativa de alarmes por hora supõe que as janelas saudáveis se encadeiam como uma cadeia de Markov "
              "e que 52 s representam a operação normal."]
    return "\n".join(lines) + "\n"


def export_reanalysis(report: dict, evaluation_dir: str | Path, output: str | Path,
                      runs: dict | None = None) -> dict[str, str]:
    """Configuração, inícios, relatório e métricas por ensaio numa pasta nova; nunca sobrescreve."""
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=False)
    paths = {"configuracao": folder / "configuracao.json", "inicio": folder / "inicio.json",
             "relatorio_json": folder / "relatorio.json", "relatorio_md": folder / "relatorio.md"}
    frozen = {"inicio": report["inicio"]["configuracao"], "sha256": report["inicio"]["configuracao_sha256"],
              "executado_em": date.today().isoformat(), "origem": report["origem"], "regras": report["regras"],
              "ambiente": environment()}
    paths["configuracao"].write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths["inicio"].write_text(json.dumps(report["inicio"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths["relatorio_json"].write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                                       encoding="utf-8")
    official = json.loads((Path(evaluation_dir) / "relatorio.json").read_text(encoding="utf-8"))
    paths["relatorio_md"].write_text(_markdown(report, official), encoding="utf-8")
    if runs is not None:
        paths["metricas"] = folder / "metricas_por_ensaio.csv"
        paths["metricas"].write_text(_csv(runs), encoding="utf-8")
    return {key: str(path) for key, path in paths.items()}


def run(evaluation_dir: str | Path, training_dir: str | Path, gpvs_dir: str | Path, output: str | Path, *,
        cache: str | Path | None = None, onset_config: onset.OnsetConfig | None = None) -> dict[str, str]:
    """Reanálise completa numa pasta nova, com as métricas por ensaio de todos os treinamentos no CSV."""
    if Path(output).exists():
        raise FileExistsError("A pasta de saída já existe; escolha uma pasta nova.")
    report, runs = _analysis(evaluation_dir, training_dir, gpvs_dir, cache=cache, onset_config=onset_config)
    return export_reanalysis(report, evaluation_dir, output, runs)
