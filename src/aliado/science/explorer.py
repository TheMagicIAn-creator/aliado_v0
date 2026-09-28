"""Exploradores da aba Ciência (lote 20): limiar, alarme e detecção, e confiabilidade.

Os do GPVS reaproveitam as funções da avaliação canônica (`segment_errors`, `top_k_scores`,
`calibrate_threshold` e `run_metrics`) com os modelos congelados. O erro por variável de cada
janela é calculado uma vez e guardado fora de `data/resultados`, que não muda. Com k = 5, p99 e
m = 3, os números são os da avaliação de 27/09/2026.

O explorador do limiar usa só a calibração. O de alarme e detecção usa o teste saudável e os
ensaios com falha, já consultados: é exploração pós-teste, não canônica (M14), e não substitui
os resultados congelados. O de confiabilidade chama o serviço RAM; o navegador não refaz contas.
"""

from __future__ import annotations

import csv
import json
import threading
from pathlib import Path

import numpy as np

from aliado.science.detection import gpvs
from aliado.science.detection.threshold import calibrate_threshold

CACHE_VERSION = 1
EVALUATION = "gpvs-avaliacao-001"
POST_TEST_NOTICE = ("Exploração pós-teste, não canônica (M14): usa o teste já consultado e não altera "
                    "os resultados congelados da avaliação de 27/09/2026.")
PERCENTILES = (90.0, 99.9)
CONFIRMATIONS = (1, 10)
MODEL_NAMES = {"denso": "Denso", "lstm": "AE-LSTM"}
EXPLORATION_SOURCE = "Exploração na aba Ciência; sem fonte registrada."


def plain(value):
    """Tipos do numpy viram tipos do Python, para a resposta em JSON."""
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


