"""Exploradores da aba Ciência (lote 20): o do limiar e o dos alarmes e da detecção.

Os do GPVS reaproveitam as funções da avaliação canônica (`errors_all`, `top_k_scores`,
`calibrate_threshold` e `run_metrics`) com os modelos congelados. O erro por variável de cada
janela vem da matriz que a avaliação gravou (`erros.npz`, lote 54), conferida pelo contrato e nunca
recalculada; nas rodadas anteriores a ela, é calculado uma vez e guardado fora de `data/resultados`,
que não muda. Com k = 5, p99 e m = 3, os números são os da avaliação de 27/09/2026.

O explorador do limiar usa só a calibração. O de alarme e detecção usa o teste saudável e os
ensaios com falha, já consultados: é exploração pós-teste, não canônica (M14), e não substitui
os resultados congelados. O "Preparar" monta também a evidência espectral das rodadas que não a
trazem (lote 55), na pasta dos exploradores, com o mesmo estatuto. O de confiabilidade fica no
núcleo (`science/confiabilidade` e a rota da aba).
"""

from __future__ import annotations

import csv
import json
import threading
from pathlib import Path

import numpy as np

from aliado.science.deteccao.limiar.calibracao import calibrate_threshold
from aliado.science.identidade.contrato import ContractViolationError
from aliado.science.identidade.hashes import config_digest
from aliado.specializations.mestrado.atributos import variaveis
from aliado.specializations.mestrado.atributos.cache import features_cache
from aliado.specializations.mestrado.base import ensaios
from aliado.specializations.mestrado.preparo import preparacao

CACHE_VERSION = 2  # lote 46: a chave inclui os hashes dos pesos e a ordem das variáveis
# Em palavras, sem códigos internos (lote 23): o controle por trás continua sendo o M14.
POST_TEST_NOTICE = ("Estes controles reusam os ensaios de teste. Servem para explorar; os números oficiais "
                    "continuam os da avaliação de 27/09/2026.")
