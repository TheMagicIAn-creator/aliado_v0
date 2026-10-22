"""O resumo auditável do preparo: proveniência, parâmetros, contagens e a verificação da autocorrelação."""

from __future__ import annotations

from aliado.science.deteccao.particao.autocorrelacao import decorrelation_report
from aliado.science.deteccao.particao.blocos import ROLES
from aliado.specializations.mestrado.atributos.variaveis import FEATURES
from aliado.specializations.mestrado.base.ensaios import (
    DATASET_DOI,
    DATASET_NAME,
    FAULTS,
    FAULTY,
    GRID_HZ,
    HEALTHY,
    MODES,
    WINDOW,
)
from aliado.specializations.mestrado.preparo.preparacao import (
    BASELINE_FRACTION,
    BASELINE_MIN_WINDOWS,
    IQR_FLOOR_FRACTION,
    PreparedGPVS,
)


def report(prepared: PreparedGPVS) -> dict:
    """Resumo auditável: proveniência, parâmetros, contagens e verificação de autocorrelação."""
    per_experiment, fractions, purge = prepared.split["por_ensaio"], prepared.fractions, prepared.purge
    decorrelation = decorrelation_report(
        {name: prepared.scaled[per_experiment[name]["train"]] for name in HEALTHY},
        names=FEATURES, purge=purge)
    return {
        "conjunto": {"nome": DATASET_NAME, "doi": DATASET_DOI, "hashes": prepared.hashes},
        "parametros": {
            "fracoes": dict(zip(ROLES, fractions)), "separacao_janelas": purge,
            "janela_amostras": WINDOW, "frequencia_rede_hz": GRID_HZ,
            "comissionamento": {"fracao_pre_falha": BASELINE_FRACTION, "minimo_janelas": BASELINE_MIN_WINDOWS},
            "piso_iqr_fracao": IQR_FLOOR_FRACTION, "variaveis": list(FEATURES),
            "fronteira_falha": "meio nominal do registro; os CSVs não trazem canal de disparo",
        },
        "saudavel": {
            "janelas_por_ensaio": {name: int((prepared.healthy_experiment == name).sum()) for name in HEALTHY},
            "papeis": {role: int(len(prepared.split[role])) for role in ROLES},
            "papeis_por_ensaio": {name: {role: int(len(per_experiment[name][role])) for role in ROLES}
                                  for name in HEALTHY},
            "descartadas_na_separacao": int(len(prepared.healthy_values) - sum(len(prepared.split[r]) for r in ROLES)),
        },
        "falhas": {name: {
            "descricao": FAULTS[int(name[1])][0], "falha_fisica": FAULTS[int(name[1])][1], "modo": MODES[name[2]],
            "comissionamento": int(len(item["comissionamento"])), "pre_teste": int(len(item["pre_teste"])),
            "transicao": int(len(item["transicao"])), "pos_falha": int(len(item["pos_falha"])),
        } for name, item in prepared.faults.items()},
        "total_janelas": {"saudaveis": int(len(prepared.healthy_values)),
                          "com_falha": int(sum(prepared.extraction[name]["janelas"] for name in FAULTY))},
        "verificacao_m14_autocorrelacao": decorrelation,
        "extracao": prepared.extraction,
    }
