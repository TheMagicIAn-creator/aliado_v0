"""Os arquivos do preparo: o relatório em JSON e Markdown e os parâmetros da normalização em `.npz`, numa pasta nova;
nunca sobrescreve."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aliado.science.deteccao.particao.blocos import ROLES
from aliado.specializations.mestrado.atributos.variaveis import FEATURES
from aliado.specializations.mestrado.base.ensaios import DATASET_DOI, DATASET_NAME
from aliado.specializations.mestrado.preparo.preparacao import PURGE, PreparedGPVS


def save_normalization(prepared: PreparedGPVS, path: str | Path) -> None:
    """Piso, linhas de base, escala robusta e índices de cada papel, em .npz (sem pickle)."""
    np.savez_compressed(
        path, variaveis=np.asarray(FEATURES), piso_iqr=prepared.iqr_floor,
        escala_centro=prepared.scaler.center, escala_amplitude=prepared.scaler.scale,
        **{f"linha_base_{name}_{key}": value for name, base in prepared.baselines.items()
           for key, value in base.items()},
        **{f"papel_{role}": prepared.split[role] for role in ROLES})


def export_preparation(prepared: PreparedGPVS, summary: dict, output: str | Path) -> dict[str, str]:
    """Relatório JSON/Markdown e parâmetros de normalização em pasta nova; nunca sobrescreve."""
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=False)
    paths = {"json": folder / "relatorio.json", "markdown": folder / "relatorio.md",
             "normalizacao": folder / "normalizacao.npz"}
    paths["json"].write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    save_normalization(prepared, paths["normalizacao"])
    healthy, decorrelation = summary["saudavel"], summary["verificacao_m14_autocorrelacao"]
    lines = [
        "# Preparo do GPVS-Faults — protocolo M14", "",
        f"Conjunto: {DATASET_NAME} (DOI {DATASET_DOI}); 16 ensaios com hashes conferidos.", "",
        "## Divisão das janelas saudáveis", "",
        "| Ensaio | Treino | Validação | Calibração | Teste |", "|---|---:|---:|---:|---:|",
        *[f"| {name} | " + " | ".join(str(counts[role]) for role in ROLES) + " |"
          for name, counts in healthy["papeis_por_ensaio"].items()],
        "| **Total** | " + " | ".join(str(healthy["papeis"][role]) for role in ROLES) + " |", "",
        f"Separação de {summary['parametros']['separacao_janelas']} janelas entre blocos: "
        f"{healthy['descartadas_na_separacao']} janelas descartadas.", "",
        "## Ensaios com falha", "",
        "| Ensaio | Descrição | Modo | Comissionamento | Pré-teste | Transição | Pós-falha |",
        "|---|---|---|---:|---:|---:|---:|",
        *[f"| {name} | {item['descricao']} | {item['modo'].split()[0]} | {item['comissionamento']} | "
          f"{item['pre_teste']} | {item['transicao']} | {item['pos_falha']} |"
          for name, item in summary["falhas"].items()], "",
        "## Verificação do M14: dependência temporal", "",
        f"Critério: |ACF| < {decorrelation['criterio']['limite_abs_acf']} em "
        f"{decorrelation['criterio']['fracao_variaveis']:.0%} das variáveis, no treino escalado.", "",
        "| Ensaio | Lag de descorrelação | ACF mediana (lags 1–5) |", "|---|---:|---|",
        *[f"| {name} | {block['lag_descorrelacao']} | "
          + ", ".join(f"{v:.2f}" for v in block["acf_mediana_por_lag"][:5]) + " |"
          for name, block in decorrelation["blocos"].items()], "",
        f"A separação atual afasta os blocos em {decorrelation['distancia_entre_blocos']} janelas; "
        f"o critério pede {decorrelation['lag_necessario']}. "
        + ("A separação é suficiente." if decorrelation["suficiente"] else
           f"**A separação não é suficiente por este critério.** A separação canônica do GPVS é de "
           f"{PURGE} janelas (decisão de 27/09/2026)."),
        "", "A fronteira de falha é o meio nominal de cada registro: os CSVs não trazem canal de disparo.",
    ]
    paths["markdown"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {key: str(path) for key, path in paths.items()}
