"""O experimento AE Denso × AE-LSTM (spec 0034), como o núcleo o lê: os 14 atributos do contrato dos experimentos,
reunidos dos arquivos desta pasta (`declaracao`, `execucao`, `consolidacao` e `apresentacao`). Só a biblioteca padrão
no topo: numpy e PyTorch entram dentro das funções.
"""

from aliado.specializations.mestrado.rodada.apresentacao import report
from aliado.specializations.mestrado.rodada.consolidacao import legacy
from aliado.specializations.mestrado.rodada.declaracao import (
    CONFIRMATION,
    DATASET,
    DATASET_DIR,
    DESCRIPTION,
    DURATION,
    KEY,
    PARAMETERS,
    TITLE,
)
from aliado.specializations.mestrado.rodada.execucao import consultations, interrupted, missing, run

__all__ = ["CONFIRMATION", "DATASET", "DATASET_DIR", "DESCRIPTION", "DURATION", "KEY", "PARAMETERS", "TITLE",
           "consultations", "interrupted", "legacy", "missing", "report", "run"]
