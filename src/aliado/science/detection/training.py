"""Treino dos autoencoders e limiar na calibração saudável do GPVS (lote 14, protocolo M14).

Os modelos veem só o treino (pesos) e a validação (parada). A calibração serve só para o
limiar. O teste saudável e os ensaios com falha não são pontuados aqui: ficam fechados até
a avaliação do lote 15, com a configuração já congelada. Exige o extra `ml`.
"""

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import torch

from aliado.science.detection import gpvs
from aliado.science.detection.models import (
    MODEL_NAMES,
    MODELS,
    Hyperparameters,
    TrainingHistory,
    feature_errors,
    fit,
    parameter_count,
    save_model,
    top_k_scores,
)
from aliado.science.detection.protocol import DEFAULT_FRACTIONS, ROLES, sequences_for_blocks
from aliado.science.detection.threshold import (
    DegenerateThresholdError,
    ThresholdCalibration,
    calibrate_threshold,
    effective_sample_size,
    minimum_n_for_percentile,
)

TRAINING_ROLES = ("train", "validation", "calibration")
SECONDS_PER_HOUR = 3600
ROLE_NAMES = {"train": "Treino", "validation": "Validação", "calibration": "Calibração", "test": "Teste"}


@dataclass(frozen=True)
class ExperimentConfig:
    """Escolhas congeladas antes de qualquer avaliação (M14), gravadas com hash em cada saída."""

    purge: int = gpvs.PURGE
    fractions: tuple[float, ...] = DEFAULT_FRACTIONS
    seeds: tuple[int, ...] = (13, 29, 42, 71, 101)
    reference_seed: int = 42
    top_k: int = 5
    sensitivity_k: tuple[int, ...] = (5, 10, 20)  # só relatada; nunca escolhe o k principal
    percentile: float = 99.0
    hyperparameters: Hyperparameters = field(default_factory=Hyperparameters)

    def __post_init__(self):
        if not self.seeds or len(set(self.seeds)) != len(self.seeds) or self.reference_seed not in self.seeds:
            raise ValueError("As sementes devem ser distintas e incluir a de referência.")
        if self.top_k not in self.sensitivity_k:
            raise ValueError("A grade de sensibilidade deve incluir o k principal.")

    def as_dict(self) -> dict:
        return json.loads(json.dumps(asdict(self)))

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.as_dict(), sort_keys=True).encode("utf-8")).hexdigest()


@dataclass
class Run:
    kind: str
    seed: int
    model: torch.nn.Module
    history: TrainingHistory
    scores: dict[int, np.ndarray]  # k -> escores da calibração
    thresholds: dict[int, ThresholdCalibration]
    block_sizes: tuple[int, ...]  # calibração de cada ensaio saudável, na ordem de gpvs.HEALTHY


def training_blocks(prepared: gpvs.PreparedGPVS) -> dict[str, list[np.ndarray]]:
    """Blocos contíguos por papel e ensaio saudável; o teste não é entregue ao treino."""
    return {role: [prepared.split["por_ensaio"][name][role] for name in gpvs.HEALTHY] for role in TRAINING_ROLES}


def model_inputs(kind: str, scaled: np.ndarray, blocks, sequence: int) -> np.ndarray:
    if kind == "denso":
        return np.asarray(scaled, dtype=np.float32)[np.concatenate(blocks)]
    return sequences_for_blocks(scaled, blocks, sequence)[0]


def train_detectors(scaled: np.ndarray, blocks: dict, config: ExperimentConfig, *, progress=None) -> list[Run]:
    """Cada modelo em cada semente: treino, parada pela validação e limiar na calibração."""
    hp = config.hyperparameters
    inputs = {kind: {role: model_inputs(kind, scaled, blocks[role], hp.sequence) for role in TRAINING_ROLES}
              for kind in MODELS}
    sizes = tuple(len(block) for block in blocks["calibration"])
    minimum = minimum_n_for_percentile(config.percentile)
    if minimum is None or sum(sizes) < minimum:
        # Recusa antes de treinar: o limiar cairia no maior escore da calibração.
        raise DegenerateThresholdError(
            f"p{config.percentile:g} exige ao menos {minimum} janelas de calibração; há {sum(sizes)}.")
    runs = []
    for seed in config.seeds:
        for kind in MODELS:
            model, history = fit(kind, inputs[kind]["train"], inputs[kind]["validation"], seed=seed, hp=hp)
            errors = feature_errors(model, inputs[kind]["calibration"])
            scores = {k: top_k_scores(errors, k) for k in config.sensitivity_k}
            thresholds = {k: calibrate_threshold(scores[k], config.percentile) for k in config.sensitivity_k}
            runs.append(Run(kind, seed, model, history, scores, thresholds, sizes))
            if progress:
                progress(f"{MODEL_NAMES[kind]}, semente {seed}: melhor época {history.best_epoch} de "
                         f"{history.epochs}; limiar {thresholds[config.top_k].value:.4g}")
    return runs


