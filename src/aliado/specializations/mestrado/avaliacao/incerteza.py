"""A incerteza da avaliação: os intervalos em blocos da semente de referência e as diferenças pareadas Denso − AE-LSTM
por ensaio."""

from __future__ import annotations

import hashlib

from aliado.science.deteccao.metricas.incerteza import paired_interval, proportion_interval
from aliado.specializations.mestrado.avaliacao.configuracao import EvaluationConfig

# (métrica, maior é melhor?, objetivo) da comparação pareada por ensaio.
PAIRED = (
    ("alarmes_pre_falha", False, "Menos falsos alarmes"),
    ("especificidade", True, "Menos falsos alarmes"),
    ("detectado", True, "Detecta mais falhas"),
    ("sensibilidade", True, "Detecta mais falhas"),
    ("atraso_ms", False, "Detecta mais rápido"),
)
PAIRED_NAMES = {"alarmes_pre_falha": "Alarmes no pré-falha, por ensaio", "especificidade": "Especificidade por janela",
                "detectado": "Ensaio detectado (1/0)", "sensibilidade": "Sensibilidade por janela",
                "atraso_ms": "Atraso (ms), ensaios detectados pelos dois"}


def _seed(base: int, *parts) -> int:
    return base + int(hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:8], 16) % 1_000_000


def _intervals(run_scores, threshold, prepared, metrics: dict, config: EvaluationConfig, kind: str) -> None:
    """Acrescenta os intervalos em blocos (semente de referência): proporções por janela e médias."""
    options = {"block": config.block, "resamples": config.resamples}
    alarms = metrics["falsos_alarmes"]
    alarms["teste_saudavel"]["fracao_janelas_acima_ic95"] = proportion_interval(
        [values > threshold for values in run_scores["saudavel"]], seed=_seed(config.seed, kind, "teste"), **options)
    alarms["pre_falha"]["fracao_janelas_acima_ic95"] = proportion_interval(
        [run_scores["ensaios"][name][item["pre_teste"]] > threshold for name, item in prepared.faults.items()],
        seed=_seed(config.seed, kind, "pre"), **options)
    for name, item in prepared.faults.items():
        values, result = run_scores["ensaios"][name], metrics["ensaios"][name]
        result["sensibilidade_ic95"] = proportion_interval(
            [values[item["pos_falha"]] > threshold], seed=_seed(config.seed, kind, name, "sens"), **options)
        result["especificidade_ic95"] = proportion_interval(
            [values[item["pre_teste"]] <= threshold], seed=_seed(config.seed, kind, name, "espec"), **options)
    for metric in ("sensibilidade", "especificidade"):
        values = [item[metric] for item in metrics["ensaios"].values()]
        metrics["resumo"][f"{metric}_media_ic95"] = paired_interval(
            values, resamples=config.resamples, seed=_seed(config.seed, kind, metric))["ic95"]


def _differences(dense: dict, lstm: dict, metric: str) -> list[float | None]:
    result = []
    for name, item in dense["ensaios"].items():
        a, b = item[metric], lstm["ensaios"][name][metric]
        result.append(None if a is None or b is None else float(a) - float(b))
    return result
