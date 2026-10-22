"""Os arquivos da avaliação: a configuração congelada, os escores, a matriz de erros por variável (lote 54), as métricas
por ensaio e o relatório, numa pasta nova; nunca sobrescreve."""

from __future__ import annotations

import csv
import io
import json
from datetime import date
from pathlib import Path

import numpy as np

from aliado.science.deteccao.escore.top_k import top_k_scores
from aliado.science.deteccao.redes.autoencoders import MODELS
from aliado.science.identidade.contrato import (
    CONTRACT,
    ContractViolationError,
    check_version,
    require,
)
from aliado.specializations.mestrado.atributos import variaveis
from aliado.specializations.mestrado.avaliacao.configuracao import EvaluationConfig
from aliado.specializations.mestrado.avaliacao.decisao import SECONDARY, run_metrics
from aliado.specializations.mestrado.avaliacao.pontuacao import errors_all
from aliado.specializations.mestrado.avaliacao.relatorio import _markdown
from aliado.specializations.mestrado.avaliacao.resumo import summarize
from aliado.specializations.mestrado.avaliacao.treino_congelado import (
    TrainedDetectors,
    weight_hashes,
)
from aliado.specializations.mestrado.base import ensaios
from aliado.specializations.mestrado.preparo import preparacao
from aliado.specializations.mestrado.treino.artefatos import environment

ERRORS = "erros.npz"
ERROR_FIELDS = ("contrato", "variaveis", "pesos", "treino", "avaliacao", "dados", "janela", "trechos")
# A convenção de tempo, gravada com a matriz para ninguém precisar supô-la.
WINDOW = {"amostras": ensaios.WINDOW,
          "data": "a primeira amostra da janela",
          "alarme": "o fim da janela que completa a confirmação",
          "amostra_inicial": f"a janela i de um ensaio começa na amostra i × {ensaios.WINDOW} do CSV, contada de 0"}


def _segments(prepared: preparacao.PreparedGPVS) -> dict[str, list[dict]]:
    """De onde vem cada linha das matrizes: trechos contíguos de janelas de um ensaio, de `inicio` até antes de `fim`."""
    def local(name: str, block) -> dict:
        block = np.asarray(block)
        if np.any(np.diff(block) != 1):
            raise ContractViolationError(f"{ERRORS}: o trecho de {name} não é contíguo.")
        first = int(np.flatnonzero(prepared.healthy_experiment == name)[0])
        return {"ensaio": name, "inicio": int(block[0]) - first, "fim": int(block[-1]) + 1 - first}

    per = prepared.split["por_ensaio"]
    return ({"calibracao": [local(name, per[name]["calibration"]) for name in ensaios.HEALTHY]}
            | {f"saudavel_{name}": [local(name, per[name]["test"])] for name in ensaios.HEALTHY}
            | {name: [{"ensaio": name, "inicio": 0, "fim": len(item["scaled"])}] for name, item in prepared.faults.items()})


def _check_scores(errors: dict, scores: dict, trained: TrainedDetectors) -> None:
    """Os k maiores de cada matriz dão, bit a bit, os escores: os da avaliação e os da calibração gravados no treino."""
    with np.load(trained.folder / "escores_calibracao.npz") as stored:
        calibration = {name: stored[name] for name in stored.files}
    for (kind, seed, k), values in scores.items():
        key = f"{kind}_s{seed}"
        pairs = [(f"{key}_calibracao", calibration[f"{key}_k{k}"]),
                 *[(f"{key}_saudavel_{name}", block) for name, block in zip(ensaios.HEALTHY, values["saudavel"])],
                 *[(f"{key}_{name}", array) for name, array in values["ensaios"].items()]]
        for name, expected in pairs:
            got = top_k_scores(errors[name], k)
            if got.dtype != expected.dtype or got.shape != expected.shape or got.tobytes() != expected.tobytes():
                raise ContractViolationError(f"{ERRORS}: os {k} maiores erros de {name} não dão os escores gravados.")