def environment() -> dict:
    return {"python": platform.python_version(), "torch": torch.__version__, "numpy": np.__version__,
            "threads": torch.get_num_threads(), "sistema": platform.platform()}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(runs: list[Run], prepared: gpvs.PreparedGPVS, config: ExperimentConfig, files: dict) -> dict:
    preparation = gpvs.report(prepared)
    decorrelation = preparation["verificacao_m14_autocorrelacao"]
    n_calibration = sum(runs[0].block_sizes)
    per_second = gpvs.GRID_HZ  # uma janela por ciclo de rede
    models = {}
    for kind in MODELS:
        own = [run for run in runs if run.kind == kind]
        seeds = {}
        for run in own:
            principal = run.thresholds[config.top_k]
            blocks = np.split(run.scores[config.top_k], np.cumsum(run.block_sizes)[:-1])
            dependence = effective_sample_size(blocks)
            for name, item in zip(gpvs.HEALTHY, dependence["blocos"]):
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


def _markdown(summary: dict, config: ExperimentConfig) -> str:
    reference = str(config.reference_seed)
    protocol, calibration = summary["protocolo"], summary["calibracao"]
    check = protocol["verificacao_m14"]
    lines = [
        "# Treino dos autoencoders — GPVS, protocolo M14", "",
        f"Configuração congelada `{summary['configuracao_sha256'][:12]}`: separação de "
        f"{protocol['separacao_janelas']} janelas; sementes {', '.join(map(str, config.seeds))} "
        f"(referência {reference}); escore top-{config.top_k}; limiar p{config.percentile:g} na calibração.", "",
        "## Divisão saudável", "",
        "| Papel | " + " | ".join(ROLE_NAMES[role] for role in ROLES) + " |", "|---|" + "---:|" * len(ROLES),
        "| Janelas | " + " | ".join(str(protocol["papeis"][role]) for role in ROLES) + " |", "",
        f"Verificação do M14: distância entre blocos {check['distancia_entre_blocos']}, lag necessário "
        f"{check['lag_necessario']} — " + ("suficiente." if check["suficiente"] else "**insuficiente**."),
        f"A calibração tem {calibration['janelas']} janelas: {calibration['duracao_s']:.2f} s de operação "
        f"({calibration['janelas_por_segundo']:g} janelas por segundo).", "",
        f"## Modelos na semente {reference}", "",
        "| Modelo | Parâmetros | Melhor época | Épocas | Perda de validação | Limiar | Posição | "
        "Falso alarme esperado |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in summary["modelos"].values():
        run, limit = item["sementes"][reference], item["sementes"][reference]["limiar"]
        lines.append(
            f"| {item['nome']} | {item['parametros']} | {run['melhor_epoca']} | {run['epocas_executadas']} | "
            f"{run['perda_validacao_minima']:.4f} | {limit['limiar']:.4f} | {limit['posicao']}/{limit['n_calibracao']} | "
            f"{100 * limit['falso_alarme_esperado_por_janela']:.2f}% por janela "
            f"(~{limit['falso_alarme_esperado_por_hora']:.0f} por hora) |")
    lines += ["", "## Estabilidade entre sementes", "",
              "| Modelo | Semente | Melhor época | Épocas | Parada | Limiar |", "|---|---:|---:|---:|---|---:|"]
    for item in summary["modelos"].values():
        for seed, run in item["sementes"].items():
            lines.append(f"| {item['nome']} | {seed} | {run['melhor_epoca']} | {run['epocas_executadas']} | "
                         f"{'validação' if run['parada'] == 'paciencia' else '**teto**'} | "
                         f"{run['limiar']['limiar']:.4f} |")
    lines += ["", f"## Sensibilidade do k (p{config.percentile:g}, semente {reference})", "",
              "| Modelo | " + " | ".join(f"k = {k}" for k in config.sensitivity_k) + " |",
              "|---|" + "---:|" * len(config.sensitivity_k)]
    for item in summary["modelos"].values():
        grid = item["sementes"][reference]["sensibilidade_k"]
        lines.append(f"| {item['nome']} | " + " | ".join(f"{grid[str(k)]:.4f}" for k in config.sensitivity_k) + " |")
    lines += ["", f"## Autocorrelação dos escores de calibração (semente {reference})", "",
              "| Modelo | ACF de lag 1 por ensaio | n efetivo |", "|---|---|---:|"]
    for item in summary["modelos"].values():
        dependence = item["sementes"][reference]["autocorrelacao_escores"]
        acf = "; ".join(f"{block['ensaio']} {block['acf_lag1']:.2f}" for block in dependence["blocos"])
        lines.append(f"| {item['nome']} | {acf} | {dependence['n_efetivo']:.0f} de {dependence['n']} |")
    lines += [
        "",
        "O falso alarme esperado vale para janelas saudáveis permutáveis com as da calibração. "
        "Com escores autocorrelacionados, a média se mantém, mas a taxa observada num trecho curto "
        "varia muito mais; o n efetivo (aproximação AR(1)) dá a ordem de grandeza.",
        "",
        "O teste saudável e os ensaios com falha não foram pontuados: ficam fechados até o lote 15.",
    ]
    return "\n".join(lines) + "\n"


def export_training(runs: list[Run], prepared: gpvs.PreparedGPVS, config: ExperimentConfig,
                    output: str | Path) -> dict[str, str]:
    """Modelos, históricos, escores de calibração, configuração e relatório numa pasta nova."""
    if prepared.purge != config.purge or tuple(prepared.fractions) != tuple(config.fractions):
        raise ValueError("Os dados preparados não seguem a divisão da configuração congelada.")
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "modelos").mkdir()
    (folder / "historicos").mkdir()
    files = {}
    for run in runs:
        name = f"{run.kind}-s{run.seed}"
        model_path = folder / "modelos" / f"{name}.pt"
        save_model(run.model, model_path, kind=run.kind, seed=run.seed, n_features=prepared.scaled.shape[1],
                   hp=config.hyperparameters)
        history_path = folder / "historicos" / f"{name}.csv"
        rows = zip(run.history.train_loss, run.history.validation_loss)
        history_path.write_text("epoca,perda_treino,perda_validacao\n" + "".join(
            f"{epoch},{train!r},{validation!r}\n" for epoch, (train, validation) in enumerate(rows, start=1)),
            encoding="utf-8")
        files[name] = {"modelo": {"caminho": f"modelos/{name}.pt", "sha256": _sha256(model_path)},
                       "historico": {"caminho": f"historicos/{name}.csv", "sha256": _sha256(history_path)}}
    paths = {"configuracao": folder / "configuracao.json", "relatorio_json": folder / "relatorio.json",
             "relatorio_md": folder / "relatorio.md", "escores": folder / "escores_calibracao.npz",
             "normalizacao": folder / "normalizacao.npz"}
    np.savez_compressed(paths["escores"], **{f"{run.kind}_s{run.seed}_k{k}": scores
                                             for run in runs for k, scores in run.scores.items()})
    gpvs.save_normalization(prepared, paths["normalizacao"])
    frozen = {"configuracao": config.as_dict(), "sha256": config.digest(), "ambiente": environment(),
              "dados": {"conjunto": gpvs.DATASET_NAME, "doi": gpvs.DATASET_DOI, "hashes": prepared.hashes}}
    paths["configuracao"].write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = summarize(runs, prepared, config, files)
    paths["relatorio_json"].write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                                       encoding="utf-8")
    paths["relatorio_md"].write_text(_markdown(summary, config), encoding="utf-8")
    return {key: str(path) for key, path in paths.items()}