class Explorer:
    """Estado carregado sob demanda: modelos, dados preparados e erros por variável."""

    def __init__(self, results_dir: str | Path, gpvs_dir: str | Path, cache_dir: str | Path):
        self.results_dir = Path(results_dir)
        self.gpvs_dir = Path(gpvs_dir)
        self.cache_dir = Path(cache_dir)
        self.evaluation_dir = self.results_dir / EVALUATION
        self._state = None
        self._lock = threading.Lock()

    # Disponibilidade e preparo

    def training_dir(self) -> Path:
        config = json.loads((self.evaluation_dir / "configuracao.json").read_text(encoding="utf-8"))
        return self.results_dir / Path(config["treino"]["pasta"]).name

    def status(self) -> dict:
        """O que falta para os exploradores do GPVS, sem carregar modelos nem dados."""
        missing = []
        if not (self.evaluation_dir / "configuracao.json").is_file():
            missing.append(f"a avaliação canônica ({EVALUATION}) em {self.results_dir}")
        elif not (self.training_dir() / "configuracao.json").is_file():
            missing.append(f"a rodada de treino {self.training_dir().name}")
        if not (self.gpvs_dir / "proveniencia.json").is_file():
            missing.append(f"os dados do GPVS em {self.gpvs_dir}")
        return {"disponivel": not missing, "faltando": missing, "pronto": self._state is not None}

    def prepare(self, progress=None) -> dict:
        """Carrega modelos e dados e calcula (ou lê do cache) o erro por variável de cada janela."""
        with self._lock:
            if self._state is None:
                self._state = self._load(progress)
        return self.status()

    def _load(self, progress) -> dict:
        from aliado.science.detection.evaluation import load_training
        from aliado.science.detection.models import MODELS

        status = self.status()
        if not status["disponivel"]:
            raise ValueError("Exploradores do GPVS indisponíveis: falta " + "; ".join(status["faltando"]) + ".")
        evaluation = json.loads((self.evaluation_dir / "configuracao.json").read_text(encoding="utf-8"))
        report = json.loads((self.evaluation_dir / "relatorio.json").read_text(encoding="utf-8"))
        if progress:
            progress("modelos", 0, 3)
        trained = load_training(self.training_dir())
        if evaluation["treino"]["configuracao_sha256"] != trained.frozen["sha256"]:
            raise ValueError("A avaliação canônica não é da rodada de treino encontrada.")
        if progress:
            progress("dados", 1, 3)
        prepared = gpvs.prepare(self.gpvs_dir, cache=self.gpvs_dir / "processado" / "variaveis.npz",
                                purge=trained.config.purge, fractions=trained.config.fractions)
        if prepared.hashes != trained.frozen["dados"]["hashes"]:
            raise ValueError("Os dados do GPVS não são os do treino.")
        if progress:
            progress("erros por variável", 2, 3)
        errors = self._errors(trained, prepared)
        with (self.evaluation_dir / "metricas_por_ensaio.csv").open(encoding="utf-8", newline="") as handle:
            canonical_trials = list(csv.DictReader(handle))
        if progress:
            progress("pronto", 3, 3)
        return {"trained": trained, "prepared": prepared, "errors": errors, "report": report,
                "canonical_trials": canonical_trials, "models": MODELS}

    def _errors(self, trained, prepared) -> dict:
        from aliado.science.detection.evaluation import segment_errors
        from aliado.science.detection.models import feature_errors
        from aliado.science.detection.training import model_inputs, training_blocks

        meta = {"versao": CACHE_VERSION, "treino": trained.frozen["sha256"], "dados": prepared.hashes}
        path = self.cache_dir / f"erros-{trained.frozen['sha256'][:12]}.npz"
        if path.is_file():
            with np.load(path) as cached:
                if json.loads(str(cached["meta"])) == meta:
                    return self._split(dict(cached), trained)
        sequence = trained.config.hyperparameters.sequence
        calibration = training_blocks(prepared)["calibration"]
        arrays = {}
        for (kind, seed), model in trained.models.items():
            key = f"{kind}_s{seed}"
            arrays[f"{key}_calibracao"] = feature_errors(model, model_inputs(kind, prepared.scaled, calibration, sequence))
            for name in gpvs.HEALTHY:
                block = prepared.split["por_ensaio"][name]["test"]
                arrays[f"{key}_saudavel_{name}"] = segment_errors(kind, model, prepared.scaled[block], sequence)
            for name, item in prepared.faults.items():
                arrays[f"{key}_{name}"] = segment_errors(kind, model, item["scaled"], sequence)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(".tmp.npz")
        np.savez_compressed(partial, meta=np.array(json.dumps(meta)), **arrays)
        partial.replace(path)
        return self._split(arrays, trained)

    @staticmethod
    def _split(arrays: dict, trained) -> dict:
        return {(kind, seed): {name[len(f"{kind}_s{seed}_"):]: arrays[name] for name in arrays
                               if name.startswith(f"{kind}_s{seed}_")}
                for kind, seed in trained.models}

    def _ready(self, kind: str, seed: int) -> tuple[dict, dict]:
        if self._state is None:
            raise ValueError("Prepare os exploradores do GPVS antes de usá-los.")
        errors = self._state["errors"].get((kind, int(seed)))
        if errors is None:
            raise ValueError("Modelo ou semente inexistente na rodada de treino.")
        return self._state, errors

    # Explorador do limiar (só calibração)

    def threshold(self, kind: str, seed: int, k: int, percentile: float, window: int | None = None) -> dict:
        from aliado.science.detection.models import top_k_scores

        state, errors = self._ready(kind, seed)
        k, percentile = _k(k), _range(percentile, PERCENTILES, "percentil")
        calibration_errors = errors["calibracao"]
        scores = top_k_scores(calibration_errors, k)
        calibration = calibrate_threshold(scores, percentile, strict=False)
        window = int(np.argmax(scores)) if window is None else int(window)
        if not 0 <= window < len(scores):
            raise ValueError("Janela de calibração inexistente.")
        row = calibration_errors[window]
        largest = [int(index) for index in np.argsort(row)[::-1][:k]]
        config = state["trained"].config
        return plain({
            "modelo": kind, "semente": int(seed), "k": k, "percentil": percentile,
            "escores_ordenados": np.sort(scores), "limiar": calibration.as_dict(),
            "janela": {"indice": window, "escore": scores[window], "variaveis": list(gpvs.FEATURES),
                       "erros": row, "maiores": largest, "media_todas": float(row.mean()),
                       "media_k": float(row[largest].mean())},
            "canonico": {"k": config.top_k, "percentil": config.percentile,
                         "limiar": state["trained"].thresholds[(kind, int(seed), config.top_k)]},
        })

    # Explorador de alarme e detecção (pós-teste)

    def alarms(self, kind: str, seed: int, k: int, percentile: float, confirmations: int,
               trial: str | None = None) -> dict:
        from aliado.science.detection.evaluation import _onset, run_metrics
        from aliado.science.detection.metrics import alarm_starts
        from aliado.science.detection.models import top_k_scores

        state, errors = self._ready(kind, seed)
        k, percentile = _k(k), _range(percentile, PERCENTILES, "percentil")
        confirmations = int(_range(confirmations, CONFIRMATIONS, "confirmações"))
        if trial is not None and trial not in gpvs.FAULTY:
            raise ValueError("Ensaio inexistente.")
        calibration = calibrate_threshold(top_k_scores(errors["calibracao"], k), percentile, strict=False)
        scores = {"saudavel": [top_k_scores(errors[f"saudavel_{name}"], k) for name in gpvs.HEALTHY],
                  "ensaios": {name: top_k_scores(errors[name], k) for name in gpvs.FAULTY}}
        prepared = state["prepared"]
        metrics = run_metrics(scores, calibration.value, prepared, confirmations)
        canonical = {row["ensaio"]: row for row in state["canonical_trials"]
                     if row["modelo"] == kind and int(row["semente"]) == int(seed)}
        trials = []
        for name in gpvs.FAULTY:
            fault, physical = gpvs.FAULTS[int(name[1])]
            item, reference = metrics["ensaios"][name], canonical.get(name, {})
            trials.append({
                "ensaio": name, "falha": fault, "fisica": physical, "modo": gpvs.MODES[name[2]],
                "detectado": item["detectado"], "atraso_ms": item["atraso_ms"],
                "alarmes_pre_falha": item["alarmes_pre_falha"],
                "canonico": {"detectado": reference.get("detectado") == "True",
                             "atraso_ms": float(reference["atraso_ms"]) if reference.get("atraso_ms") else None}
                if reference else None,
            })
        timeline = None
        if trial is not None:
            item, values = prepared.faults[trial], scores["ensaios"][trial]
            above = values > calibration.value
            timeline = {"ensaio": trial, "escores": values, "limiar": calibration.value,
                        "alarmes": alarm_starts(above, confirmations),
                        "inicio_nominal": _onset(item), "comissionamento": _span(item["comissionamento"]),
                        "pre_teste": _span(item["pre_teste"]), "transicao": _span(item["transicao"]),
                        "pos_falha": _span(item["pos_falha"])}
        run = state["report"]["modelos"][kind]["sementes"][str(int(seed))]
        config = state["trained"].config
        official = {"k": config.top_k, "percentil": config.percentile, "confirmacoes": state["report"]["confirmacao"]}
        return plain({
            "aviso": POST_TEST_NOTICE, "modelo": kind, "semente": int(seed), "k": k, "percentil": percentile,
            "confirmacoes": confirmations, "limiar": calibration.as_dict(), "resumo": metrics["resumo"],
            "falsos_alarmes": metrics["falsos_alarmes"], "ensaios": trials, "linha_do_tempo": timeline,
            "parametros_canonicos": (k, percentile, confirmations) == (official["k"], official["percentil"],
                                                                       official["confirmacoes"]),
            "canonico": official | {"limiar": state["trained"].thresholds[(kind, int(seed), config.top_k)],
                                    "detectados": run["resumo"]["detectados"],
                                    "atraso_mediano_ms": run["resumo"]["atraso_mediano_ms"],
                                    "alarmes_teste_saudavel": run["alarmes_teste_saudavel"],
                                    "alarmes_pre_falha": run["alarmes_pre_falha"]},
        })

    def choices(self) -> dict:
        state = self._state
        if state is None:
            return {}
        config = state["trained"].config
        return {"modelos": [{"id": kind, "nome": MODEL_NAMES.get(kind, kind)} for kind in state["models"]],
                "sementes": list(config.seeds), "semente_referencia": config.reference_seed,
                "k_canonico": config.top_k, "percentil_canonico": config.percentile,
                "confirmacoes_canonicas": state["report"]["confirmacao"],
                "variaveis": len(gpvs.FEATURES), "ensaios": list(gpvs.FAULTY)}


