"""Experimento AE Denso × AE-LSTM (spec 0034): os dois autoencoders na base GPVS, do preparo ao resumo.

`run` roda o experimento inteiro num processo só, com as mesmas funções dos comandos do terminal:
preparo dos dados, treino dos dois modelos em cada repetição com o limiar p99, avaliação nos ensaios de
teste (uma consulta ao teste, aberta logo antes de pontuá-lo), início observado das falhas e o resumo.
Sem rodada nova, vale a avaliação oficial de 27/09/2026 e a reanálise dela (`legacy`).

O resultado (`collect`) leva os números das mesmas funções da aba Ciência, já formatados como na tela;
o PDF (`report`) sai só dele. Só a biblioteca padrão no topo: numpy e PyTorch entram dentro das funções.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from importlib.util import find_spec
from pathlib import Path

from aliado.science.deteccao.registro import consultas as registry
from aliado.specializations.mestrado.atributos.cache import features_cache
from aliado.specializations.mestrado.base.ensaios import DATA_DIR

KEY = "ae-denso-lstm"
TITLE = "AE Denso × AE-LSTM"
DATASET = "GPVS"
DATASET_DIR = DATA_DIR
CONFIRMATION = registry.PHRASE
DESCRIPTION = ("Compara dois detectores de falhas não supervisionados na base GPVS: um autoencoder denso, que olha "
               "cada janela de 20 ms sozinha, e um autoencoder LSTM, que olha sequências de janelas. Os dois seguem o "
               "mesmo protocolo: divisão do tempo em blocos, limiar no percentil 99 da calibração, alarme com janelas "
               "seguidas acima do limiar e avaliação nos 14 ensaios com falha e no teste saudável.")
DURATION = "cerca de 2 minutos"
LEGACY_EVALUATION = "gpvs-avaliacao-001"
LEGACY_ID = "avaliacao-oficial"
STAGES = {"preparo": "preparo", "modelos": "modelos", "avaliacao": "avaliacao", "inicio": "inicio"}
PARAMETERS = (
    {"nome": "separacao", "rotulo": "Separação entre blocos", "tipo": "inteiro", "padrao": 11, "minimo": 0,
     "maximo": 200, "unidade": "janelas",
     "nota": "Janelas descartadas entre os blocos de treino, validação, calibração e teste, para um bloco não "
             "vazar no outro. 11 é a decisão de 27/09/2026."},
    {"nome": "sementes", "rotulo": "Repetições do treino", "tipo": "inteiros", "padrao": [13, 29, 42, 71, 101],
     "minimo": 0, "ordenar": True,
     "nota": "Um número por repetição do treino, separados por vírgula: cada um fixa o ponto de partida aleatório. "
             "Os números mostrados são os da repetição de referência (42, se estiver na lista), e a faixa vai do "
             "menor ao maior valor das repetições."},
    {"nome": "teto_epocas", "rotulo": "Teto de épocas", "tipo": "inteiro", "padrao": 2000, "minimo": 1,
     "maximo": 100_000,
     "nota": "Limite de segurança do treino; quem o encerra é a perda na validação. 150 repete a pesquisa de origem."},
)
METRICS = (("sensibilidade", "Sensibilidade"), ("especificidade", "Especificidade"), ("precisao", "Precisão"),
           ("f1", "F1"), ("mcc", "MCC"), ("auc_roc", "AUC-ROC"), ("auc_pr", "AUC-PR"))


def missing(dataset_dir: str | Path) -> list[str]:
    """O que falta neste computador para rodar, sem importar numpy nem PyTorch."""
    absent = [] if (Path(dataset_dir) / "proveniencia.json").is_file() else [f"a base de dados {DATASET} em {dataset_dir}"]
    return absent + [f"o {name} (extra 'ml')" for module, name in (("numpy", "numpy"), ("torch", "PyTorch"))
                     if find_spec(module) is None]


def consultations(results_dir: str | Path) -> int:
    """Quantas vezes os dados de teste já foram usados, pelo registro de consultas."""
    return len(registry.consultations(results_dir, LEGACY_EVALUATION))


def interrupted(results_dir: str | Path, folder: str | Path, state: str) -> None:
    """O processo parou antes de fechar a consulta (cancelado ou com erro): ela é fechada aqui."""
    output = Path(folder).resolve().relative_to(Path(results_dir).resolve()).as_posix()
    registry.close_open(results_dir, output, "cancelada" if state == "cancelado" else "falhou")


def run(params: dict, folder: str | Path, *, results_dir: str | Path, dataset_dir: str | Path, phrase: str,
        progress=print) -> dict:
    """O experimento inteiro, numa pasta nova, com os parâmetros já conferidos; devolve o resultado."""
    from aliado.science.deteccao.redes.autoencoders import Hyperparameters
    from aliado.specializations.mestrado import reanalysis, summary
    from aliado.specializations.mestrado.evaluation import (
        EvaluationConfig,
        export_evaluation,
        load_training,
        score_all,
    )
    from aliado.specializations.mestrado.preparo import artefatos as artefatos_do_preparo
    from aliado.specializations.mestrado.preparo import preparacao
    from aliado.specializations.mestrado.preparo import resumo as resumo_do_preparo
    from aliado.specializations.mestrado.treino.artefatos import export_training
    from aliado.specializations.mestrado.treino.configuracao import ExperimentConfig
    from aliado.specializations.mestrado.treino.detectores import train_detectors, training_blocks

    started = time.monotonic()
    folder, results_dir, dataset_dir = Path(folder), Path(results_dir), Path(dataset_dir)
    output = folder.resolve().relative_to(results_dir.resolve()).as_posix()
    cache = features_cache(dataset_dir)
    seeds = tuple(params["sementes"])
    config = ExperimentConfig(purge=params["separacao"], seeds=seeds, reference_seed=42 if 42 in seeds else seeds[0],
                              hyperparameters=Hyperparameters(max_epochs=params["teto_epocas"]))
    progress(f"Preparando a base de dados, com {config.purge} janelas entre os blocos…")
    prepared = preparacao.prepare(dataset_dir, cache=cache, purge=config.purge, fractions=config.fractions)
    artefatos_do_preparo.export_preparation(prepared, resumo_do_preparo.report(prepared), folder / STAGES["preparo"])
    progress(f"Treinando os dois modelos em {len(seeds)} repetições…")
    runs = train_detectors(prepared.scaled, training_blocks(prepared), config, progress=progress)
    export_training(runs, prepared, config, folder / STAGES["modelos"])
    trained = load_training(folder / STAGES["modelos"])  # confere os hashes do que acabou de ser gravado
    number = registry.start(results_dir, training=f"{output}/{STAGES['modelos']}", training_sha=trained.frozen["sha256"],
                            output=output, phrase=phrase, canonical=LEGACY_EVALUATION, origin="experimento")
    progress(f"Pontuando os ensaios de teste: é a {number}ª vez que os dados de teste são usados…")
    try:
        export_evaluation(score_all(trained, prepared), trained, prepared, EvaluationConfig(), folder / STAGES["avaliacao"])
        progress("Procurando quando cada falha aparece nos sinais…")
        reanalysis.run(folder / STAGES["avaliacao"], folder / STAGES["modelos"], dataset_dir, folder / STAGES["inicio"],
                       cache=cache)
    except BaseException:
        registry.finish(results_dir, number, "falhou")
        raise
    registry.finish(results_dir, number, "concluida")
    progress("Montando o resumo…")
    return collect(summary.Run(folder / STAGES["avaliacao"], folder / STAGES["inicio"], False, folder.name, number),
                   params, executed=datetime.now().astimezone().isoformat(timespec="seconds"),
                   duration=time.monotonic() - started)


def legacy(results_dir: str | Path) -> dict | None:
    """A avaliação oficial de 27/09 e a reanálise dela, no formato de uma rodada; None se faltarem."""
    from aliado.specializations.mestrado import summary

    results_dir = Path(results_dir)
    try:
        evaluation = _json(results_dir / LEGACY_EVALUATION / "configuracao.json")
        training = _json(results_dir / Path(evaluation["treino"]["pasta"]).name / "configuracao.json")["configuracao"]
        params = {"separacao": training["purge"], "sementes": sorted(training["seeds"]),
                  "teto_epocas": training["hyperparameters"]["max_epochs"]}
        run_ = summary.Run(results_dir / LEGACY_EVALUATION, summary._legacy_reanalysis(results_dir), True, LEGACY_ID, 1)
        return collect(run_, params, executed=evaluation.get("executado_em"))
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


def collect(run_, params: dict, *, executed: str | None, duration: float | None = None) -> dict:
    """O resultado da rodada: identificação, parâmetros, hashes, os indicadores e as visões da aba."""
    from aliado.experiments import FORMAT
    from aliado.specializations.mestrado import summary

    overview, faults = summary.overview(run_), summary.per_fault(run_)
    try:
        onsets = summary.onsets(run_)
    except (FileNotFoundError, KeyError, ValueError):
        onsets = None
    evaluation = _json(run_.evaluation / "configuracao.json")
    training_dir = run_.evaluation.parent / Path(evaluation["treino"]["pasta"]).name
    training = _json(training_dir / "configuracao.json")
    onset = _json(run_.reanalysis / "configuracao.json") if onsets and run_.reanalysis else None
    hp = training["configuracao"]["hyperparameters"]
    return {
        "formato": FORMAT, "experimento": KEY, "titulo": TITLE, "base": DATASET, "rodada": run_.id,
        "oficial": run_.official, "rotulo": summary.label(run_, evaluation.get("executado_em"))["rotulo"],
        "consulta": run_.consultation, "executado_em": executed, "avaliado_em": evaluation.get("executado_em"),
        "duracao_s": None if duration is None else round(duration, 1), "versao": _version(),
        "parametros": params, "parametros_texto": parameter_texts(params), "comando": command(params),
        "protocolo": {"fracoes": training["configuracao"]["fractions"], "k": training["configuracao"]["top_k"],
                      "percentil": training["configuracao"]["percentile"], "confirmacoes": overview["confirmacoes"],
                      "sequencia": hp["sequence"], "paciencia": hp["patience"]},
        "hashes": {"treino": training["sha256"], "avaliacao": evaluation["sha256"],
                   "inicio": onset["sha256"] if onset else None, "dados": evaluation["dados"]["hashes"]},
        "ambiente": training.get("ambiente"),
        "numeros": numbers(overview, onsets),
        "detalhe": {"resumo": overview, "metricas": faults, "inicio": onsets},
    }


def numbers(overview: dict, onsets: dict | None) -> dict:
    """Os indicadores que o Markdown, o PDF e a comparação mostram, com o texto da tela e a nota."""
    from aliado.science.resumo_citavel.formato import dec, num, seconds
    from aliado.specializations.mestrado.notes import NOTES

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


def report(result: dict) -> list[dict]:
    """Os blocos do PDF, só a partir do resultado: o PDF de uma rodada antiga sai igual ao de hoje."""
    from aliado.science.resumo_citavel.formato import dec, num, seconds
    from aliado.specializations.mestrado.notes import NOTES

    detail, protocol = result["detalhe"], result["protocolo"]
    overview, faults, onsets = detail["resumo"], detail["metricas"], detail.get("inicio")
    models = overview["modelos"]
    names = [model["nome"] for model in models.values()]
    repetitions = overview.get("treinamentos") or len(result["parametros"]["sementes"])

    def spread(value, pair, formatter):
        return f"{formatter(value)} ({formatter(pair[0])} a {formatter(pair[1])})" if pair else formatter(value)

    status = ("É a avaliação oficial da pesquisa." if result.get("oficial") else
              "É uma rodada feita depois da avaliação oficial de 27/09/2026, que continua sendo a oficial. Estes "
              "números não devem escolher ajustes: os ensaios de teste deixariam de ser um teste independente.")
    blocks = [
        {"tipo": "secao", "titulo": "Objetivo"},
        {"tipo": "paragrafo", "texto": DESCRIPTION},
        {"tipo": "paragrafo", "texto": "Não há vencedor geral: cada objetivo é comparado à parte, com a diferença "
                                       "pareada por ensaio e o intervalo de 95%."},
        {"tipo": "secao", "titulo": "Rodada e reprodutibilidade"},
        {"tipo": "paragrafo", "texto": f"{result['rotulo']}. {status}"},
        {"tipo": "tabela", "legenda": "Parâmetros da rodada", "colunas": ["Parâmetro", "Valor", "O que é"],
         "linhas": [[item["rotulo"], item["texto"], item["nota"]] for item in result["parametros_texto"]],
         "numericas": [False, False, False]},
        {"tipo": "tabela", "legenda": "Escolhas fixas do protocolo", "colunas": ["Escolha", "Valor"], "numericas": [False, False],
         "linhas": [["Divisão do tempo: treino, validação, calibração e teste",
                     " / ".join(num(100 * part) for part in protocol["fracoes"]) + " %"],
                    ["Escore de cada janela", f"média dos {protocol['k']} maiores erros por variável"],
                    ["Limiar", f"percentil {num(protocol['percentil'])} dos escores de calibração"],
                    ["Alarme", f"{protocol['confirmacoes']} janelas seguidas acima do limiar"],
                    ["Sequência do AE-LSTM", f"{protocol['sequencia']} janelas de 20 ms"],
                    ["Parada do treino", f"{protocol['paciencia']} épocas sem melhora na validação"]]},
        {"tipo": "tabela", "legenda": "Conferência dos arquivos (SHA-256, início do código)", "colunas": ["Item", "Código"],
         "numericas": [False, False],
         "linhas": [["Configuração do treino", result["hashes"]["treino"][:16]],
                    ["Configuração da avaliação", result["hashes"]["avaliacao"][:16]],
                    *([["Configuração do início das falhas", result["hashes"]["inicio"][:16]]] if result["hashes"].get("inicio") else []),
                    ["Base de dados", f"{len(result['hashes']['dados'])} arquivos conferidos; os códigos completos estão no JSON anexo"]],
         "notas": ["O código de cada arquivo muda com qualquer alteração dele: códigos iguais garantem os mesmos dados e as "
                   "mesmas escolhas."]},
        {"tipo": "paragrafo", "texto": "Para rodar de novo pelo terminal, com os mesmos parâmetros:"},
        {"tipo": "codigo", "texto": result["comando"]},
    ]
    environment = result.get("ambiente") or {}
    if environment:
        blocks.append({"tipo": "paragrafo", "texto": f"Ambiente do treino: Python {environment.get('python')}, PyTorch "
                       f"{environment.get('torch')}, numpy {environment.get('numpy')}, {environment.get('threads')} "
                       f"threads de processamento."})
    rows = [["Ensaios detectados, de 14", *[spread(m["detectados"], m["faixa"].get("detectados"), str) for m in models.values()]],
            ["Atraso mediano", *[spread(m["atraso_mediano_ms"], m["faixa"].get("atraso_mediano_ms"), seconds)
                                 for m in models.values()]],
            ["Alarmes falsos por hora", *[num(m["saudavel"]["alarmes_por_hora"]) for m in models.values()]],
            ["Limite superior de 95% por hora", *[num(m["saudavel"]["limite_superior_por_hora"]) for m in models.values()]]]
    rows += [[label, *[spread(m["metricas"][key], m["faixa"].get(key), dec) for m in models.values()]] for key, label in METRICS]
    blocks += [
        {"tipo": "secao", "titulo": "Resultados por modelo"},
        {"tipo": "paragrafo", "texto": f"Os números são os da repetição de referência; entre parênteses, o menor e o maior "
                                       f"valor nas {repetitions} repetições do treino. As métricas por janela são a média "
                                       f"dos 14 ensaios."},
        {"tipo": "tabela", "legenda": "Indicadores por modelo", "colunas": ["Indicador", *names],
         "linhas": rows, "numericas": [False, *[True] * len(names)],
         "notas": [f"{label}: {NOTES[key]}" for key, label in (("detectados", "Ensaios detectados"), ("atraso", "Atraso"),
                                                               ("alarme", "Alarme"), ("limite_superior", "Limite superior"),
                                                               ("mcc", "MCC"))]},
        {"tipo": "secao", "titulo": "Comparação entre os modelos"},
        {"tipo": "tabela", "legenda": f"Diferença {names[0]} − {names[1]} por objetivo",
         "colunas": ["Objetivo", "Métrica", "Diferença", "Intervalo de 95%", "Leitura"],
         "linhas": [[row["objetivo"], row["metrica"], num(row["diferenca"]),
                     f"{num(row['ic95'][0])} a {num(row['ic95'][1])}" if row.get("ic95") else "—", row["leitura"]]
                    for row in overview["comparacao"]],
         "numericas": [False, False, True, True, False], "notas": [f"Intervalo de 95%: {NOTES['ic95']}"]},
        {"tipo": "secao", "titulo": "Resultados por tipo de falha"},
        {"tipo": "paragrafo", "texto": "Cada falha tem dois ensaios: L, com a potência limitada, e M, com a potência "
                                       "máxima. Sensibilidade, especificidade e MCC somam as janelas dos dois; o atraso "
                                       "é a média dos ensaios detectados."},
    ]
    for kind, model in faults["modelos"].items():
        blocks.append({"tipo": "tabela", "legenda": f"{model['nome']}: resultados por tipo de falha",
                       "colunas": ["Falha", "Detectados", "Sensibilidade", "Especificidade", "MCC", "Atraso"],
                       "numericas": [False, True, True, True, True, True],
                       "linhas": [[f"{fault['id']} · {fault['nome']}", f"{model['por_falha'][fault['id']]['detectados']} de 2",
                                   dec(model["por_falha"][fault["id"]]["sensibilidade"]),
                                   dec(model["por_falha"][fault["id"]]["especificidade"]),
                                   dec(model["por_falha"][fault["id"]]["mcc"]),
                                   seconds(model["por_falha"][fault["id"]]["atraso_ms"])] for fault in faults["falhas"]]})
    if onsets:
        clear = len(onsets["clara"])
        columns = (("meio", "14 · meio"), ("mudanca", "14 · mudança"), ("clara_meio", f"{clear} claros · meio"),
                   ("clara_mudanca", f"{clear} claros · mudança"))
        indicator_rows = []
        for model in onsets["modelos"].values():
            indicator_rows += [[f"{model['nome']} · detectados", *[f"{model[c]['detectados']} de {model[c]['ensaios']}"
                                                                   for c, _ in columns]],
                               [f"{model['nome']} · atraso mediano", *[seconds(model[c]["atraso_mediano_ms"]) for c, _ in columns]],
                               [f"{model['nome']} · sensibilidade", *[dec(model[c]["sensibilidade"]) for c, _ in columns]],
                               [f"{model['nome']} · especificidade", *[dec(model[c]["especificidade"]) for c, _ in columns]]]
        blocks += [
            {"tipo": "secao", "titulo": "Início das falhas"},
            {"tipo": "paragrafo", "texto": "Os arquivos da base não marcam o instante do disparo de cada falha. A avaliação "
                                           "usa o meio do registro; aqui, um detector de mudança sobre as 24 variáveis, sem "
                                           "os autoencoders, mostra quando a falha aparece nos sinais. Só os ensaios de "
                                           "mudança clara passam a usá-la."},
            {"tipo": "tabela", "legenda": "Quando cada falha aparece nos sinais",
             "colunas": ["Ensaio", "Falha", "Meio do registro", "Mudança observada", "Classe"],
             "numericas": [False, False, True, True, False],
             "linhas": [[item["id"], item["nome"], f"{dec(item['nominal_s'], 2)} s",
                         "—" if item["observado_s"] is None else f"{dec(item['observado_s'], 2)} s", item["classe"]]
                        for item in onsets["ensaios"]],
             "notas": [f"Mudança observada: {NOTES['mudanca']}"]},
            {"tipo": "tabela", "legenda": "Indicadores com cada início", "colunas": ["Indicador", *[label for _, label in columns]],
             "linhas": indicator_rows, "numericas": [False, True, True, True, True],
             "notas": [f"Trecho entre o meio e a mudança: {NOTES['trecho_incerto']}"]},
        ]
    blocks += [
        {"tipo": "secao", "titulo": "Limites"},
        {"tipo": "lista", "itens": [
            "Há só cerca de 52 s de operação saudável fora do treino e da calibração: taxas baixas de alarme falso por hora "
            "não podem ser afirmadas, só limitadas por cima.",
            "14 ensaios é pouco para a comparação pareada; intervalos largos são esperados.",
            "A mudança observada é onde a falha aparece nas variáveis, não o instante do disparo; a resolução é de uma "
            "janela (20 ms).",
            "F4 não muda as 24 variáveis, e F6 e F7 mudam pouco: para eles, a falta de detecção é em boa parte das "
            "variáveis, não só dos modelos.",
            "Os números de cada modelo são os da repetição de referência; a faixa entre parênteses mostra o quanto eles "
            "mudam só por repetir o treino."]},
        {"tipo": "secao", "titulo": "Arquivo anexo"},
        {"tipo": "paragrafo", "texto": "O resultado.json com todos os números desta rodada vai anexado a este PDF. Na aba "
                                       "Ciência, \"Comparar com resultado salvo\" lê esse anexo e mostra a rodada guardada "
                                       "ao lado da atual, indicador por indicador, e pode reaplicar os parâmetros dela."},
    ]
    return blocks
