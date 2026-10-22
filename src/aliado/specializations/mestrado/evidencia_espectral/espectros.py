"""Os espectros das 6 fases de cada janela dos 14 ensaios com falha: o nível médio, as 5 primeiras harmônicas e a THD,
com janela retangular (a janela é um ciclo de 50 Hz). Ficam num cache ao lado dos CSVs, que só vale com os mesmos
arquivos (pelos hashes), e são conferidos contra os atributos ao serem montados."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aliado.science.espectro.decomposicao import harmonics, thd
from aliado.specializations.mestrado.atributos.cache import features_cache
from aliado.specializations.mestrado.atributos.extracao import extract_all
from aliado.specializations.mestrado.atributos.variaveis import FEATURES, PRIMARY_COLUMNS
from aliado.specializations.mestrado.base.ensaios import FAULTY, SOURCE_COLUMNS, WINDOW
from aliado.specializations.mestrado.base.leitura import dataset_files, load_csv, verify_provenance

VERSION = 1
PHASES = ("ia", "ib", "ic", "va", "vb", "vc")
COLUMNS = ("a0", "c1", "c2", "c3", "c4", "c5", "thd")
# Um passo de tempo a mais de 1% da mediana. Na base real são de 5 a 8 por ensaio, isolados, cada um numa janela.
IRREGULAR = 0.01


def spectra_cache(dataset_dir: str | Path) -> Path:
    return Path(dataset_dir) / "processado" / "espectro.npz"


def _trial(data: np.ndarray) -> tuple[dict, np.ndarray, np.ndarray]:
    primary = data[:, [SOURCE_COLUMNS.index(column) for column in PRIMARY_COLUMNS]]
    starts = np.arange(len(data) // WINDOW) * WINDOW
    rows = {phase: [] for phase in PHASES}
    for start in starts:
        matrix = np.asarray(primary[start:start + WINDOW], dtype=np.float64)  # as mesmas operações dos atributos
        for phase in PHASES:
            column = matrix[:, PRIMARY_COLUMNS.index(phase)]
            a0, amplitudes = harmonics(column)
            rows[phase].append([a0, *amplitudes[:5], thd(column)])
    steps = np.diff(data[:, 0])
    off = np.abs(steps / np.median(steps) - 1) > IRREGULAR
    irregular = np.array([bool(off[start:start + WINDOW - 1].any()) for start in starts])
    return {phase: np.asarray(values) for phase, values in rows.items()}, starts, irregular


def load_spectra(dataset_dir: str | Path) -> dict[str, dict]:
    """{ensaio: {"fases": {fase: (janelas, a0 C1…C5 THD)}, "inicio": amostra inicial, "irregular": marca}}.

    Na primeira vez, lê os CSVs, confere que o início de cada janela e a THD em float32 são os dos atributos e grava o
    cache de forma atômica."""
    dataset_dir = Path(dataset_dir)
    hashes = verify_provenance(dataset_dir)
    path = spectra_cache(dataset_dir)
    meta = {"versao": VERSION, "hashes": hashes, "colunas": list(COLUMNS), "limite_irregular": IRREGULAR}
    if path.is_file():
        with np.load(path) as stored:
            if json.loads(str(stored["meta"])) == meta:
                return {name: {"fases": {phase: stored[f"{name}_{phase}"] for phase in PHASES},
                               "inicio": stored[f"{name}_inicio"], "irregular": stored[f"{name}_irregular"]}
                        for name in FAULTY}
    features, _ = extract_all(dataset_dir, cache=features_cache(dataset_dir))
    files = dataset_files(dataset_dir)
    spectra = {}
    for name in FAULTY:
        phases, starts, irregular = _trial(load_csv(files[name]))
        item = features[name]
        same_thd = all(np.array_equal(phases[phase][:, -1].astype(np.float32), item.values[:, FEATURES.index(f"{phase}_thd")])
                       for phase in PHASES)
        if not np.array_equal(starts, item.sample_start) or not same_thd:
            raise ValueError(f"{name}: os espectros não conferem com os atributos (início das janelas ou THD).")
        spectra[name] = {"fases": phases, "inicio": starts, "irregular": irregular}
    arrays = {}
    for name, item in spectra.items():
        arrays |= {f"{name}_inicio": item["inicio"], f"{name}_irregular": item["irregular"]}
        arrays |= {f"{name}_{phase}": values for phase, values in item["fases"].items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".tmp.npz")
    np.savez_compressed(partial, meta=np.array(json.dumps(meta)), **arrays)
    partial.replace(path)
    return spectra
