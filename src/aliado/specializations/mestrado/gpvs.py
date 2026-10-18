"""Contrato do GPVS-Faults (Bakdi et al., 2020; DOI 10.17632/n76t439f65.1) para o protocolo M14.

Reimplementação, sem pandas nem scikit-learn, do contrato validado no repositório de
origem: 16 ensaios, 24 variáveis por ciclo de 50 Hz, divisão 50/15/15/20 por ensaio
saudável, normalização pela linha de base do treino e
comissionamento dos ensaios com falha pela primeira metade do próprio trecho pré-falha.
Pelo M11, FMECA e GPVS são análises independentes: não há mapeamento entre falhas do
conjunto e grupos da FMECA.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from aliado.science.detection.protocol import (
    DEFAULT_FRACTIONS,
    ROLES,
    RobustScaler,
    decorrelation_report,
    robust_center_scale,
    temporal_split,
)

DATASET_NAME = "GPVS-Faults"
DATASET_DOI = "10.17632/n76t439f65.1"
HEALTHY = ("F0L", "F0M")
FAULTY = tuple(f"F{fault}{mode}" for fault in range(1, 8) for mode in "LM")
EXPERIMENTS = HEALTHY + FAULTY
SOURCE_COLUMNS = ("Time", "Ipv", "Vpv", "Vdc", "ia", "ib", "ic", "va", "vb", "vc", "Iabc", "If", "Vabc", "Vf")
PRIMARY_COLUMNS = ("Ipv", "Vpv", "Vdc", "ia", "ib", "ic", "va", "vb", "vc")
FEATURES = (
    "Ipv_median", "Ipv_iqr", "Vpv_median", "Vpv_iqr", "Vdc_median", "Vdc_iqr",
    "ia_rms", "ib_rms", "ic_rms", "va_rms", "vb_rms", "vc_rms",
    "ia_thd", "ib_thd", "ic_thd", "va_thd", "vb_thd", "vc_thd",
    "i_rms_unbalance", "v_rms_unbalance", "p_ac_mean", "p_ac_std", "p_dc_median", "p_dc_iqr",
)
# Descrição nativa do conjunto e se a falha é física; sem correspondência com a FMECA (M11).
FAULTS = {
    1: ("Falha completa de um IGBT", True),
    2: ("Erro de 20% no sistema de sensor/realimentação", False),
    3: ("Afundamentos intermitentes de tensão da rede", False),
    4: ("Sombreamento parcial não uniforme (10–20%)", False),
    5: ("Circuito aberto em 15% do arranjo fotovoltaico", True),
    6: ("Ganho do controlador PI reduzido em 20%", False),
    7: ("Constante de tempo do controlador PI elevada em 20%", False),
}
MODES = {"L": "IPPT (potência limitada)", "M": "MPPT (potência máxima)"}
SAMPLING_HZ = 10_000.0
GRID_HZ = 50.0
WINDOW = int(round(SAMPLING_HZ / GRID_HZ))  # um ciclo de rede: 200 amostras
BASELINE_FRACTION = 0.50
BASELINE_MIN_WINDOWS = 30
IQR_FLOOR_FRACTION = 0.10
CACHE_VERSION = 1
# Separação canônica entre blocos, decidida pelo pesquisador em 27/09/2026: a verificação do
# lote 13 mostrou |ACF| < 0,2 em 90% das variáveis só no lag 12. A origem usava 2 janelas,
# que continuam servindo para conferir a reprodução.
PURGE = 11


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dataset_files(directory: str | Path) -> dict[str, Path]:
    """Exatamente F0L–F7M; recusa conjunto incompleto ou CSV fora do contrato."""
    base = Path(directory)
    files = {name: base / f"{name}.csv" for name in EXPERIMENTS}
    missing = [name for name, path in files.items() if not path.is_file()]
    if missing:
        raise ValueError("GPVS incompleto; faltam: " + ", ".join(missing))
    extra = sorted(p.name for p in base.glob("*.csv") if p.stem.upper() not in EXPERIMENTS)
    if extra:
        raise ValueError("CSVs fora do contrato GPVS: " + ", ".join(extra))
    return files


def verify_provenance(directory: str | Path) -> dict[str, str]:
    """Hashes atuais; se houver `proveniencia.json`, cada arquivo precisa coincidir com ele."""
    files = dataset_files(directory)
    hashes = {name: sha256_file(path) for name, path in files.items()}
    record = Path(directory) / "proveniencia.json"
    if record.is_file():
        expected = json.loads(record.read_text(encoding="utf-8"))["files"]
        wrong = [name for name, digest in hashes.items() if expected.get(name, {}).get("sha256") != digest]
        if wrong:
            raise ValueError("Arquivos GPVS divergem da proveniência registrada: " + ", ".join(wrong))
    return hashes


def load_csv(path: Path) -> np.ndarray:
    with Path(path).open(encoding="utf-8") as handle:
        header = tuple(handle.readline().strip().split(","))
    if header[:len(SOURCE_COLUMNS)] != SOURCE_COLUMNS:
        raise ValueError(f"{Path(path).name}: colunas fora do contrato GPVS.")
    data = np.loadtxt(path, delimiter=",", skiprows=1, dtype=np.float64, ndmin=2)
    if not np.isfinite(data).all():
        raise ValueError(f"{Path(path).name}: há valores NaN ou infinitos.")
    return data


def sampling(time: np.ndarray) -> dict:
    delta = np.diff(np.asarray(time, dtype=np.float64))
    if len(time) < 1000 or np.any(delta <= 0):
        raise ValueError("Time deve ser estritamente crescente e ter ao menos 1000 pontos.")
    median = float(np.median(delta))
    rate = 1.0 / median
    if not 9_000.0 <= rate <= 11_000.0:
        raise ValueError(f"Taxa de amostragem fora do contrato GPVS: {rate:.1f} Hz.")
    if int(round(rate / GRID_HZ)) != WINDOW:
        raise ValueError("A amostragem não permite janelas de um ciclo de 200 amostras.")
    return {"fs_hz": rate, "dt_mediano_s": median, "dt_min_s": float(delta.min()), "dt_max_s": float(delta.max())}


def _iqr(values: np.ndarray) -> float:
    q25, q75 = np.percentile(values, (25, 75))
    return float(q75 - q25)


def _thd(values: np.ndarray, max_harmonic: int = 40) -> float:
    spectrum = np.abs(np.fft.rfft(values - np.mean(values)))
    fundamental = max(float(spectrum[1]), np.finfo(float).eps)
    limit = min(max_harmonic + 1, len(spectrum))
    return float(np.sqrt(np.sum(spectrum[2:limit] ** 2)) / fundamental)


def feature_vector(window: np.ndarray) -> np.ndarray:
    """24 variáveis de uma janela (200 × 9 colunas primárias, na ordem de PRIMARY_COLUMNS)."""
    matrix = np.asarray(window, dtype=np.float64)
    if matrix.shape != (WINDOW, len(PRIMARY_COLUMNS)):
        raise ValueError(f"A janela deve ter formato ({WINDOW}, {len(PRIMARY_COLUMNS)}).")
    values: list[float] = []
    for column in range(3):  # Ipv, Vpv, Vdc
        values += [float(np.median(matrix[:, column])), _iqr(matrix[:, column])]
    current_rms = np.sqrt(np.mean(matrix[:, 3:6] ** 2, axis=0))
    voltage_rms = np.sqrt(np.mean(matrix[:, 6:9] ** 2, axis=0))
    values += current_rms.tolist() + voltage_rms.tolist()
    values += [_thd(matrix[:, column]) for column in range(3, 9)]
    eps = np.finfo(float).eps
    values += [float(np.std(current_rms) / max(float(np.mean(current_rms)), eps)),
               float(np.std(voltage_rms) / max(float(np.mean(voltage_rms)), eps))]
    ac_power = np.sum(matrix[:, 3:6] * matrix[:, 6:9], axis=1)
    dc_power = matrix[:, 0] * matrix[:, 1]
    values += [float(np.mean(ac_power)), float(np.std(ac_power)), float(np.median(dc_power)), _iqr(dc_power)]
    return np.asarray(values, dtype=np.float32)


@dataclass
class ExperimentFeatures:
    name: str
    values: np.ndarray        # (janelas, 24), float32
    sample_start: np.ndarray  # início de cada janela em amostras
    phase: np.ndarray         # healthy | pre_fault | transition | post_fault
    metadata: dict = field(default_factory=dict)


def extract_experiment(name: str, data: np.ndarray) -> ExperimentFeatures:
    fault = int(name[1])
    info = sampling(data[:, 0])
    primary = data[:, [SOURCE_COLUMNS.index(c) for c in PRIMARY_COLUMNS]]
    windows = len(data) // WINDOW
    # Fronteira nominal no meio do registro: os CSVs não trazem canal de disparo.
    boundary = len(data) // 2 if fault else None
    starts = np.arange(windows) * WINDOW
    values = np.stack([feature_vector(primary[s:s + WINDOW]) for s in starts])
    if boundary is None:
        phase = np.full(windows, "healthy")
    else:
        phase = np.where(starts + WINDOW <= boundary, "pre_fault",
                         np.where(starts >= boundary, "post_fault", "transition"))
    if not np.isfinite(values).all():
        raise ValueError(f"{name}: variáveis não finitas.")
    return ExperimentFeatures(name, values, starts, phase.astype("U10"), {
        **info, "linhas": int(len(data)), "janelas": int(windows),
        "amostras_descartadas_no_fim": int(len(data) - windows * WINDOW),
        "fronteira_falha_amostra": boundary, "fronteira_metodo": "meio_nominal" if fault else None,
    })


def extract_all(directory: str | Path, *, cache: str | Path | None = None) -> tuple[dict, dict]:
    """Extrai os 16 ensaios, reaproveitando o cache só se os hashes dos CSVs forem os mesmos."""
    hashes = verify_provenance(directory)
    files = dataset_files(directory)
    cache_path = Path(cache) if cache else None
    if cache_path and cache_path.is_file():
        with np.load(cache_path, allow_pickle=False) as stored:
            meta = json.loads(str(stored["meta"]))
            if meta.get("hashes") == hashes and meta.get("versao") == CACHE_VERSION:
                return {name: ExperimentFeatures(name, stored[f"{name}_values"], stored[f"{name}_start"],
                                                 stored[f"{name}_phase"], meta["experimentos"][name])
                        for name in EXPERIMENTS}, hashes
    experiments = {name: extract_experiment(name, load_csv(path)) for name, path in files.items()}
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        arrays = {}
        for name, item in experiments.items():
            arrays |= {f"{name}_values": item.values, f"{name}_start": item.sample_start, f"{name}_phase": item.phase}
        meta = {"versao": CACHE_VERSION, "hashes": hashes,
                "experimentos": {name: item.metadata for name, item in experiments.items()}}
        temporary = cache_path.with_suffix(".tmp.npz")
        np.savez_compressed(temporary, meta=json.dumps(meta), **arrays)
        temporary.replace(cache_path)
    return experiments, hashes


@dataclass
class PreparedGPVS:
    healthy_values: np.ndarray       # (N, 24) variáveis brutas de F0L seguido de F0M
    healthy_experiment: np.ndarray   # ensaio de cada janela saudável
    split: dict                      # papel -> índices globais; "por_ensaio" -> ensaio -> papel -> índices
    normalized: np.ndarray           # normalização pela linha de base do treino de cada ensaio
    scaler: RobustScaler             # ajustado só no treino normalizado
    scaled: np.ndarray               # entrada dos modelos
    iqr_floor: np.ndarray
    baselines: dict
    faults: dict                     # ensaio -> escalado, índices de avaliação e metadados
    hashes: dict
    extraction: dict
    fractions: tuple
    purge: int


def prepare(directory: str | Path, *, cache: str | Path | None = None,
            fractions=DEFAULT_FRACTIONS, purge: int = PURGE) -> PreparedGPVS:
    experiments, hashes = extract_all(directory, cache=cache)
    values = np.concatenate([experiments[name].values for name in HEALTHY])
    labels = np.concatenate([np.full(len(experiments[name].values), name) for name in HEALTHY])
    split = {role: [] for role in ROLES}
    per_experiment = {}
    offset = 0
    for name in HEALTHY:
        local = temporal_split(len(experiments[name].values), fractions=fractions, purge=purge)
        per_experiment[name] = {role: local[role] + offset for role in ROLES}
        for role in ROLES:
            split[role].append(per_experiment[name][role])
        offset += len(experiments[name].values)
    split = {role: np.concatenate(parts) for role, parts in split.items()}
    split["por_ensaio"] = per_experiment

    # Piso da escala: 10% do IQR de todo o treino, nunca abaixo de 1e-6.
    train = values[split["train"]].astype(np.float64)
    q25, q75 = np.percentile(train, (25, 75), axis=0)
    iqr_floor = np.maximum((q75 - q25) * IQR_FLOOR_FRACTION, 1e-6)
    normalized = np.empty_like(values, dtype=np.float32)
    baselines = {}
    for name in HEALTHY:
        center, scale = robust_center_scale(values[per_experiment[name]["train"]], floor=iqr_floor)
        mask = labels == name
        normalized[mask] = ((values[mask] - center) / scale).astype(np.float32)
        baselines[name] = {"mediana": center, "escala": scale}
    scaler = RobustScaler.fit(normalized[split["train"]])
    scaled = scaler.transform(normalized)

    faults = {}
    for name in FAULTY:
        item = experiments[name]
        pre = np.flatnonzero(item.phase == "pre_fault")
        n_baseline = max(BASELINE_MIN_WINDOWS, int(np.floor(len(pre) * BASELINE_FRACTION)))
        if n_baseline >= len(pre):
            raise ValueError(f"{name}: pré-falha insuficiente para comissionamento e teste.")
        # Comissionamento: cada ensaio com falha usa a primeira metade do próprio pré-falha.
        center, scale = robust_center_scale(item.values[pre[:n_baseline]], floor=iqr_floor)
        commissioned = ((item.values - center) / scale).astype(np.float32)
        faults[name] = {
            "scaled": scaler.transform(commissioned),
            "comissionamento": pre[:n_baseline],
            "pre_teste": pre[n_baseline:],
            "transicao": np.flatnonzero(item.phase == "transition"),
            "pos_falha": np.flatnonzero(item.phase == "post_fault"),
        }
    return PreparedGPVS(values, labels, split, normalized, scaler, scaled, iqr_floor, baselines, faults,
                        hashes, {name: item.metadata for name, item in experiments.items()},
                       tuple(fractions), int(purge))


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
