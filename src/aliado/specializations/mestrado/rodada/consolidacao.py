"""A consolidação do resultado da rodada: a identificação, os parâmetros, os hashes, os indicadores e as visões da aba;
e a avaliação oficial de 27/09 no mesmo formato (`legacy`)."""

from __future__ import annotations

import json
from pathlib import Path

from aliado.science.identidade.contrato import PRIOR
from aliado.specializations.mestrado.rodada.declaracao import (
    CONFIRMATION,
    DATASET,
    KEY,
    LEGACY_EVALUATION,
    LEGACY_ID,
    METRICS,
    PARAMETERS,
    TITLE,
)


def legacy(results_dir: str | Path) -> dict | None:
    """A avaliação oficial de 27/09 e a reanálise dela, no formato de uma rodada; None se faltarem."""
    from aliado.specializations.mestrado.resultados import rodada_atual

    results_dir = Path(results_dir)
    try:
        evaluation = _json(results_dir / LEGACY_EVALUATION / "configuracao.json")
        training = _json(results_dir / Path(evaluation["treino"]["pasta"]).name / "configuracao.json")["configuracao"]
        params = {"separacao": training["purge"], "sementes": sorted(training["seeds"]),
                  "teto_epocas": training["hyperparameters"]["max_epochs"]}
        run_ = rodada_atual.Run(results_dir / LEGACY_EVALUATION, rodada_atual._legacy_reanalysis(results_dir), True, LEGACY_ID, 1)
        return collect(run_, params, executed=evaluation.get("executado_em"), identity={"contrato": None, "estado": PRIOR})
    except (OSError, KeyError, ValueError, TypeError):
        return None


def _json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("aliado")
    except PackageNotFoundError:
        return "desenvolvimento"


def parameter_texts(params: dict) -> list[dict]:
    from aliado.science.resumo_citavel.formato import num

    texts = {"separacao": f"{params['separacao']} janelas", "sementes": ", ".join(str(s) for s in params["sementes"]),
             "teto_epocas": num(params["teto_epocas"], 6)}
    return [{"nome": item["nome"], "rotulo": item["rotulo"], "texto": texts[item["nome"]], "nota": item["nota"]}
            for item in PARAMETERS]


def command(params: dict) -> str:
    values = {"separacao": params["separacao"], "sementes": ",".join(str(s) for s in params["sementes"]),
              "teto_epocas": params["teto_epocas"]}
    return (f"aliado experimento rodar {KEY} " + " ".join(f"--parametro {key}={value}" for key, value in values.items())
            + f' --frase "{CONFIRMATION}"')


def collect(run_, params: dict, *, executed: str | None, identity: dict, duration: float | None = None) -> dict:
    """O resultado da rodada: identificação, parâmetros, hashes, a identidade (lote 54), os indicadores e as visões
    da aba. A identidade vem sempre de quem chama: a de uma rodada nova, ou a marca de anterior ao contrato."""
    from aliado.experiments import FORMAT
    from aliado.specializations.mestrado.resultados import paineis, rodada_atual

    overview, faults = paineis.overview(run_), paineis.per_fault(run_)
    try:
        onsets = paineis.onsets(run_)
    except (FileNotFoundError, KeyError, ValueError):
        onsets = None
    evaluation = _json(run_.evaluation / "configuracao.json")
    training_dir = run_.evaluation.parent / Path(evaluation["treino"]["pasta"]).name
    training = _json(training_dir / "configuracao.json")
    onset = _json(run_.reanalysis / "configuracao.json") if onsets and run_.reanalysis else None
    hp = training["configuracao"]["hyperparameters"]
    return {
        "formato": FORMAT, "experimento": KEY, "titulo": TITLE, "base": DATASET, "rodada": run_.id,
        "oficial": run_.official, "rotulo": rodada_atual.label(run_, evaluation.get("executado_em"))["rotulo"],
        "consulta": run_.consultation, "executado_em": executed, "avaliado_em": evaluation.get("executado_em"),
        "duracao_s": None if duration is None else round(duration, 1), "versao": _version(),
        "parametros": params, "parametros_texto": parameter_texts(params), "comando": command(params),
        "protocolo": {"fracoes": training["configuracao"]["fractions"], "k": training["configuracao"]["top_k"],
                      "percentil": training["configuracao"]["percentile"], "confirmacoes": overview["confirmacoes"],
                      "sequencia": hp["sequence"], "paciencia": hp["patience"]},
        "hashes": {"treino": training["sha256"], "avaliacao": evaluation["sha256"],
                   "inicio": onset["sha256"] if onset else None, "dados": evaluation["dados"]["hashes"]},
        "identidade": identity,
        "ambiente": training.get("ambiente"),
        "numeros": numbers(overview, onsets),
        "detalhe": {"resumo": overview, "metricas": faults, "inicio": onsets},
    }


def numbers(overview: dict, onsets: dict | None) -> dict:
    """Os indicadores que o Markdown, o PDF e a comparação mostram, com o texto da tela e a nota."""
    from aliado.science.resumo_citavel.formato import dec, num, seconds
    from aliado.specializations.mestrado.glossario.notas import NOTES

    found = {}

    def add(key, label, value, text, note):
        found[key] = {"rotulo": label, "valor": value, "texto": text, "nota": note}

    for kind, model in overview["modelos"].items():
        name, healthy = model["nome"], model["saudavel"]
        add(f"{kind}.detectados", f"{name} · ensaios detectados", model["detectados"],
            f"{model['detectados']} de {model['ensaios']}", NOTES["detectados"])
        add(f"{kind}.atraso_mediano_ms", f"{name} · atraso mediano", model["atraso_mediano_ms"],
            seconds(model["atraso_mediano_ms"]), NOTES["atraso"])
        add(f"{kind}.alarmes_por_hora", f"{name} · alarmes falsos por hora", healthy["alarmes_por_hora"],
            num(healthy["alarmes_por_hora"]), NOTES["alarme"])
        add(f"{kind}.limite_superior_por_hora", f"{name} · limite superior de 95% por hora",
            healthy["limite_superior_por_hora"], num(healthy["limite_superior_por_hora"]), NOTES["limite_superior"])
        for key, label in METRICS:
            add(f"{kind}.{key}", f"{name} · {label}", model["metricas"][key], dec(model["metricas"][key]), NOTES[key])
    for kind, model in (onsets or {}).get("modelos", {}).items():
        changed = model["mudanca"]
        add(f"{kind}.mudanca.detectados", f"{model['nome']} · detectados, com a mudança observada", changed["detectados"],
            f"{changed['detectados']} de {changed['ensaios']}", NOTES["mudanca"])
        add(f"{kind}.mudanca.atraso_mediano_ms", f"{model['nome']} · atraso mediano desde a mudança",
            changed["atraso_mediano_ms"], seconds(changed["atraso_mediano_ms"]), NOTES["mudanca"])
        add(f"{kind}.mudanca.sensibilidade", f"{model['nome']} · sensibilidade, com a mudança observada",
            changed["sensibilidade"], dec(changed["sensibilidade"]), NOTES["trecho_incerto"])
    return found
