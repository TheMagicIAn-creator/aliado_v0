"""Resultados oficiais do GPVS para a aba Ciência (lote 23): só leitura e só numpy.

Lê a avaliação de 27/09/2026 (relatório, métricas por ensaio e escores) e o treino dela, sem
carregar modelos. Os números são os do treino de referência do relatório; a faixa dos 5
treinamentos repetidos vem do próprio relatório e do CSV. Nada é gravado.

As métricas por tipo de falha somam as contagens de janelas dos modos L e M e recalculam
sensibilidade, especificidade, precisão, F1, acurácia balanceada e MCC com as fórmulas de
`metrics.window_metrics`; AUC e atraso não se somam e entram como a média dos dois modos.
"""

from __future__ import annotations

import csv
import json
import math
import threading
from pathlib import Path

import numpy as np

from aliado.science.detection import gpvs
from aliado.science.detection.metrics import alarm_starts, first_alarm
from aliado.science.detection.threshold import false_alarm_interval

EVALUATION = "gpvs-avaliacao-001"
REANALYSIS_PREFIX = "gpvs-reanalise-"
SECONDARY = ("precisao", "f1", "acuracia_balanceada", "mcc", "auc_roc", "auc_pr")
MODELS = {"denso": "Denso", "lstm": "AE-LSTM"}
SHORT_FAULTS = {1: "Falha em IGBT", 2: "Sensor: −20%", 3: "Afundamento de tensão", 4: "Sombreamento parcial",
                5: "Arranjo FV: 15% aberto", 6: "Ganho PI: −20%", 7: "Constante PI: +20%"}
COUNT_METRICS = ("sensibilidade", "especificidade", "precisao", "f1", "acuracia_balanceada", "mcc")
MEAN_METRICS = ("auc_roc", "auc_pr")
METRICS = COUNT_METRICS + MEAN_METRICS
COMPARISON_NAMES = {"alarmes_pre_falha": "Alarmes antes da falha, por ensaio", "especificidade": "Especificidade",
                    "detectado": "Ensaio detectado (1 ou 0)", "sensibilidade": "Sensibilidade",
                    "atraso_ms": "Atraso (ms), nos ensaios detectados pelos dois"}
WINDOW_S = gpvs.WINDOW / gpvs.SAMPLING_HZ  # uma janela de um ciclo de rede: 20 ms
_cache: dict = {}
_lock = threading.Lock()


