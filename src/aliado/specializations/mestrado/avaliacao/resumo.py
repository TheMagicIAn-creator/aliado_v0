"""Avaliação M13 do GPVS (lote 15): a abertura do teste saudável e dos ensaios com falha.

Carrega uma rodada de treino congelada (lote 14) conferindo os hashes, prepara os dados com a
mesma divisão e pontua uma vez, com a configuração de avaliação também congelada. Detectar
não altera S/O/D, NPR nem taxas de falha (M09). Exige o extra `ml`.
"""

from __future__ import annotations

import numpy as np

from aliado.science.deteccao.metricas.incerteza import (
    paired_interval,
    verdict,
)
from aliado.science.deteccao.redes.autoencoders import MODEL_NAMES, MODELS
from aliado.specializations.mestrado.avaliacao.configuracao import EvaluationConfig
from aliado.specializations.mestrado.avaliacao.decisao import run_metrics
from aliado.specializations.mestrado.avaliacao.incerteza import (
    PAIRED,
    _differences,
    _intervals,
    _seed,
)
from aliado.specializations.mestrado.avaliacao.treino_congelado import TrainedDetectors
from aliado.specializations.mestrado.preparo import preparacao


def summarize(scores: dict, trained: TrainedDetectors, prepared: preparacao.PreparedGPVS, config: EvaluationConfig) -> dict:
    experiment = trained.config
    k, reference = experiment.top_k, experiment.reference_seed
    runs = {(kind, seed): run_metrics(scores[(kind, seed, k)], trained.thresholds[(kind, seed, k)], prepared,
                                      config.confirmations)
            for kind in MODELS for seed in experiment.seeds}
    for kind in MODELS:
        _intervals(scores[(kind, reference, k)], trained.thresholds[(kind, reference, k)], prepared,
                   runs[(kind, reference)], config, kind)
    models = {}
    for kind in MODELS:
        own = [runs[(kind, seed)] for seed in experiment.seeds]
        spread = {key: [min(values), max(values)] for key in own[0]["resumo"]
                  if not key.endswith("_ic95") and None not in (values := [run["resumo"][key] for run in own])}
        spread["alarmes_teste_saudavel"] = [min(r["falsos_alarmes"]["teste_saudavel"]["alarmes"] for r in own),
                                            max(r["falsos_alarmes"]["teste_saudavel"]["alarmes"] for r in own)]
        spread["alarmes_pre_falha"] = [min(r["falsos_alarmes"]["pre_falha"]["alarmes"] for r in own),
                                       max(r["falsos_alarmes"]["pre_falha"]["alarmes"] for r in own)]
        models[kind] = {"nome": MODEL_NAMES[kind], "limiar": trained.thresholds[(kind, reference, k)],
                        "referencia": runs[(kind, reference)], "faixa_sementes": spread,
                        "sementes": {str(seed): {"resumo": runs[(kind, seed)]["resumo"],
                                                 "alarmes_teste_saudavel": runs[(kind, seed)]["falsos_alarmes"]["teste_saudavel"]["alarmes"],
                                                 "alarmes_pre_falha": runs[(kind, seed)]["falsos_alarmes"]["pre_falha"]["alarmes"]}
                                     for seed in experiment.seeds}}
    comparison = []
    for metric, higher, objective in PAIRED:
        differences = _differences(runs[("denso", reference)], runs[("lstm", reference)], metric)
        result = paired_interval(differences, resamples=config.resamples, seed=_seed(config.seed, "pareado", metric))
        signs = []
        for seed in experiment.seeds:
            values = [d for d in _differences(runs[("denso", seed)], runs[("lstm", seed)], metric) if d is not None]
            signs.append(float(np.sign(np.mean(values))) if values else None)
        reference_sign = signs[experiment.seeds.index(reference)]
        comparison.append({"objetivo": objective, "metrica": metric, "maior_e_melhor": higher, **result,
                           "mesmo_sinal_sementes": sum(sign == reference_sign for sign in signs if sign is not None),
                           "sementes": len(signs), "leitura": verdict(result["ic95"], higher_is_better=higher)})
    grids = {"confirmacao": {}, "k": {}}
    for m in config.confirmation_grid:
        grids["confirmacao"][str(m)] = {kind: _grid_row(run_metrics(scores[(kind, reference, k)],
                                                                    trained.thresholds[(kind, reference, k)], prepared, m))
                                        for kind in MODELS}
    for kk in experiment.sensitivity_k:
        grids["k"][str(kk)] = {kind: _grid_row(run_metrics(scores[(kind, reference, kk)],
                                                           trained.thresholds[(kind, reference, kk)], prepared,
                                                           config.confirmations))
                               for kind in MODELS}
    return {
        "configuracao_sha256": config.digest(),
        "treino_configuracao_sha256": trained.frozen["sha256"],
        "semente_referencia": reference, "top_k": k, "confirmacao": config.confirmations,
        "modelos": models, "comparacao": comparison, "sensibilidade": grids,
        "aviso": "Teste saudável e ensaios com falha consultados; mudanças posteriores exigem avaliação independente (M14).",
    }


def _grid_row(metrics: dict) -> dict:
    alarms = metrics["falsos_alarmes"]
    return {"alarmes_teste_saudavel": alarms["teste_saudavel"]["alarmes"], "alarmes_pre_falha": alarms["pre_falha"]["alarmes"],
            "detectados": metrics["resumo"]["detectados"], "atraso_mediano_ms": metrics["resumo"]["atraso_mediano_ms"]}
