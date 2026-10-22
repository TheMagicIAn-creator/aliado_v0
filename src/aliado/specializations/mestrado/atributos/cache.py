"""O lugar do cache dos 24 atributos de uma base, ao lado dos CSVs. Só a biblioteca padrão: o terminal e o
experimento o usam sem carregar o numpy (lote 51: o caminho era repetido em quatro lugares)."""

from __future__ import annotations

from pathlib import Path


def features_cache(dataset_dir: str | Path) -> Path:
    """O arquivo do cache dos atributos da base em `dataset_dir`."""
    return Path(dataset_dir) / "processado" / "variaveis.npz"
