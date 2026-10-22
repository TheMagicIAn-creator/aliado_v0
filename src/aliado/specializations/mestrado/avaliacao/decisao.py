"""A decisão: os alarmes falsos no teste saudável e no pré-falha, a detecção de cada falha a partir do início nominal
e as métricas por janela, numa semente e num k."""

from __future__ import annotations

import statistics

import numpy as np

from aliado.science.deteccao.alarmes.confirmacao import alarm_starts, first_alarm
from aliado.science.deteccao.metricas.incerteza import poisson_upper
from aliado.science.deteccao.metricas.por_janela import window_metrics
from aliado.specializations.mestrado.base import ensaios
from aliado.specializations.mestrado.preparo import preparacao
from aliado.specializations.mestrado.preparo.inicio_nominal import nominal_onset

SECONDS_PER_HOUR = 3600
SECONDARY = ("precisao", "f1", "acuracia_balanceada", "mcc", "auc_roc", "auc_pr")


def _false_alarms(segments, confirmations: int) -> dict:
    windows = sum(len(segment) for segment in segments)
    above = sum(int(np.sum(segment)) for segment in segments)
    alarms = sum(len(alarm_starts(segment, confirmations)) for segment in segments)
    duration = windows / ensaios.GRID_HZ
    return {"janelas": windows, "janelas_acima": above, "fracao_janelas_acima": above / windows,
            "alarmes": alarms, "duracao_s": duration, "alarmes_por_hora": alarms / duration * SECONDS_PER_HOUR,
            "limite_superior_por_hora": poisson_upper(alarms) / duration * SECONDS_PER_HOUR}


def run_metrics(run_scores: dict, threshold: float, prepared: preparacao.PreparedGPVS, confirmations: int) -> dict:
    """Falsos alarmes, detecção e métricas por janela de um modelo, numa semente e num k."""
    healthy = [values > threshold for values in run_scores["saudavel"]]
    experiments, pre_segments = {}, []
    for name, item in prepared.faults.items():
        values = run_scores["ensaios"][name]
        above = values > threshold
        pre = above[item["pre_teste"]]
        pre_segments.append(pre)
        onset = nominal_onset(item)
        alarm = first_alarm(above[onset:], confirmations)
        meta = prepared.extraction[name]
        delay = None
        if alarm is not None:
            # Do início nominal da falha ao fim da janela que completa a confirmação.
            delay = ((onset + alarm + 1) * ensaios.WINDOW - meta["fronteira_falha_amostra"]) / meta["fs_hz"] * 1000
        experiments[name] = {
            "detectado": alarm is not None, "atraso_ms": delay, "atraso_janelas": None if alarm is None else alarm + 1,
            "alarmes_pre_falha": int(len(alarm_starts(pre, confirmations))), "janelas_pre_falha": int(len(pre)),
            **window_metrics(values[item["pre_teste"]], values[item["pos_falha"]], threshold),
        }
    test, pre_total = _false_alarms(healthy, confirmations), _false_alarms(pre_segments, confirmations)
    total_alarms, total_duration = test["alarmes"] + pre_total["alarmes"], test["duracao_s"] + pre_total["duracao_s"]
    delays = [item["atraso_ms"] for item in experiments.values() if item["detectado"]]
    summary = {
        "detectados": sum(item["detectado"] for item in experiments.values()),
        "atraso_mediano_ms": statistics.median(delays) if delays else None,
        "sensibilidade_media": float(np.mean([item["sensibilidade"] for item in experiments.values()])),
        "especificidade_media": float(np.mean([item["especificidade"] for item in experiments.values()])),
    }
    for metric in SECONDARY:
        values = [item[metric] for item in experiments.values() if item[metric] is not None]
        summary[f"{metric}_media"] = float(np.mean(values)) if values else None
    return {
        "falsos_alarmes": {
            "teste_saudavel": test, "pre_falha": pre_total,
            "combinado": {"alarmes": total_alarms, "duracao_s": total_duration,
                          "limite_superior_por_hora": poisson_upper(total_alarms) / total_duration * SECONDS_PER_HOUR},
        },
        "ensaios": experiments,
        "resumo": summary,
    }
