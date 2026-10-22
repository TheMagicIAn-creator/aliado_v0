"""O resumo do treino: os limiares, as épocas, a autocorrelação dos escores e a estabilidade entre as repetições."""

from __future__ import annotations

import numpy as np

from aliado.science.deteccao.limiar.calibracao import effective_sample_size
from aliado.science.deteccao.redes.autoencoders import MODEL_NAMES, MODELS, parameter_count
from aliado.specializations.mestrado.base import ensaios
from aliado.specializations.mestrado.preparo import preparacao
from aliado.specializations.mestrado.preparo import resumo as resumo_do_preparo
from aliado.specializations.mestrado.treino.configuracao import ExperimentConfig
from aliado.specializations.mestrado.treino.detectores import Run

SECONDS_PER_HOUR = 3600


def summarize(runs: list[Run], prepared: preparacao.PreparedGPVS, config: ExperimentConfig, files: dict) -> dict:
    preparation = resumo_do_preparo.report(prepared)
    decorrelation = preparation["verificacao_m14_autocorrelacao"]
    n_calibration = sum(runs[0].block_sizes)
    per_second = ensaios.GRID_HZ  # uma janela por ciclo de rede
    models = {}
    for kind in MODELS:
        own = [run for run in runs if run.kind == kind]
        seeds = {}
        for run in own:
            principal = run.thresholds[config.top_k]
            blocks = np.split(run.scores[config.top_k], np.cumsum(run.block_sizes)[:-1])
            dependence = effective_sample_size(blocks)
            for name, item in zip(ensaios.HEALTHY, dependence["blocos"]):
                item["ensaio"] = name
            seeds[str(run.seed)] = {
                "melhor_epoca": run.history.best_epoch,
                "epocas_executadas": run.history.epochs,
                "parada": run.history.stop_reason(config.hyperparameters.patience),
                "perda_validacao_minima": run.history.best_validation_loss,
                "limiar": principal.as_dict() | {"falso_alarme_esperado_por_hora":
                                                 principal.expected_false_alarm * per_second * SECONDS_PER_HOUR},
                "sensibilidade_k": {str(k): run.thresholds[k].value for k in config.sensitivity_k},
                "autocorrelacao_escores": dependence,
                "arquivos": files[f"{kind}-s{run.seed}"],
            }
        values = [run.thresholds[config.top_k].value for run in own]
        epochs = [run.history.best_epoch for run in own]
        models[kind] = {
            "nome": MODEL_NAMES[kind], "parametros": parameter_count(own[0].model), "sementes": seeds,
            "estabilidade": {"limiar_min": min(values), "limiar_mediana": float(np.median(values)),
                             "limiar_max": max(values), "melhor_epoca_min": min(epochs),
                             "melhor_epoca_max": max(epochs)},
        }
    return {
        "configuracao_sha256": config.digest(),
        "semente_referencia": config.reference_seed,
        "protocolo": {
            "separacao_janelas": prepared.purge,
            "papeis": preparation["saudavel"]["papeis"],
            "papeis_por_ensaio": preparation["saudavel"]["papeis_por_ensaio"],
            "verificacao_m14": {"lag_necessario": decorrelation["lag_necessario"],
                                "distancia_entre_blocos": decorrelation["distancia_entre_blocos"],
                                "suficiente": decorrelation["suficiente"]},
        },
        "calibracao": {"janelas": n_calibration, "janelas_por_segundo": per_second,
                       "duracao_s": n_calibration / per_second},
        "modelos": models,
        "fechado_ate_o_lote_15": "Teste saudável e ensaios com falha não foram pontuados neste lote.",
    }
