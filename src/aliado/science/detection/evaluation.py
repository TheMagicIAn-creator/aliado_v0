"""Avaliação M13 do GPVS (lote 15): a abertura do teste saudável e dos ensaios com falha.

Carrega uma rodada de treino congelada (lote 14) conferindo os hashes, prepara os dados com a
mesma divisão e pontua uma vez, com a configuração de avaliação também congelada. Detectar
não altera S/O/D, NPR nem taxas de falha (M09). Exige o extra `ml`.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import statistics
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import numpy as np

from aliado.science.detection import gpvs
from aliado.science.detection.metrics import (
    BLOCK,
    CONFIRMATIONS,
    RESAMPLES,
    alarm_starts,
    first_alarm,
    paired_interval,
    poisson_upper,
    proportion_interval,
    verdict,
    window_metrics,
)
from aliado.science.detection.models import (
    MODEL_NAMES,
    MODELS,
    Hyperparameters,
    feature_errors,
    load_model,
    top_k_scores,
)
from aliado.science.detection.protocol import sequences_from_flow
from aliado.science.detection.training import ExperimentConfig, environment

SECONDS_PER_HOUR = 3600
SECONDARY = ("precisao", "f1", "acuracia_balanceada", "mcc", "auc_roc", "auc_pr")
# (métrica, maior é melhor?, objetivo) da comparação pareada por ensaio.
PAIRED = (
    ("alarmes_pre_falha", False, "Menos falsos alarmes"),
    ("especificidade", True, "Menos falsos alarmes"),
    ("detectado", True, "Detecta mais falhas"),
    ("sensibilidade", True, "Detecta mais falhas"),
    ("atraso_ms", False, "Detecta mais rápido"),
)
PAIRED_NAMES = {"alarmes_pre_falha": "Alarmes no pré-falha, por ensaio", "especificidade": "Especificidade por janela",
                "detectado": "Ensaio detectado (1/0)", "sensibilidade": "Sensibilidade por janela",
                "atraso_ms": "Atraso (ms), ensaios detectados pelos dois"}


@dataclass(frozen=True)
class EvaluationConfig:
    """Escolhas da avaliação, congeladas antes de pontuar o teste (M14)."""

    confirmations: int = CONFIRMATIONS
    confirmation_grid: tuple[int, ...] = (1, 2, 3, 5)  # só relatada
    block: int = BLOCK  # lag de descorrelação medido no lote 13
    resamples: int = RESAMPLES
    seed: int = 20260927

    def __post_init__(self):
        if self.confirmations not in self.confirmation_grid or min(self.confirmation_grid) < 1:
            raise ValueError("A grade de confirmação deve incluir a principal e só valores positivos.")
        if self.block < 1 or self.resamples < 100:
            raise ValueError("Bloco e reamostragens inválidos.")

    def as_dict(self) -> dict:
        return json.loads(json.dumps(asdict(self)))

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.as_dict(), sort_keys=True).encode("utf-8")).hexdigest()


@dataclass
class TrainedDetectors:
    folder: Path
    config: ExperimentConfig
    frozen: dict
    models: dict  # (modelo, semente) -> rede
    thresholds: dict  # (modelo, semente, k) -> limiar


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_thresholds(folder: str | Path) -> tuple[TrainedDetectors, dict]:
    """Configuração e limiares de uma rodada congelada, conferidos pelo hash, sem carregar os pesos.

    Devolve também o relatório do treino, que guarda o caminho e o hash de cada modelo.
    """
    folder = Path(folder)
    frozen = json.loads((folder / "configuracao.json").read_text(encoding="utf-8"))
    summary = json.loads((folder / "relatorio.json").read_text(encoding="utf-8"))
    raw = frozen["configuracao"]
    config = ExperimentConfig(**(raw | {
        "fractions": tuple(raw["fractions"]), "seeds": tuple(raw["seeds"]),
        "sensitivity_k": tuple(raw["sensitivity_k"]), "hyperparameters": Hyperparameters(**raw["hyperparameters"])}))
    if config.digest() != frozen["sha256"] or summary["configuracao_sha256"] != frozen["sha256"]:
        raise ValueError("A configuração do treino não confere com o hash gravado.")
    thresholds = {(kind, seed, int(k)): float(value)
                  for kind in MODELS for seed in config.seeds
                  for k, value in summary["modelos"][kind]["sementes"][str(seed)]["sensibilidade_k"].items()}
    return TrainedDetectors(folder, config, frozen, {}, thresholds), summary


def load_training(folder: str | Path) -> TrainedDetectors:
    """Rodada de treino congelada, com configuração e pesos conferidos pelos hashes gravados."""
    trained, summary = load_thresholds(folder)
    for kind in MODELS:
        for seed in trained.config.seeds:
            run = summary["modelos"][kind]["sementes"][str(seed)]
            path = trained.folder / run["arquivos"]["modelo"]["caminho"]
            if _sha256(path) != run["arquivos"]["modelo"]["sha256"]:
                raise ValueError(f"Os pesos de {path.name} não conferem com o hash gravado.")
            model, checkpoint = load_model(path)
            if (checkpoint["modelo"], checkpoint["semente"]) != (kind, seed):
                raise ValueError(f"{path.name} não é o modelo {kind} da semente {seed}.")
            trained.models[(kind, seed)] = model
    return trained


def segment_errors(kind: str, model, scaled: np.ndarray, sequence: int) -> np.ndarray:
    """Erro por variável de um trecho contínuo; no AE-LSTM, a 1ª janela só se repete no início do trecho."""
    inputs = np.asarray(scaled, dtype=np.float32) if kind == "denso" else sequences_from_flow(scaled, sequence)
    return feature_errors(model, inputs)


def score_segment(kind: str, model, scaled: np.ndarray, sequence: int, ks) -> dict[int, np.ndarray]:
    errors = segment_errors(kind, model, scaled, sequence)
    return {int(k): top_k_scores(errors, k) for k in ks}


def score_all(trained: TrainedDetectors, prepared: gpvs.PreparedGPVS) -> dict:
    """Escores do teste saudável (por ensaio) e dos 14 ensaios com falha, para cada modelo, semente e k."""
    config = trained.config
    if prepared.hashes != trained.frozen["dados"]["hashes"]:
        raise ValueError("Os dados preparados não são os do treino.")
    if prepared.purge != config.purge or tuple(prepared.fractions) != tuple(config.fractions):
        raise ValueError("Os dados preparados não seguem a divisão do treino.")
    tests = [prepared.split["por_ensaio"][name]["test"] for name in gpvs.HEALTHY]
    scores = {}
    for (kind, seed), model in trained.models.items():
        sequence = config.hyperparameters.sequence
        healthy = [score_segment(kind, model, prepared.scaled[block], sequence, config.sensitivity_k) for block in tests]
        faults = {name: score_segment(kind, model, item["scaled"], sequence, config.sensitivity_k)
                  for name, item in prepared.faults.items()}
        for k in config.sensitivity_k:
            scores[(kind, seed, int(k))] = {"saudavel": [block[k] for block in healthy],
                                            "ensaios": {name: values[k] for name, values in faults.items()}}
    return scores


def _false_alarms(segments, confirmations: int) -> dict:
    windows = sum(len(segment) for segment in segments)
    above = sum(int(np.sum(segment)) for segment in segments)
    alarms = sum(len(alarm_starts(segment, confirmations)) for segment in segments)
    duration = windows / gpvs.GRID_HZ
    return {"janelas": windows, "janelas_acima": above, "fracao_janelas_acima": above / windows,
            "alarmes": alarms, "duracao_s": duration, "alarmes_por_hora": alarms / duration * SECONDS_PER_HOUR,
            "limite_superior_por_hora": poisson_upper(alarms) / duration * SECONDS_PER_HOUR}


def _onset(item: dict) -> int:
    return int(item["transicao"][0]) if len(item["transicao"]) else int(item["pos_falha"][0])


def run_metrics(run_scores: dict, threshold: float, prepared: gpvs.PreparedGPVS, confirmations: int) -> dict:
    """Falsos alarmes, detecção e métricas por janela de um modelo, numa semente e num k."""
    healthy = [values > threshold for values in run_scores["saudavel"]]
    experiments, pre_segments = {}, []
    for name, item in prepared.faults.items():
        values = run_scores["ensaios"][name]
        above = values > threshold
        pre = above[item["pre_teste"]]
        pre_segments.append(pre)
        onset = _onset(item)
        alarm = first_alarm(above[onset:], confirmations)
        meta = prepared.extraction[name]
        delay = None
        if alarm is not None:
            # Do início nominal da falha ao fim da janela que completa a confirmação.
            delay = ((onset + alarm + 1) * gpvs.WINDOW - meta["fronteira_falha_amostra"]) / meta["fs_hz"] * 1000
        experiments[name] = {
            "detectado": alarm is not None, "atraso_ms": delay, "atraso_janelas": None if alarm is None else alarm + 1,
            "alarmes_pre_falha": int(len(alarm_starts(pre, confirmations))), "janelas_pre_falha": int(len(pre)),
            **window_metrics(values[item["pre_teste"]], values[item["pos_falha"]], threshold),
        }
    test, pre_total = _false_alarms(healthy, confirmations), _false_alarms(pre_segments, confirmations)
    total_alarms, total_duration = test["alarmes"] + pre_total["alarmes"], test["duracao_s"] + pre_total["duracao_s"]
    delays = [item["atraso_ms"] for item in experiments.values() if item["detectado"]]
    summary = {
        "detectados": sum(item["detectado"] for item in experiments.values()),
        "atraso_mediano_ms": statistics.median(delays) if delays else None,
        "sensibilidade_media": float(np.mean([item["sensibilidade"] for item in experiments.values()])),
        "especificidade_media": float(np.mean([item["especificidade"] for item in experiments.values()])),
    }
    for metric in SECONDARY:
        values = [item[metric] for item in experiments.values() if item[metric] is not None]
        summary[f"{metric}_media"] = float(np.mean(values)) if values else None
    return {
        "falsos_alarmes": {
            "teste_saudavel": test, "pre_falha": pre_total,
            "combinado": {"alarmes": total_alarms, "duracao_s": total_duration,
                          "limite_superior_por_hora": poisson_upper(total_alarms) / total_duration * SECONDS_PER_HOUR},
        },
        "ensaios": experiments,
        "resumo": summary,
    }


def _seed(base: int, *parts) -> int:
    return base + int(hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:8], 16) % 1_000_000


def _intervals(run_scores, threshold, prepared, metrics: dict, config: EvaluationConfig, kind: str) -> None:
    """Acrescenta os intervalos em blocos (semente de referência): proporções por janela e médias."""
    options = {"block": config.block, "resamples": config.resamples}
    alarms = metrics["falsos_alarmes"]
    alarms["teste_saudavel"]["fracao_janelas_acima_ic95"] = proportion_interval(
        [values > threshold for values in run_scores["saudavel"]], seed=_seed(config.seed, kind, "teste"), **options)
    alarms["pre_falha"]["fracao_janelas_acima_ic95"] = proportion_interval(
        [run_scores["ensaios"][name][item["pre_teste"]] > threshold for name, item in prepared.faults.items()],
        seed=_seed(config.seed, kind, "pre"), **options)
    for name, item in prepared.faults.items():
        values, result = run_scores["ensaios"][name], metrics["ensaios"][name]
        result["sensibilidade_ic95"] = proportion_interval(
            [values[item["pos_falha"]] > threshold], seed=_seed(config.seed, kind, name, "sens"), **options)
        result["especificidade_ic95"] = proportion_interval(
            [values[item["pre_teste"]] <= threshold], seed=_seed(config.seed, kind, name, "espec"), **options)
    for metric in ("sensibilidade", "especificidade"):
        values = [item[metric] for item in metrics["ensaios"].values()]
        metrics["resumo"][f"{metric}_media_ic95"] = paired_interval(
            values, resamples=config.resamples, seed=_seed(config.seed, kind, metric))["ic95"]


def _differences(dense: dict, lstm: dict, metric: str) -> list[float | None]:
    result = []
    for name, item in dense["ensaios"].items():
        a, b = item[metric], lstm["ensaios"][name][metric]
        result.append(None if a is None or b is None else float(a) - float(b))
    return result


def summarize(scores: dict, trained: TrainedDetectors, prepared: gpvs.PreparedGPVS, config: EvaluationConfig) -> dict:
    experiment = trained.config
    k, reference = experiment.top_k, experiment.reference_seed
    runs = {(kind, seed): run_metrics(scores[(kind, seed, k)], trained.thresholds[(kind, seed, k)], prepared,
                                      config.confirmations)
            for kind in MODELS for seed in experiment.seeds}
    for kind in MODELS:
        _intervals(scores[(kind, reference, k)], trained.thresholds[(kind, reference, k)], prepared,
                   runs[(kind, reference)], config, kind)
    models = {}
    for kind in MODELS:
        own = [runs[(kind, seed)] for seed in experiment.seeds]
        spread = {key: [min(values), max(values)] for key in own[0]["resumo"]
                  if not key.endswith("_ic95") and None not in (values := [run["resumo"][key] for run in own])}
        spread["alarmes_teste_saudavel"] = [min(r["falsos_alarmes"]["teste_saudavel"]["alarmes"] for r in own),
                                            max(r["falsos_alarmes"]["teste_saudavel"]["alarmes"] for r in own)]
        spread["alarmes_pre_falha"] = [min(r["falsos_alarmes"]["pre_falha"]["alarmes"] for r in own),
                                       max(r["falsos_alarmes"]["pre_falha"]["alarmes"] for r in own)]
        models[kind] = {"nome": MODEL_NAMES[kind], "limiar": trained.thresholds[(kind, reference, k)],
                        "referencia": runs[(kind, reference)], "faixa_sementes": spread,
                        "sementes": {str(seed): {"resumo": runs[(kind, seed)]["resumo"],
                                                 "alarmes_teste_saudavel": runs[(kind, seed)]["falsos_alarmes"]["teste_saudavel"]["alarmes"],
                                                 "alarmes_pre_falha": runs[(kind, seed)]["falsos_alarmes"]["pre_falha"]["alarmes"]}
                                     for seed in experiment.seeds}}
    comparison = []
    for metric, higher, objective in PAIRED:
        differences = _differences(runs[("denso", reference)], runs[("lstm", reference)], metric)
        result = paired_interval(differences, resamples=config.resamples, seed=_seed(config.seed, "pareado", metric))
        signs = []
        for seed in experiment.seeds:
            values = [d for d in _differences(runs[("denso", seed)], runs[("lstm", seed)], metric) if d is not None]
            signs.append(float(np.sign(np.mean(values))) if values else None)
        reference_sign = signs[experiment.seeds.index(reference)]
        comparison.append({"objetivo": objective, "metrica": metric, "maior_e_melhor": higher, **result,
                           "mesmo_sinal_sementes": sum(sign == reference_sign for sign in signs if sign is not None),
                           "sementes": len(signs), "leitura": verdict(result["ic95"], higher_is_better=higher)})
    grids = {"confirmacao": {}, "k": {}}
    for m in config.confirmation_grid:
        grids["confirmacao"][str(m)] = {kind: _grid_row(run_metrics(scores[(kind, reference, k)],
                                                                    trained.thresholds[(kind, reference, k)], prepared, m))
                                        for kind in MODELS}
    for kk in experiment.sensitivity_k:
        grids["k"][str(kk)] = {kind: _grid_row(run_metrics(scores[(kind, reference, kk)],
                                                           trained.thresholds[(kind, reference, kk)], prepared,
                                                           config.confirmations))
                               for kind in MODELS}
    return {
        "configuracao_sha256": config.digest(),
        "treino_configuracao_sha256": trained.frozen["sha256"],
        "semente_referencia": reference, "top_k": k, "confirmacao": config.confirmations,
        "modelos": models, "comparacao": comparison, "sensibilidade": grids,
        "aviso": "Teste saudável e ensaios com falha consultados; mudanças posteriores exigem avaliação independente (M14).",
    }


def _grid_row(metrics: dict) -> dict:
    alarms = metrics["falsos_alarmes"]
    return {"alarmes_teste_saudavel": alarms["teste_saudavel"]["alarmes"], "alarmes_pre_falha": alarms["pre_falha"]["alarmes"],
            "detectados": metrics["resumo"]["detectados"], "atraso_mediano_ms": metrics["resumo"]["atraso_mediano_ms"]}


def _number(value, digits: int = 1) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _interval(interval, digits: int = 2) -> str:
    return "—" if interval is None else f"[{interval[0]:.{digits}f}; {interval[1]:.{digits}f}]"


def _markdown(summary: dict, trained: TrainedDetectors, config: EvaluationConfig, run_date: str) -> str:
    experiment = trained.config
    reference = str(experiment.reference_seed)
    lines = [
        "# Avaliação M13 — GPVS, Denso × AE-LSTM", "",
        f"Treino `{summary['treino_configuracao_sha256'][:12]}` ({trained.folder.as_posix()}); avaliação "
        f"`{summary['configuracao_sha256'][:12]}`. Alarme com {config.confirmations} janelas seguidas; escore "
        f"top-{experiment.top_k}; limiar p{experiment.percentile:g} da calibração; semente de referência {reference}; "
        f"intervalos de 95% por bootstrap em blocos de {config.block} janelas ({config.resamples} reamostragens).", "",
        f"**O teste saudável e os ensaios com falha foram consultados em {run_date}.** Pelo M14, qualquer mudança "
        "posterior de protocolo exige avaliação independente. Pelo M09, detectar não altera S/O/D, NPR nem taxas de falha.",
        "", f"## Falsos alarmes (semente {reference})", "",
        "| Modelo | Trecho | Tempo (s) | Janelas acima do limiar | Alarmes | Por hora | Limite superior 95% por hora |",
        "|---|---|---:|---|---:|---:|---:|",
    ]
    for item in summary["modelos"].values():
        alarms = item["referencia"]["falsos_alarmes"]
        for label, key in (("Teste saudável", "teste_saudavel"), ("Pré-falha, 14 ensaios", "pre_falha")):
            part = alarms[key]
            lines.append(
                f"| {item['nome']} | {label} | {part['duracao_s']:.1f} | {part['janelas_acima']} de {part['janelas']} "
                f"({100 * part['fracao_janelas_acima']:.2f}%, IC {_interval([100 * v for v in part['fracao_janelas_acima_ic95']])}%) | "
                f"{part['alarmes']} | {part['alarmes_por_hora']:.0f} | {part['limite_superior_por_hora']:.0f} |")
        combined = alarms["combinado"]
        lines.append(f"| {item['nome']} | Os dois juntos | {combined['duracao_s']:.1f} | — | {combined['alarmes']} | "
                     f"{combined['alarmes'] / combined['duracao_s'] * SECONDS_PER_HOUR:.0f} | "
                     f"{combined['limite_superior_por_hora']:.0f} |")
    lines += ["", "Alarmes nas 5 sementes (teste saudável; pré-falha): " + "; ".join(
        f"{item['nome']} {item['faixa_sementes']['alarmes_teste_saudavel'][0]}–{item['faixa_sementes']['alarmes_teste_saudavel'][1]} e "
        f"{item['faixa_sementes']['alarmes_pre_falha'][0]}–{item['faixa_sementes']['alarmes_pre_falha'][1]}"
        for item in summary["modelos"].values()) + "."]
    for item in summary["modelos"].values():
        lines += ["", f"## Detecção por ensaio — {item['nome']} (semente {reference}, limiar {item['limiar']:.4f})", "",
                  "| Ensaio | Falha | Física | Detectada | Atraso (ms) | Sensibilidade [IC 95%] | "
                  "Especificidade [IC 95%] | Alarmes no pré-falha |",
                  "|---|---|---|---|---:|---|---|---:|"]
        for name, result in item["referencia"]["ensaios"].items():
            description, physical = gpvs.FAULTS[int(name[1])]
            lines.append(
                f"| {name} | {description} | {'sim' if physical else 'não'} | {'sim' if result['detectado'] else '**não**'} | "
                f"{_number(result['atraso_ms'])} | {result['sensibilidade']:.3f} {_interval(result['sensibilidade_ic95'], 3)} | "
                f"{result['especificidade']:.3f} {_interval(result['especificidade_ic95'], 3)} | {result['alarmes_pre_falha']} |")
    lines += ["", f"## Resumo por modelo (semente {reference}; entre parênteses, a faixa nas 5 sementes)", "",
              "| Modelo | Ensaios detectados | Atraso mediano (ms) | Sensibilidade média [IC 95%] | "
              "Especificidade média [IC 95%] |", "|---|---|---|---|---|"]
    for item in summary["modelos"].values():
        result, spread = item["referencia"]["resumo"], item["faixa_sementes"]
        delay_spread = spread.get("atraso_mediano_ms")
        lines.append(
            f"| {item['nome']} | {result['detectados']} de 14 ({spread['detectados'][0]}–{spread['detectados'][1]}) | "
            f"{_number(result['atraso_mediano_ms'])} ({_number(delay_spread[0]) if delay_spread else '—'}–"
            f"{_number(delay_spread[1]) if delay_spread else '—'}) | "
            f"{result['sensibilidade_media']:.3f} {_interval(result['sensibilidade_media_ic95'], 3)} "
            f"({spread['sensibilidade_media'][0]:.3f}–{spread['sensibilidade_media'][1]:.3f}) | "
            f"{result['especificidade_media']:.3f} {_interval(result['especificidade_media_ic95'], 3)} "
            f"({spread['especificidade_media'][0]:.3f}–{spread['especificidade_media'][1]:.3f}) |")
    lines += ["", f"## Comparação por objetivo (Denso − AE-LSTM, pareada por ensaio, semente {reference})", "",
              "Não há vencedor geral (M13). \"Sem diferença clara\" significa que o intervalo inclui o zero.", "",
              "| Objetivo | Métrica | Diferença média | IC 95% | Ensaios | Mesmo sinal nas sementes | Leitura |",
              "|---|---|---:|---|---:|---:|---|"]
    for row in summary["comparacao"]:
        lines.append(f"| {row['objetivo']} | {PAIRED_NAMES[row['metrica']]} | {_number(row['media'], 3)} | "
                     f"{_interval(row['ic95'], 3)} | {row['n']} | {row['mesmo_sinal_sementes']}/{row['sementes']} | "
                     f"{row['leitura']} |")
    tests = {item["nome"]: item["referencia"]["falsos_alarmes"]["teste_saudavel"]["alarmes"]
             for item in summary["modelos"].values()}
    lines += ["", "No teste saudável, sem pareamento: " + "; ".join(f"{name} {count} alarme(s)" for name, count in tests.items())
              + ". Ver a tabela de falsos alarmes.",
              "", f"## Métricas secundárias (semente {reference}, média nos 14 ensaios)", "",
              "| Métrica | " + " | ".join(item["nome"] for item in summary["modelos"].values()) + " |", "|---|---:|---:|"]
    labels = {"precisao": "Precisão", "f1": "F1", "acuracia_balanceada": "Acurácia balanceada", "mcc": "MCC",
              "auc_roc": "AUC-ROC", "auc_pr": "AUC-PR"}
    for metric in SECONDARY:
        lines.append(f"| {labels[metric]} | " + " | ".join(
            _number(item["referencia"]["resumo"][f"{metric}_media"], 3) for item in summary["modelos"].values()) + " |")
    lines += ["", "Precisão, F1 e MCC dependem da proporção 1:2 entre pré-falha e pós-falha, fixada pelos registros.",
              "", f"## Sensibilidade (semente {reference}; só relatada)", "",
              "| Variação | Modelo | Alarmes no teste saudável | Alarmes no pré-falha | Detectados | Atraso mediano (ms) |",
              "|---|---|---:|---:|---:|---:|"]
    for group, label in (("confirmacao", "m = {} (k = %d)" % experiment.top_k), ("k", "k = {} (m = %d)" % config.confirmations)):
        for value, per_model in summary["sensibilidade"][group].items():
            for kind, row in per_model.items():
                lines.append(f"| {label.format(value)} | {MODEL_NAMES[kind]} | {row['alarmes_teste_saudavel']} | "
                             f"{row['alarmes_pre_falha']} | {row['detectados']} | {_number(row['atraso_mediano_ms'])} |")
    lines += ["", "## Observações", "",
              "- O início da falha é o meio nominal do registro (os CSVs não trazem canal de disparo): cada atraso "
              "tem incerteza de ±20 ms, uma janela.",
              "- Há só 52 s de operação saudável fora do treino e da calibração: taxas baixas de falso alarme por hora "
              "não podem ser afirmadas, só limitadas por cima.",
              "- 14 ensaios é pouco para a comparação pareada: intervalos largos são esperados."]
    return "\n".join(lines) + "\n"


def _csv(runs_by_seed: dict) -> str:
    stream = io.StringIO()
    fields = ["modelo", "semente", "ensaio", "detectado", "atraso_ms", "atraso_janelas", "alarmes_pre_falha",
              "janelas_pre_falha", "sensibilidade", "especificidade", *SECONDARY, "vp", "fn", "fp", "vn"]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for (kind, seed), metrics in runs_by_seed.items():
        for name, result in metrics["ensaios"].items():
            writer.writerow({"modelo": kind, "semente": seed, "ensaio": name, **result})
    return stream.getvalue()


def export_evaluation(scores: dict, trained: TrainedDetectors, prepared: gpvs.PreparedGPVS,
                      config: EvaluationConfig, output: str | Path) -> dict[str, str]:
    """Configuração congelada, escores, métricas por ensaio e relatório numa pasta nova."""
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=False)
    run_date = date.today().isoformat()
    summary = summarize(scores, trained, prepared, config)
    paths = {"configuracao": folder / "configuracao.json", "relatorio_json": folder / "relatorio.json",
             "relatorio_md": folder / "relatorio.md", "metricas": folder / "metricas_por_ensaio.csv",
             "escores": folder / "escores.npz"}
    frozen = {"avaliacao": config.as_dict(), "sha256": config.digest(), "executado_em": run_date,
              "treino": {"pasta": trained.folder.as_posix(), "configuracao_sha256": trained.frozen["sha256"]},
              "dados": {"conjunto": gpvs.DATASET_NAME, "doi": gpvs.DATASET_DOI, "hashes": prepared.hashes},
              "ambiente": environment()}
    paths["configuracao"].write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    arrays = {}
    for (kind, seed, k), values in scores.items():
        arrays |= {f"{kind}_s{seed}_k{k}_saudavel_{name}": block for name, block in zip(gpvs.HEALTHY, values["saudavel"])}
        arrays |= {f"{kind}_s{seed}_k{k}_{name}": array for name, array in values["ensaios"].items()}
    np.savez_compressed(paths["escores"], **arrays)
    k = trained.config.top_k
    runs = {(kind, seed): run_metrics(scores[(kind, seed, k)], trained.thresholds[(kind, seed, k)], prepared,
                                      config.confirmations)
            for kind in MODELS for seed in trained.config.seeds}
    paths["metricas"].write_text(_csv(runs), encoding="utf-8")
    paths["relatorio_json"].write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                                       encoding="utf-8")
    paths["relatorio_md"].write_text(_markdown(summary, trained, config, run_date), encoding="utf-8")
    return {key: str(path) for key, path in paths.items()}