WINDOW_KEYS = ("sensibilidade", "especificidade", "precisao", "f1", "mcc", "auc_roc", "auc_pr", "vp", "fn", "fp", "vn")
PERCENTILES = (90.0, 99.9)
CONFIRMATIONS = (1, 10)
MODEL_NAMES = {"denso": "Denso", "lstm": "AE-LSTM"}


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
        from aliado.specializations.mestrado.resultados.rodada_atual import current

        self.results_dir = Path(results_dir)
        self.gpvs_dir = Path(gpvs_dir)
        self.cache_dir = Path(cache_dir)
        self.run = current(self.results_dir)  # a rodada que a aba mostra; outra rodada pede outro explorador
        self.evaluation_dir = self.run.evaluation
        self._state = None
        self._evidence_error = None
        self._lock = threading.Lock()

    # Disponibilidade e preparo

    def training_dir(self) -> Path:
        config = json.loads((self.evaluation_dir / "configuracao.json").read_text(encoding="utf-8"))
        return self.evaluation_dir.parent / Path(config["treino"]["pasta"]).name

    def status(self) -> dict:
        """O que falta para os exploradores do GPVS, sem carregar modelos nem dados."""
        missing = []
        if not (self.evaluation_dir / "configuracao.json").is_file():
            missing.append(f"a avaliação da rodada ({self.evaluation_dir.name}) em {self.results_dir}")
        elif not (self.training_dir() / "configuracao.json").is_file():
            missing.append(f"a rodada de treino {self.training_dir().name}")
        if not (self.gpvs_dir / "proveniencia.json").is_file():
            missing.append(f"os dados do GPVS em {self.gpvs_dir}")
        return {"disponivel": not missing, "faltando": missing, "pronto": self._state is not None,
                "evidencia_espectral": self.evidence_status()}

    def evidence_status(self) -> dict:
        """A evidência espectral da rodada: a da própria rodada, a de exploração pós-teste ou nenhuma, e o erro dela."""
        from aliado.specializations.mestrado.evidencia_espectral import artefatos

        found = artefatos.find(self.run, self.cache_dir)
        origin = None if found is None else ("exploracao" if found.parent == self.cache_dir else "rodada")
        return {"pronta": found is not None, "origem": origin, "erro": self._evidence_error}

    def prepare(self, progress=None) -> dict:
        """Carrega modelos e dados e calcula (ou lê do cache) o erro por variável de cada janela."""
        with self._lock:
            if self._state is None:
                self._state = self._load(progress)
        return self.status()

    def _load(self, progress) -> dict:
        from aliado.science.deteccao.redes.autoencoders import MODELS
        from aliado.specializations.mestrado.avaliacao.treino_congelado import (
            load_training,
            weight_hashes,
        )

        status = self.status()
        if not status["disponivel"]:
            raise ValueError("Exploradores do GPVS indisponíveis: falta " + "; ".join(status["faltando"]) + ".")
        evaluation = json.loads((self.evaluation_dir / "configuracao.json").read_text(encoding="utf-8"))
        report = json.loads((self.evaluation_dir / "relatorio.json").read_text(encoding="utf-8"))
        if progress:
            progress("modelos", 0, 4)
        trained = load_training(self.training_dir())
        if evaluation["treino"]["configuracao_sha256"] != trained.frozen["sha256"]:
            raise ValueError("A avaliação não é da rodada de treino encontrada.")
        if progress:
            progress("dados", 1, 4)
        prepared = preparacao.prepare(self.gpvs_dir, cache=features_cache(self.gpvs_dir),
                                purge=trained.config.purge, fractions=trained.config.fractions)
        if prepared.hashes != trained.frozen["dados"]["hashes"]:
            raise ValueError("Os dados do GPVS não são os do treino.")
        if progress:
            progress("erros por variável", 2, 4)
        # Os hashes dos pesos que `load_training` acabou de conferir com os arquivos (lote 46).
        errors = self._errors(trained, prepared, weight_hashes(trained))
        with (self.evaluation_dir / "metricas_por_ensaio.csv").open(encoding="utf-8", newline="") as handle:
            canonical_trials = list(csv.DictReader(handle))
        if progress:
            progress("evidência espectral", 3, 4)
        self._evidence(prepared, errors)
        if progress:
            progress("pronto", 4, 4)
        return {"trained": trained, "prepared": prepared, "errors": errors, "report": report,
                "canonical_trials": canonical_trials, "models": MODELS}

    def _evidence(self, prepared, errors: dict) -> None:
        """Numa rodada sem a evidência espectral, monta a de exploração pós-teste na pasta dos exploradores, nunca em
        data/resultados. Ela é secundária: uma falha fica no estado, com o motivo, e os exploradores seguem."""
        from aliado.specializations.mestrado.evidencia_espectral import artefatos, evidencia

        if artefatos.find(self.run) is not None:  # a rodada já traz a dela
            return
        flat = {f"{kind}_s{seed}_{group}": array for (kind, seed), groups in errors.items()
                for group, array in groups.items()}
        try:
            built = evidencia.build(self.run, self.gpvs_dir, prepared, flat, origin="exploracao")
            artefatos.write(built, artefatos.exploration_file(self.cache_dir, self.run))
            self._evidence_error = None
        except Exception as exc:  # secundária: qualquer falha, o erro de contrato inclusive, fica no estado
            self._evidence_error = str(exc) or type(exc).__name__

    def _errors(self, trained, prepared, weights: dict) -> dict:
        from aliado.specializations.mestrado.avaliacao.artefatos import ERRORS, load_errors
        from aliado.specializations.mestrado.avaliacao.pontuacao import errors_all

        saved = self.evaluation_dir / ERRORS
        if saved.is_file():  # rodada com o contrato do lote 54: vale a matriz gravada, sem recalcular nem copiar
            meta, arrays = load_errors(saved)
            if (meta["treino"], meta["dados"], meta["pesos"]) != (trained.frozen["sha256"], prepared.hashes, weights):
                raise ContractViolationError(f"{ERRORS}: não é desta rodada; o treino, os dados ou os pesos não conferem.")
            return self._split(arrays, trained)
        meta = {"versao": CACHE_VERSION, "treino": trained.frozen["sha256"], "dados": prepared.hashes,
                "pesos": weights, "variaveis": list(variaveis.FEATURES)}
        # O nome vem da chave inteira: um treino com a mesma configuração e outros pesos não reaproveita nem
        # sobrescreve os erros de outro (lote 46).
        name = config_digest(meta)[:12]
        path = self.cache_dir / f"erros-{name}.npz"
        if path.is_file():
            with np.load(path) as cached:
                if json.loads(str(cached["meta"])) == meta:
                    return self._split(dict(cached), trained)
        arrays = errors_all(trained, prepared)
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
        from aliado.science.deteccao.escore.top_k import top_k_scores

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
            "janela": {"indice": window, "escore": scores[window], "variaveis": list(variaveis.FEATURES),
                       "erros": row, "maiores": largest, "media_todas": float(row.mean()),
                       "media_k": float(row[largest].mean())},
            "canonico": {"k": config.top_k, "percentil": config.percentile,
                         "limiar": state["trained"].thresholds[(kind, int(seed), config.top_k)]},
        })

    # Explorador de alarme e detecção (pós-teste)

    def alarms(self, kind: str, seed: int, k: int, percentile: float, confirmations: int,
               trial: str | None = None) -> dict:
        from aliado.science.deteccao.alarmes.confirmacao import alarm_starts
        from aliado.science.deteccao.escore.top_k import top_k_scores
        from aliado.specializations.mestrado.avaliacao.decisao import run_metrics
        from aliado.specializations.mestrado.preparo.inicio_nominal import nominal_onset

        state, errors = self._ready(kind, seed)
        k, percentile = _k(k), _range(percentile, PERCENTILES, "percentil")
        confirmations = int(_range(confirmations, CONFIRMATIONS, "confirmações"))
        if trial is not None and trial not in ensaios.FAULTY:
            raise ValueError("Ensaio inexistente.")
        calibration = calibrate_threshold(top_k_scores(errors["calibracao"], k), percentile, strict=False)
        scores = {"saudavel": [top_k_scores(errors[f"saudavel_{name}"], k) for name in ensaios.HEALTHY],
                  "ensaios": {name: top_k_scores(errors[name], k) for name in ensaios.FAULTY}}
        prepared = state["prepared"]
        metrics = run_metrics(scores, calibration.value, prepared, confirmations)
        canonical = {row["ensaio"]: row for row in state["canonical_trials"]
                     if row["modelo"] == kind and int(row["semente"]) == int(seed)}
        trials = []
        for name in ensaios.FAULTY:
            fault, physical = ensaios.FAULTS[int(name[1])]
            item, reference = metrics["ensaios"][name], canonical.get(name, {})
            trials.append({
                "ensaio": name, "falha": fault, "fisica": physical, "modo": ensaios.MODES[name[2]],
                "detectado": item["detectado"], "atraso_ms": item["atraso_ms"],
                "alarmes_pre_falha": item["alarmes_pre_falha"],
                # Lote 23: métricas por janela e contagens, para a matriz de confusão dos parâmetros explorados.
                **{key: item.get(key) for key in WINDOW_KEYS},
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
                        "inicio_nominal": nominal_onset(item), "comissionamento": _span(item["comissionamento"]),
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
                "variaveis": len(variaveis.FEATURES), "ensaios": list(ensaios.FAULTY)}


def _k(value) -> int:
    k = int(value)
    if not 1 <= k <= len(variaveis.FEATURES):
        raise ValueError(f"k deve estar entre 1 e {len(variaveis.FEATURES)}.")
    return k


def _range(value, bounds: tuple, label: str) -> float:
    number = float(value)
    if not bounds[0] <= number <= bounds[1]:
        raise ValueError(f"{label} deve estar entre {bounds[0]:g} e {bounds[1]:g}.")
    return number


def _span(indices) -> list[int] | None:
    return [int(indices[0]), int(indices[-1])] if len(indices) else None