def _evaluation(results_dir: str | Path) -> Path:
    folder = Path(results_dir) / EVALUATION
    for name in ("configuracao.json", "relatorio.json", "metricas_por_ensaio.csv"):
        if not (folder / name).is_file():
            raise FileNotFoundError(f"Falta a avaliação oficial de 27/09 ({name}) na pasta de resultados.")
    return folder


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(folder: Path) -> list[dict]:
    """Linhas do CSV com os tipos certos: contagens inteiras, métricas reais e atraso vazio como None."""
    with (folder / "metricas_por_ensaio.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["semente"] = int(row["semente"])
        row["detectado"] = row["detectado"] == "True"
        row["atraso_ms"] = float(row["atraso_ms"]) if row["atraso_ms"] else None
        for key in ("atraso_janelas", "alarmes_pre_falha", "janelas_pre_falha", "vp", "fn", "fp", "vn"):
            row[key] = int(row[key]) if row[key] else None
        for key in METRICS:
            row[key] = float(row[key]) if row[key] not in ("", "None") else None
    return rows


def from_counts(vp: int, fn: int, fp: int, vn: int) -> dict:
    """As mesmas fórmulas de `metrics.window_metrics`, a partir das contagens de janelas."""
    sensitivity, specificity = vp / (vp + fn), vn / (vn + fp)
    denominator = math.sqrt((vp + fp) * (vp + fn) * (vn + fp) * (vn + fn))
    return {"sensibilidade": sensitivity, "especificidade": specificity,
            "precisao": vp / (vp + fp) if vp + fp else None,
            "f1": 2 * vp / (2 * vp + fp + fn) if 2 * vp + fp + fn else 0.0,
            "acuracia_balanceada": (sensitivity + specificity) / 2,
            "mcc": (vp * vn - fp * fn) / denominator if denominator else 0.0,
            "vp": vp, "fn": fn, "fp": fp, "vn": vn}


def _counts(rows) -> dict:
    return {key: sum(row[key] for row in rows) for key in ("vp", "fn", "fp", "vn")}


def trials() -> list[dict]:
    """Os 14 ensaios com o nome curto e o longo da falha, o modo e se a falha é física."""
    items = []
    for name in gpvs.FAULTY:
        fault = int(name[1])
        description, physical = gpvs.FAULTS[fault]
        items.append({"id": name, "falha": f"F{fault}", "nome": SHORT_FAULTS[fault], "descricao": description,
                      "fisica": physical, "modo": name[2], "modo_nome": gpvs.MODES[name[2]]})
    return items


def overview(results_dir: str | Path) -> dict:
    """Cartões por modelo, matrizes de confusão (total, por falha e por ensaio) e a comparação."""
    folder = _evaluation(results_dir)
    report, config = _json(folder / "relatorio.json"), _json(folder / "configuracao.json")
    reference = report["semente_referencia"]
    rows = [row for row in _rows(folder) if row["semente"] == reference]
    training = folder.parent / Path(config["treino"]["pasta"]).name / "relatorio.json"
    limits = _json(training)["modelos"] if training.is_file() else None
    later = reanalysis(results_dir)
    models = {}
    for kind, name in MODELS.items():
        model = report["modelos"][kind]
        own = [row for row in rows if row["modelo"] == kind]
        alarms = model["referencia"]["falsos_alarmes"]
        healthy, pre, combined = alarms["teste_saudavel"], alarms["pre_falha"], alarms["combinado"]
        summary = model["referencia"]["resumo"]
        limit = limits[kind]["sementes"][str(reference)]["limiar"] if limits else None
        estimate = ((later or {}).get("alarmes_estimados") or {}).get(kind)
        if estimate and not all(key in estimate for key in ("alarmes_por_hora", "ic95", "p01", "p11", "previsto", "observado")):
            estimate = None  # reanálise incompleta: o Resumo segue sem a estimativa
        models[kind] = {
            # Os 52 s saudáveis juntos (teste saudável e antes da falha), a fração de janelas acima do
            # limiar em cada trecho, o quanto o limiar pode variar e a estimativa da reanálise (lote 24).
            "saudavel": {"alarmes": combined["alarmes"], "duracao_s": combined["duracao_s"],
                         "alarmes_por_hora": combined["alarmes"] / combined["duracao_s"] * 3600,
                         "limite_superior_por_hora": combined["limite_superior_por_hora"],
                         "janelas": healthy["janelas"] + pre["janelas"],
                         "janelas_acima": healthy["janelas_acima"] + pre["janelas_acima"],
                         "trechos": {part: {"janelas": alarms[part]["janelas"], "janelas_acima": alarms[part]["janelas_acima"],
                                            "fracao": alarms[part]["fracao_janelas_acima"],
                                            "ic95": alarms[part].get("fracao_janelas_acima_ic95")}
                                     for part in ("teste_saudavel", "pre_falha")}},
            "limiar_faixa": None if limit is None else false_alarm_interval(limit["posicao"], limit["n_calibracao"]),
            "alarmes_estimados": None if estimate is None else {
                key: estimate[key] for key in ("alarmes_por_hora", "ic95", "p01", "p11", "previsto", "observado")},
            "nome": name, "limiar": model["limiar"], "ensaios": len(own),
            "detectados": summary["detectados"], "atraso_mediano_ms": summary["atraso_mediano_ms"],
            "metricas": {key: summary[f"{key}_media"] for key in METRICS},
            "teste_saudavel": {key: healthy[key] for key in ("janelas", "janelas_acima", "alarmes", "duracao_s",
                                                             "alarmes_por_hora", "limite_superior_por_hora")},
            "antes_da_falha": {key: pre[key] for key in ("janelas", "janelas_acima", "alarmes", "duracao_s")},
            "faixa": {key.removesuffix("_media"): value for key, value in model["faixa_sementes"].items()},
            "matrizes": {
                "total": _counts(own),
                "por_falha": {f"F{f}": _counts([r for r in own if r["ensaio"][1] == str(f)]) for f in range(1, 8)},
                "por_ensaio": {row["ensaio"]: _counts([row]) for row in own},
            },
        }
    return {"data": config.get("executado_em"), "confirmacoes": report["confirmacao"], "k": report["top_k"],
            "modelos": models, "comparacao": _comparison(report["comparacao"]), "ensaios": trials()}


def per_fault(results_dir: str | Path) -> dict:
    """Métricas por ensaio e por tipo de falha (L + M), com a faixa dos 5 treinamentos repetidos."""
    folder = _evaluation(results_dir)
    report = _json(folder / "relatorio.json")
    reference = report["semente_referencia"]
    rows = _rows(folder)
    result = {}
    for kind in MODELS:
        own = [row for row in rows if row["modelo"] == kind]
        by_trial = {}
        for name in gpvs.FAULTY:
            runs = [row for row in own if row["ensaio"] == name]
            chosen = next(row for row in runs if row["semente"] == reference)
            spread = {key: [min(r[key] for r in runs if r[key] is not None), max(r[key] for r in runs if r[key] is not None)]
                      for key in METRICS if any(r[key] is not None for r in runs)}
            delays = [r["atraso_ms"] for r in runs if r["atraso_ms"] is not None]
            by_trial[name] = {**{key: chosen[key] for key in METRICS}, "detectado": chosen["detectado"],
                              "atraso_ms": chosen["atraso_ms"], "alarmes_pre_falha": chosen["alarmes_pre_falha"],
                              **_counts([chosen]),
                              "faixa": spread | ({"atraso_ms": [min(delays), max(delays)]} if delays else {}),
                              "detectado_em": sum(r["detectado"] for r in runs), "treinamentos": len(runs)}
        by_fault = {}
        for fault in range(1, 8):
            modes = [by_trial[f"F{fault}{mode}"] for mode in "LM"]
            delays = [m["atraso_ms"] for m in modes if m["atraso_ms"] is not None]
            by_fault[f"F{fault}"] = {**from_counts(**_counts(modes)),
                                     **{key: sum(m[key] for m in modes) / 2 for key in MEAN_METRICS},
                                     "atraso_ms": sum(delays) / len(delays) if delays else None,
                                     "detectados": sum(m["detectado"] for m in modes), "ensaios": 2}
        model = report["modelos"][kind]
        overall = model["referencia"]["resumo"]
        result[kind] = {"nome": MODELS[kind], "por_ensaio": by_trial, "por_falha": by_fault,
                        "gerais": {key: {"valor": overall[f"{key}_media"],
                                         "faixa": model["faixa_sementes"][f"{key}_media"]} for key in METRICS}}
    return {"modelos": result, "ensaios": trials(),
            "falhas": [{"id": f"F{f}", "nome": SHORT_FAULTS[f], "descricao": gpvs.FAULTS[f][0],
                        "fisica": gpvs.FAULTS[f][1]} for f in range(1, 8)]}


def _span(indices) -> list[int] | None:
    return [int(indices[0]), int(indices[-1])] if len(indices) else None


def onset(item: dict) -> int:
    """Primeira janela da transição, ou do pós-falha: a mesma regra de `evaluation._onset`, sem o torch."""
    return int(item["transicao"][0]) if len(item["transicao"]) else int(item["pos_falha"][0])


def _ratio(values, threshold: float) -> list[float]:
    return [float(f"{value:.5g}") for value in np.asarray(values, dtype=float) / threshold]


def score_panels(results_dir: str | Path, gpvs_dir: str | Path) -> dict:
    """Escore ÷ limiar de cada janela, as fases, o início nominal e os alarmes, para os dois modelos.

    Os escores são os de `escores.npz` do treino de referência com o k oficial; as fases vêm da
    mesma preparação dos dados do treino. Fica em memória depois da primeira vez."""
    folder = _evaluation(results_dir)
    gpvs_dir = Path(gpvs_dir)
    if not (gpvs_dir / "proveniencia.json").is_file():
        raise FileNotFoundError("Faltam os dados do GPVS para as fases de cada ensaio.")
    key = (str(folder.resolve()), (folder / "escores.npz").stat().st_mtime_ns, str(gpvs_dir.resolve()))
    with _lock:
        if key not in _cache:
            _cache.clear()
            _cache[key] = _panels(folder, gpvs_dir)
        panels = _cache[key]
    return _with_onsets(panels, reanalysis(results_dir))


def _with_onsets(panels: dict, report: dict | None) -> dict:
    """Acrescenta a mudança observada (só a clara) e o atraso desde ela, sem mexer no que fica em memória."""
    if report is None:
        return panels
    trials_ = []
    for panel in panels["ensaios"]:
        trial = report["inicio"]["ensaios"][panel["id"]]
        observed = trial["observado_janela"] if trial["classe"] == "clara" else None
        models = {kind: model | {"atraso_mudanca_ms": report["modelos"][kind]["referencia"]["ensaios"][panel["id"]]["atraso_ms"]
                                 if observed is not None else None}
                  for kind, model in panel["modelos"].items()}
        trials_.append(panel | {"classe": trial["classe"], "inicio_observado": observed, "modelos": models})
    return panels | {"ensaios": trials_, "reanalise": True}


def reanalysis(results_dir: str | Path) -> dict | None:
    """A reanálise mais recente dos escores da avaliação oficial, com o início observado (lote 24)."""
    for folder in sorted(Path(results_dir).glob(f"{REANALYSIS_PREFIX}*"), reverse=True):
        if (folder / "relatorio.json").is_file() and (folder / "configuracao.json").is_file():
            try:
                report = _json(folder / "relatorio.json")
                if report.get("origem", {}).get("avaliacao") == EVALUATION:
                    return report | {"executado_em": _json(folder / "configuracao.json").get("executado_em")}
            except (OSError, ValueError, AttributeError):
                continue  # reanálise ilegível: é secundária e não pode derrubar as visões da avaliação oficial
    return None


def _indicators(summary: dict, trials_count: int) -> dict:
    return {"ensaios": trials_count, "detectados": summary["detectados"], "atraso_mediano_ms": summary["atraso_mediano_ms"],
            **{key: summary[f"{key}_media"] for key in ("sensibilidade", "especificidade", *SECONDARY)}}


def _comparison(rows: list[dict]) -> list[dict]:
    return [{"objetivo": row["objetivo"], "metrica": COMPARISON_NAMES.get(row["metrica"], row["metrica"]),
             "diferenca": row["media"], "ic95": row["ic95"], "ensaios": row["n"], "maior_e_melhor": row["maior_e_melhor"],
             "leitura": row["leitura"]} for row in rows]


def onsets(results_dir: str | Path) -> dict:
    """Início nominal e observado de cada ensaio e os indicadores com cada um (seção Início das falhas)."""
    official = _json(_evaluation(results_dir) / "relatorio.json")
    report = reanalysis(results_dir)
    if report is None:
        raise FileNotFoundError("Ainda não há a reanálise com o início observado das falhas. Ela é feita pelo "
                                "terminal: aliado ciencia reanalisar-gpvs --saida data/resultados/gpvs-reanalise-001")
    start = report["inicio"]
    clear = report["so_mudanca_clara"]
    items = []
    for item in trials():
        trial = start["ensaios"][item["id"]]
        items.append(item | {key: trial[key] for key in ("classe", "nominal_s", "observado_s")}
                     | {"duracao_s": trial["janelas"] * WINDOW_S})
    models, per_trial = {}, {}
    for kind, name in MODELS.items():
        before = official["modelos"][kind]["referencia"]
        after = report["modelos"][kind]["referencia"]
        models[kind] = {"nome": name,
                        "meio": _indicators(before["resumo"], len(before["ensaios"])),
                        "mudanca": _indicators(after["resumo"], len(after["ensaios"])),
                        "clara_meio": _indicators(clear["meio"]["modelos"][kind]["resumo"], len(clear["ensaios"])),
                        "clara_mudanca": _indicators(clear["modelos"][kind]["resumo"], len(clear["ensaios"]))}
        per_trial[kind] = {name_: {"detectado": result["detectado"], "atraso_meio_ms": result["atraso_desde_o_meio_ms"],
                                   "atraso_mudanca_ms": result["atraso_ms"],
                                   "sensibilidade_meio": before["ensaios"][name_]["sensibilidade"],
                                   "sensibilidade_mudanca": result["sensibilidade"],
                                   "especificidade_meio": before["ensaios"][name_]["especificidade"],
                                   "especificidade_mudanca": result["especificidade"]}
                           for name_, result in after["ensaios"].items()}
    return {"data": report["executado_em"], "data_oficial": _json(_evaluation(results_dir) / "configuracao.json").get("executado_em"),
            "penalidade_c": start["penalidade_c"], "controle_saudavel": {
                name: counts[f"{float(start['penalidade_c'])}"] for name, counts in start["controle_saudavel"].items()},
            "ensaios": items, "clara": clear["ensaios"], "modelos": models, "por_ensaio": per_trial,
            "comparacao": {"mudanca": _comparison(report["comparacao"]), "clara": _comparison(clear["comparacao"])}}


def _panels(folder: Path, gpvs_dir: Path) -> dict:
    report, config = _json(folder / "relatorio.json"), _json(folder / "configuracao.json")
    training = _json(Path(folder.parent) / Path(config["treino"]["pasta"]).name / "configuracao.json")["configuracao"]
    reference, k, confirmations = report["semente_referencia"], report["top_k"], report["confirmacao"]
    prepared = gpvs.prepare(gpvs_dir, cache=gpvs_dir / "processado" / "variaveis.npz", purge=training["purge"],
                            fractions=tuple(training["fractions"]))
    rows = {(row["modelo"], row["ensaio"]): row for row in _rows(folder) if row["semente"] == reference}
    thresholds = {kind: report["modelos"][kind]["limiar"] for kind in MODELS}
    panels = []
    with np.load(folder / "escores.npz") as scores:
        for item in trials():
            name, data = item["id"], prepared.faults[item["id"]]
            models = {}
            start, pre = onset(data), data["pre_teste"]
            for kind in MODELS:
                values = scores[f"{kind}_s{reference}_k{k}_{name}"]
                above = values > thresholds[kind]
                row = rows[(kind, name)]
                # A mesma regra da avaliação: alarmes contados só no trecho antes da falha, e a detecção
                # como o primeiro alarme a partir do início (a contagem de janelas recomeça nele).
                first = first_alarm(above[start:], confirmations)
                models[kind] = {"razao": _ratio(values, thresholds[kind]),
                                "alarmes_antes": [int(pre[i]) for i in alarm_starts(above[pre], confirmations)],
                                "alarme_deteccao": None if first is None else start + int(first),
                                "detectado": row["detectado"], "atraso_ms": row["atraso_ms"],
                                "alarmes_pre_falha": row["alarmes_pre_falha"]}
            panels.append(item | {"janelas": len(values), "inicio": onset(data),
                                  "fases": {phase: _span(data[phase]) for phase in
                                            ("comissionamento", "pre_teste", "transicao", "pos_falha")},
                                  "modelos": models})
        healthy = []
        for name in gpvs.HEALTHY:
            models = {}
            for kind in MODELS:
                values = scores[f"{kind}_s{reference}_k{k}_saudavel_{name}"]
                models[kind] = {"razao": _ratio(values, thresholds[kind]),
                                "alarmes_antes": [int(i) for i in alarm_starts(values > thresholds[kind], confirmations)],
                                "alarme_deteccao": None}
            healthy.append({"id": name, "nome": "Teste saudável", "modo": name[2], "modo_nome": gpvs.MODES[name[2]],
                            "janelas": len(values), "modelos": models})
    return {"janela_s": WINDOW_S, "confirmacoes": confirmations, "k": k,
            "modelos": {kind: {"nome": name, "limiar": thresholds[kind]} for kind, name in MODELS.items()},
            "ensaios": panels, "teste_saudavel": healthy}