def load_errors(path: str | Path) -> tuple[dict, dict[str, np.ndarray]]:
    """A matriz de erros gravada, conferida campo a campo e formato a formato: nada é suposto nem recalculado."""
    where = Path(path).name
    with np.load(path) as saved:
        arrays = {name: saved[name] for name in saved.files}
    try:
        meta = json.loads(str(arrays.pop("meta")))
    except (KeyError, ValueError) as exc:
        raise ContractViolationError(f"{where}: faltam os metadados.") from exc
    if not isinstance(meta, dict) or check_version(meta, where) is None:
        raise ContractViolationError(f"{where}: falta a versão do contrato.")
    require(meta, ERROR_FIELDS, where)
    if meta["variaveis"] != list(variaveis.FEATURES) or meta["janela"] != WINDOW:
        raise ContractViolationError(f"{where}: as variáveis ou a convenção da janela não são as do protocolo.")
    try:
        rows = {f"{model}_{group}": sum(part["fim"] - part["inicio"] for part in parts)
                for model in meta["pesos"] for group, parts in meta["trechos"].items()}
    except (AttributeError, KeyError, TypeError) as exc:
        raise ContractViolationError(f"{where}: os pesos ou os trechos estão fora do formato.") from exc
    if set(arrays) != set(rows):
        raise ContractViolationError(f"{where}: as matrizes gravadas não são as dos metadados.")
    wrong = sorted(name for name, count in rows.items()
                   if arrays[name].dtype != np.float32 or arrays[name].shape != (count, len(variaveis.FEATURES)))
    if wrong:
        raise ContractViolationError(f"{where}: formato inesperado em {', '.join(wrong)}.")
    return meta, arrays


def _csv(runs_by_seed: dict) -> str:
    stream = io.StringIO()
    fields = ["modelo", "semente", "ensaio", "detectado", "atraso_ms", "atraso_janelas", "alarmes_pre_falha",
              "janelas_pre_falha", "sensibilidade", "especificidade", *SECONDARY, "vp", "fn", "fp", "vn"]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for (kind, seed), metrics in runs_by_seed.items():
        for name, result in metrics["ensaios"].items():
            writer.writerow({"modelo": kind, "semente": seed, "ensaio": name, **result})
    return stream.getvalue()


def export_evaluation(scores: dict, trained: TrainedDetectors, prepared: preparacao.PreparedGPVS,
                      config: EvaluationConfig, output: str | Path) -> dict[str, str]:
    """Configuração congelada, escores, matriz de erros, métricas por ensaio e relatório numa pasta nova."""
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=False)
    # A matriz é recalculada aqui, à parte dos escores: a conferência bit a bit vale pelas duas contas.
    errors = errors_all(trained, prepared)
    _check_scores(errors, scores, trained)
    run_date = date.today().isoformat()
    summary = summarize(scores, trained, prepared, config)
    paths = {"configuracao": folder / "configuracao.json", "relatorio_json": folder / "relatorio.json",
             "relatorio_md": folder / "relatorio.md", "metricas": folder / "metricas_por_ensaio.csv",
             "escores": folder / "escores.npz", "erros": folder / ERRORS}
    frozen = {"avaliacao": config.as_dict(), "sha256": config.digest(), "executado_em": run_date,
              "treino": {"pasta": trained.folder.as_posix(), "configuracao_sha256": trained.frozen["sha256"]},
              "dados": {"conjunto": ensaios.DATASET_NAME, "doi": ensaios.DATASET_DOI, "hashes": prepared.hashes},
              "ambiente": environment()}
    paths["configuracao"].write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    arrays = {}
    for (kind, seed, k), values in scores.items():
        arrays |= {f"{kind}_s{seed}_k{k}_saudavel_{name}": block for name, block in zip(ensaios.HEALTHY, values["saudavel"])}
        arrays |= {f"{kind}_s{seed}_k{k}_{name}": array for name, array in values["ensaios"].items()}
    np.savez_compressed(paths["escores"], **arrays)
    meta = {"contrato": CONTRACT, "variaveis": list(variaveis.FEATURES), "pesos": weight_hashes(trained),
            "treino": trained.frozen["sha256"], "avaliacao": config.digest(), "dados": prepared.hashes,
            "janela": WINDOW, "trechos": _segments(prepared)}
    np.savez_compressed(paths["erros"], meta=np.array(json.dumps(meta)), **errors)
    k = trained.config.top_k
    runs = {(kind, seed): run_metrics(scores[(kind, seed, k)], trained.thresholds[(kind, seed, k)], prepared,
                                      config.confirmations)
            for kind in MODELS for seed in trained.config.seeds}
    paths["metricas"].write_text(_csv(runs), encoding="utf-8")
    paths["relatorio_json"].write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                                       encoding="utf-8")
    paths["relatorio_md"].write_text(_markdown(summary, trained, config, run_date), encoding="utf-8")
    return {key: str(path) for key, path in paths.items()}
