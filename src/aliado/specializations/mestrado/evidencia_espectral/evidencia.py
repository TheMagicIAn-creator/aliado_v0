"""A evidência espectral do primeiro alarme: na janela em que cada modelo confirmou o alarme, a fase com o maior erro de
reconstrução e os indicadores de Fourier dela, ao lado do comissionamento do próprio ensaio; e a tabela do que muda em
cada ensaio. A janela do alarme é a da aba Ciência (`alarme_deteccao`), dos escores salvos com o início nominal."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np

from aliado.science.deteccao.escore.top_k import top_k_scores
from aliado.science.identidade.contrato import ContractViolationError
from aliado.specializations.mestrado.atributos.variaveis import FEATURES
from aliado.specializations.mestrado.base.ensaios import FAULTY
from aliado.specializations.mestrado.evidencia_espectral.espectros import PHASES, load_spectra
from aliado.specializations.mestrado.evidencia_espectral.tabela import (
    INDICATORS,
    changes,
    phase_indicators,
    strongest,
)
from aliado.specializations.mestrado.preparo.inicio_nominal import nominal_onset

VERSION = 1
MODELS = ("denso", "lstm")
# Os 12 erros próprios das fases: o RMS e a THD de cada uma.
PHASE_FEATURES = tuple(FEATURES.index(f"{phase}_{kind}") for phase in PHASES for kind in ("rms", "thd"))


def _check_scores(errors: dict, scores_path: Path, seed: int, k: int) -> None:
    """Os k maiores da matriz dão, bit a bit, os escores salvos do treino de referência em cada ensaio com falha."""
    with np.load(scores_path) as scores:
        for kind in MODELS:
            for name in FAULTY:
                got, saved = top_k_scores(errors[f"{kind}_s{seed}_{name}"], k), scores[f"{kind}_s{seed}_k{k}_{name}"]
                if (got.dtype, got.shape, got.tobytes()) != (saved.dtype, saved.shape, saved.tobytes()):
                    raise ContractViolationError(f"A matriz de erros de {kind} em {name} não dá os escores salvos.")


def _at_alarm(matrix: np.ndarray, window: int, spectra: dict, prepared, name: str) -> dict:
    """A fase do maior dos 12 erros próprios das fases e os indicadores dela na janela e no comissionamento."""
    row = matrix[window]
    chosen = max(PHASE_FEATURES, key=lambda index: row[index])
    phase = FEATURES[chosen].split("_")[0]
    values = phase_indicators(spectra, prepared, name, phase)
    commissioning = prepared.faults[name]["comissionamento"]
    return {"alarme": int(window), "fase": phase, "atributo_da_fase": FEATURES[chosen],
            "posicao_da_fase": int((row > row[chosen]).sum()) + 1, "maior_atributo": FEATURES[int(np.argmax(row))],
            "indicadores": dict(zip(INDICATORS, map(float, values[window]))),
            "comissionamento": dict(zip(INDICATORS, map(float, np.median(values[commissioning], axis=0)))),
            "passo_irregular": bool(spectra[name]["irregular"][window])}


def build(run, gpvs_dir: str | Path, prepared, errors: dict, *, origin: str) -> dict:
    """A evidência de uma rodada. `errors` é a matriz de erros por variável (`denso_s42_F1L`…), a de `erros.npz` ou a do
    explorador, conferida contra os escores salvos; `origin` diz se ela é da própria rodada ou exploração pós-teste."""
    from aliado.specializations.mestrado.resultados import paineis

    report = json.loads((run.evaluation / "relatorio.json").read_text(encoding="utf-8"))
    seed, k = report["semente_referencia"], report["top_k"]
    _check_scores(errors, run.evaluation / "escores.npz", seed, k)
    spectra = load_spectra(gpvs_dir)
    panels = {panel["id"]: panel["modelos"] for panel in paineis.score_panels(run, gpvs_dir)["ensaios"]}
    alarms = {kind: {name: {"alarme": None} if panels[name][kind]["alarme_deteccao"] is None else
                     _at_alarm(errors[f"{kind}_s{seed}_{name}"], panels[name][kind]["alarme_deteccao"], spectra, prepared,
                               name)
                     for name in FAULTY} for kind in MODELS}
    onsets = (paineis.reanalysis(run) or {}).get("inicio", {}).get("ensaios", {})
    late = {name: (onsets[name]["observado_janela"] - nominal_onset(prepared.faults[name])
                   if onsets.get(name, {}).get("classe") == "clara" else None) for name in FAULTY}
    table = changes(spectra, prepared)
    return {"versao": VERSION, "origem": origin, "executado_em": date.today().isoformat(), "rodada": run.id,
            "avaliacao": run.evaluation.name, "treino_de_referencia": seed, "k": k, "confirmacoes": report["confirmacao"],
            "alarmes": alarms, "mais_mudam": strongest(table), "janelas_antes_da_mudanca": late, "tabela": table}
