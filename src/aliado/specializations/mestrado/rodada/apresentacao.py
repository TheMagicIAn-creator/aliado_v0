"""A apresentação da rodada no PDF: os blocos, só a partir do resultado, para o PDF de uma rodada antiga sair igual
ao de hoje."""

from __future__ import annotations

from aliado.science.identidade.contrato import NOT_RECORDED, PRIOR, check_version, require
from aliado.specializations.mestrado.rodada.declaracao import DESCRIPTION, METRICS

IDENTITY_FIELDS = ("contrato", "codigo", "pesos", "variaveis", "janela", "erros_sha256")
CODE_FIELDS = ("estado", "commit", "alteracoes_locais")
IDENTITY_LABELS = ("Versão do programa (commit do Git)", "Pesos dos modelos", "Matriz de erros por variável")


def identity_rows(result: dict) -> list[list[str]]:
    """As linhas da identidade (lote 54). Uma rodada que declara o contrato precisa de todos os campos; uma anterior a
    ele mostra que não os gravou, sem inventar nenhum."""
    identity = result.get("identidade") or {}
    if check_version(identity, "resultado.json") is None:
        return [[label, f"{NOT_RECORDED} ({PRIOR})"] for label in IDENTITY_LABELS]
    require(identity, IDENTITY_FIELDS, "resultado.json")
    code = identity["codigo"]
    require(code, CODE_FIELDS, "resultado.json, versão do programa")
    version = (code["commit"][:16] + (", com alterações locais" if code["alteracoes_locais"] else "")
               if code["estado"] == "registrado" else code["estado"])
    return [[IDENTITY_LABELS[0], version],
            [IDENTITY_LABELS[1], f"{len(identity['pesos'])} arquivos conferidos; os códigos completos estão no JSON anexo"],
            [IDENTITY_LABELS[2], identity["erros_sha256"][:16]]]


def report(result: dict) -> list[dict]:
    """Os blocos do PDF, só a partir do resultado: o PDF de uma rodada antiga sai igual ao de hoje."""
    from aliado.science.resumo_citavel.formato import dec, num, seconds
    from aliado.specializations.mestrado.glossario.notas import NOTES

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
                    ["Base de dados", f"{len(result['hashes']['dados'])} arquivos conferidos; os códigos completos estão no JSON anexo"],
                    *identity_rows(result)],
         "notas": ["O código de cada arquivo muda com qualquer alteração dele: códigos iguais garantem os mesmos dados e as "
                   "mesmas escolhas.",
                   "Versão do programa: o commit do Git do AL-IAdo que rodou; \"com alterações locais\" quer dizer que havia "
                   "mudanças no código ainda sem commit.",
                   "Matriz de erros: o erro de cada uma das 24 variáveis em cada janela, por modelo e repetição; o código é o "
                   "do conteúdo das matrizes, e não o do arquivo, que guarda a hora em que foi gravado.",
                   "As rodadas anteriores ao contrato de 22/10/2026 não gravaram a versão do programa, os pesos nem a matriz "
                   "de erros no resultado."]},
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
    evidence = detail.get("evidencia_espectral")
    if evidence:  # só as rodadas feitas a partir do lote 55 trazem a evidência no resultado
        from aliado.specializations.mestrado.evidencia_espectral import relatorio as espectral

        blocks += [
            {"tipo": "secao", "titulo": "Evidência espectral no primeiro alarme"},
            {"tipo": "paragrafo", "texto": espectral.ALARM_TEXT},
            {"tipo": "tabela", "legenda": "Harmônicos na janela do primeiro alarme", "colunas": espectral.ALARM_HEADERS,
             "linhas": espectral.alarm_rows(evidence), "numericas": [False, False, True, False, False, *[True] * 6],
             "notas": [f"{label}: {NOTES[key]}" for key, label in (
                 ("fase_maior_erro", "Fase com maior erro"), ("nivel_dc", "Nível DC / fundamental"),
                 ("fundamental_relativa", "Fundamental / comissionamento"), ("thd", "THD"),
                 ("harmonicas", "Harmônicas / fundamental"), ("passo_irregular", "Passo irregular"))]},
            {"tipo": "paragrafo", "texto": espectral.CHANGE_TEXT},
            {"tipo": "tabela", "legenda": "Os dois indicadores que mais mudam em cada ensaio",
             "colunas": espectral.CHANGE_HEADERS,
             "linhas": espectral.change_rows(evidence, {fault["id"]: fault["nome"] for fault in faults["falhas"]}),
             "numericas": [False, False, False, False, True],
             "notas": [f"Mais muda: {NOTES['mais_muda']}",
                       f"Janelas antes da mudança observada: {NOTES['janelas_antes_mudanca']}"]},
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