def _k(value) -> int:
    k = int(value)
    if not 1 <= k <= len(gpvs.FEATURES):
        raise ValueError(f"k deve estar entre 1 e {len(gpvs.FEATURES)}.")
    return k


def _range(value, bounds: tuple, label: str) -> float:
    number = float(value)
    if not bounds[0] <= number <= bounds[1]:
        raise ValueError(f"{label} deve estar entre {bounds[0]:g} e {bounds[1]:g}.")
    return number


def _span(indices) -> list[int] | None:
    return [int(indices[0]), int(indices[-1])] if len(indices) else None


def reliability(rate_per_hour: float, hours_per_year: float, basis: str, horizon_years: float,
                points: int = 41) -> dict:
    """Curvas de confiabilidade exponencial pelo serviço RAM, sem gravar nada (exploração)."""
    from aliado.science import evaluate_scenario

    horizon = float(horizon_years)
    if not 0 < horizon <= 100:
        raise ValueError("O horizonte deve estar entre 0 e 100 anos.")
    times = {round(horizon * index / (points - 1), 6) for index in range(points)}
    times = sorted(times | {1.0} if horizon >= 1 else times)  # 1 ano sempre aparece na tabela
    scenario = {
        "name": "Exploração na aba Ciência", "kind": "exponential", "time_unit": "year",
        "time_base": {"rate_unit": "h", "hours_per_year": hours_per_year, "basis": basis},
        "parameters": {"rate": rate_per_hour}, "times": times,
        "sources": [EXPLORATION_SOURCE], "assumptions": ["Valores escolhidos nos controles; nada é gravado."],
    }
    return evaluate_scenario(scenario)
