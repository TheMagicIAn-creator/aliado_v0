"""Resumo dos resultados da pesquisa para o chat (lote 26): blocos [R1]…[R8] gerados por código.

Os números saem das mesmas funções da aba Ciência (`summary`, `fmeca` e `components`), nunca dos
relatórios em markdown, e vão no formato da tela. Cada bloco diz a fonte, a data e o estatuto:
a avaliação de 27/09/2026 é a oficial, e a reanálise com o início observado é secundária. O que
não puder ser montado (sem numpy, sem a avaliação ou sem a reanálise) fica de fora, com o motivo
em palavras. O módulo abre sem numpy: `summary` só é importado dentro da função que o usa.
"""

from __future__ import annotations

import json
import threading
from decimal import Decimal
from pathlib import Path

MAX_CHARS = 16_000
HEADER = ("A avaliação oficial é a de 27/09/2026 (treino de referência). A reanálise de 30/09/2026, com o "
          "início observado das falhas, é secundária: complementa, não substitui.")
OFFICIAL, SECONDARY = "oficial", "secundaria"
MODELS = (("denso", "Denso"), ("lstm", "AE-LSTM"))
METRICS = (("sensibilidade", "Sensibilidade"), ("especificidade", "Especificidade"), ("precisao", "Precisão"),
           ("f1", "F1"), ("acuracia_balanceada", "Acurácia balanceada"), ("mcc", "MCC"), ("auc_roc", "AUC-ROC"),
           ("auc_pr", "AUC-PR"))
BASES = (("operation", "operação, 4.015 h/ano"), ("calendar", "calendário, 8.760 h/ano"))
CLASSES = {"clara": "clara", "fraca": "fraca (não usada)", "nenhuma": "nenhuma"}
REPAIR_NAMES = {"ieee493": "IEEE 493", "baschel": "Baschel"}
# As mesmas notas da aba Ciência (GLOSSARIO em graficos.js); um teste compara os textos.
NOTES = {
    "sensibilidade": "Das janelas depois do início da falha, a fração que o modelo marcou como anormais (acima do limiar). 1 = marcou todas.",
    "especificidade": "Das janelas saudáveis antes da falha, a fração que o modelo deixou abaixo do limiar. 1 = nenhum falso positivo.",
    "precisao": "Das janelas que o modelo marcou como anormais, a fração que era mesmo de falha. Depende da proporção entre janelas saudáveis e com falha.",
    "f1": "Média harmônica entre precisão e sensibilidade, de 0 a 1. Só é alta quando as duas são.",
    "acuracia_balanceada": "Média entre sensibilidade e especificidade. 0,5 equivale a sortear.",
    "auc_roc": "Área sob a curva ROC: a chance de uma janela com falha ter escore maior que uma saudável, sem depender do limiar. 0,5 = sorteio; 1 = separação perfeita.",
    "auc_pr": "Área sob a curva de precisão por sensibilidade, sem depender do limiar. O valor de sorteio é a fração de janelas com falha, cerca de 2/3 aqui.",
    "mcc": "Coeficiente de Matthews: resume a matriz de confusão num número de −1 a 1. 0 equivale a sortear e 1 é perfeito. Engana-se menos quando uma classe é bem maior que a outra.",
    "detectados": "Ensaios com falha em que houve alarme a partir do início da falha, de 14.",
    "atraso": "Tempo do início nominal da falha (o meio do registro) até o alarme, no fim da janela que o confirma. O atraso mediano usa só os ensaios detectados.",
    "alarme": "Um alarme dispara quando 3 janelas seguidas ficam acima do limiar. Enquanto o escore continua acima, é o mesmo alarme.",
    "limite_superior": "Limite superior de 95% (Poisson) para os alarmes falsos por hora. Com pouco tempo de observação, mesmo sem nenhum alarme o limite fica alto: é falta de tempo, não excesso de alarmes.",
    "ic95": "Intervalo de 95% da diferença entre os modelos, reamostrando os ensaios. Se ele inclui o zero, não há diferença clara.",
    "mudanca": "Mudança observada: o primeiro instante, depois do comissionamento, em que a média das 24 variáveis do ensaio muda de patamar. Vem de um detector de mudança sobre os sinais, sem os autoencoders.",
    "trecho_incerto": "Entre o meio do registro e a mudança observada pode haver falha ainda invisível. Essas janelas ficam fora da sensibilidade e da especificidade; um alarme nelas conta como detecção.",
    "alarmes_estimados": "Estimativa dos alarmes falsos por hora pelo encadeamento das janelas acima do limiar nos 52 s saudáveis: uma cadeia de Markov de dois estados (Brook e Evans, 1972). As sequências de 1 e de 2 janelas acima do limiar, que aparecem nos dados, dão a chance de 3 seguidas, que disparam o alarme. O intervalo de 95% sorteia os 16 trechos saudáveis.",
    "faixa_limiar": "Quanto a fração esperada de janelas acima do limiar pode variar só por o limiar vir de poucas janelas de calibração: com o limiar na posição r de n, ela segue uma distribuição Beta(n + 1 − r, r) (Vovk, 2012).",
    "npr": "Número de prioridade de risco: S × O × D. Quanto maior, mais prioritário. As notas vêm de Cristaldi et al. (2017).",
    "base_tempo": "Horas de operação: só enquanto o inversor funciona, 4.015 h por ano (a premissa de Baschel et al., 2018). Horas de calendário: o ano inteiro, 8.760 h. As fontes não dizem em qual base a taxa foi medida; por isso as duas aparecem. A mesma taxa por hora dá riscos anuais diferentes.",
    "disponibilidade": "Fração do tempo em que o componente está funcionando: MTBF / (MTBF + parada por falha), com o MTBF em horas de calendário.",
    "cenario_reparo": "Os dois cenários de reparo usam o tempo do inversor inteiro para os 4 grupos: nenhuma fonte traz o tempo de reparo de cada componente.",
    "horas_paradas": "Horas por ano com o componente parado: falhas por ano × parada por falha.",
}
NOTE_NAMES = {
    "sensibilidade": "Sensibilidade", "especificidade": "Especificidade", "precisao": "Precisão", "f1": "F1",
    "acuracia_balanceada": "Acurácia balanceada", "auc_roc": "AUC-ROC", "auc_pr": "AUC-PR", "mcc": "MCC",
    "detectados": "Ensaios detectados", "atraso": "Atraso", "alarme": "Alarme", "limite_superior": "Limite superior de 95%",
    "ic95": "Intervalo de 95%", "mudanca": "Mudança observada", "trecho_incerto": "Trecho entre o meio e a mudança",
    "alarmes_estimados": "Alarmes falsos estimados", "faixa_limiar": "Faixa esperada pelo limiar", "npr": "NPR",
    "base_tempo": "Base de tempo", "disponibilidade": "Disponibilidade", "cenario_reparo": "Cenários de reparo",
    "horas_paradas": "Horas paradas por ano",
}
# Nomes das seções da aba Ciência, como na tela (SCIENCE_TABS em ciencia.js); um teste compara.
SECTIONS = {"resumo": "Resumo", "metricas": "Métricas por falha", "inicio": "Início das falhas", "fmeca": "FMECA",
            "confiabilidade": "Confiabilidade"}
# O treino repetido, em palavras, sem o termo interno da nota da tela.
TRAININGS = ("O treino foi repetido 5 vezes, cada uma partindo de um ponto aleatório diferente. Os números são os do "
             "treino de referência, e a faixa entre parênteses vai do menor ao maior valor das 5 repetições.")
_cache: dict = {}
_lock = threading.Lock()


# Formatação igual à da tela (num, pct, seconds e dec de graficos.js e ciencia.js).
def _group(text: str) -> str:
    whole, _, fraction = text.partition(".")
    sign, whole = ("-", whole[1:]) if whole.startswith("-") else ("", whole)
    parts = []
    while len(whole) > 3:
        parts.insert(0, whole[-3:])
        whole = whole[:-3]
    parts.insert(0, whole)
    return sign + ".".join(parts) + ("," + fraction if fraction else "")


def num(value, digits: int = 3) -> str:
    """Algarismos significativos, vírgula decimal e ponto de milhar; muito pequeno ou muito grande, em notação e."""
    if value is None:
        return "—"
    value = float(value)
    if value != 0 and (abs(value) < 1e-3 or abs(value) >= 1e6):
        return f"{value:.2e}".replace("e-0", "e-").replace("e+0", "e+").replace(".", ",")
    rounded = Decimal(f"{value:.{digits}g}")
    text = format(rounded, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return _group(text)


def pct(value, digits: int = 3) -> str:
    return "—" if value is None else f"{num(100 * value, digits)}%"


def seconds(ms) -> str:
    return "—" if ms is None else f"{num(ms / 1000, 3)} s"


def dec(value, digits: int = 3) -> str:
    return "—" if value is None else f"{value:.{digits}f}".replace(".", ",")


def _table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def _day(iso: str | None) -> str:
    return "/".join(reversed(str(iso)[:10].split("-"))) if iso else ""


def _block(mark: str, title: str, source: str, date: str | None, status: str, section: str, text: str,
           notes: tuple[str, ...] = ()) -> dict:
    """Um bloco citável; `notes` são as chaves das notas dos indicadores que ele usa."""
    return {"citation_id": mark, "titulo": title, "fonte": source, "data": str(date or "")[:10], "estatuto": status,
            "secao": section, "texto": text,
            "notas": [{"nome": NOTE_NAMES[key], "texto": NOTES[key]} for key in notes]}


def _spread(values, formatter) -> str:
    return f"{formatter(values[0])} a {formatter(values[1])}" if values else "—"


def _gpvs_blocks(results_dir: Path) -> tuple[list[dict], list[str]]:
    """R1 a R6, das funções da aba; a reanálise (R5 e R6) só entra se existir."""
    from aliado.science.detection import summary  # numpy só aqui

    overview = summary.overview(results_dir)
    faults = summary.per_fault(results_dir)
    day = overview["data"]
    source = (f"Avaliação oficial de {_day(day)}: os 14 ensaios com falha e o teste saudável do GPVS, em janelas de "
              "20 ms, com o treino de referência")
    models = overview["modelos"]
    rows = [["Ensaios detectados, de 14",
             *[f"{models[k]['detectados']} (faixa: {_spread(models[k]['faixa'].get('detectados'), str)})"
               for k, _ in MODELS]],
            ["Atraso mediano desde o início nominal",
             *[f"{seconds(models[k]['atraso_mediano_ms'])} (faixa: "
               f"{_spread(models[k]['faixa'].get('atraso_mediano_ms'), seconds)})" for k, _ in MODELS]]]
    rows += [[label, *[f"{dec(models[k]['metricas'][key])} (faixa: "
                       f"{_spread(models[k]['faixa'].get(key), dec)})" for k, _ in MODELS]] for key, label in METRICS]
    blocks = [_block("R1", "Avaliação oficial: detecção, atraso e métricas por janela", source, day, OFFICIAL, "resumo",
                     _table(["Indicador", *[name for _, name in MODELS]], rows) + "\n\nAs métricas são a média dos 14 ensaios. "
                     + TRAININGS, ("detectados", "atraso", *[key for key, _ in METRICS]))]

    rows = []
    for key, name in MODELS:
        healthy = models[key]["saudavel"]
        test, pre = healthy["trechos"]["teste_saudavel"], healthy["trechos"]["pre_falha"]
        rows.append([name, healthy["alarmes"], f"{num(healthy['duracao_s'])} s", num(healthy["alarmes_por_hora"]),
                     num(healthy["limite_superior_por_hora"]),
                     f"{healthy['janelas_acima']} de {num(healthy['janelas'], 4)} ({pct(healthy['janelas_acima'] / healthy['janelas'])})",
                     f"{pct(test['fracao'])} (IC 95%: {_spread(test['ic95'], pct)})",
                     f"{pct(pre['fracao'])} (IC 95%: {_spread(pre['ic95'], pct)})"])
    blocks.append(_block(
        "R2", "Avaliação oficial: alarmes falsos na operação saudável", source, day, OFFICIAL, "resumo",
        _table(["Modelo", "Alarmes falsos", "Tempo saudável", "Alarmes por hora", "Limite superior de 95% por hora",
                "Janelas acima do limiar", "No teste saudável", "Antes da falha"], rows)
        + "\n\nO tempo saudável soma o teste saudável e o trecho antes da falha dos 14 ensaios.",
        ("alarme", "limite_superior")))

    rows = [[row["objetivo"], row["metrica"], num(row["diferenca"]), _spread(row["ic95"], num), row["leitura"]]
            for row in overview["comparacao"]]
    blocks.append(_block(
        "R3", "Avaliação oficial: comparação Denso − AE-LSTM por objetivo", source, day, OFFICIAL, "resumo",
        _table(["Objetivo", "Métrica", "Diferença (Denso − AE-LSTM)", "Intervalo de 95%", "Leitura"], rows)
        + "\n\nA diferença é pareada por ensaio. Não há vencedor geral.", ("ic95",)))

    rows = []
    for fault in faults["falhas"]:
        row = [f"{fault['nome']} ({fault['id']})"]
        for key, _ in MODELS:
            item = faults["modelos"][key]["por_falha"][fault["id"]]
            modes = [mode for mode in "LM" if faults["modelos"][key]["por_ensaio"][f"{fault['id']}{mode}"]["detectado"]]
            where = f" ({' e '.join(modes)})" if modes else ""
            row += [f"{item['detectados']} de 2{where}", dec(item["sensibilidade"]), dec(item["especificidade"]),
                    dec(item["mcc"]), seconds(item["atraso_ms"])]
        rows.append(row)
    headers = ["Tipo de falha"] + [f"{name}: {column}" for _, name in MODELS
                                   for column in ("detectou", "sensibilidade", "especificidade", "MCC", "atraso")]
    blocks.append(_block(
        "R4", "Avaliação oficial: resultados por tipo de falha", source, day, OFFICIAL, "metricas",
        _table(headers, rows) + "\n\nCada falha tem dois ensaios: L, com potência limitada, e M, com potência máxima. "
        "Sensibilidade, especificidade e MCC somam as janelas dos dois; o atraso é a média dos ensaios detectados.",
        ("detectados", "sensibilidade", "especificidade", "mcc", "atraso")))

    try:
        blocks += _reanalysis_blocks(summary.onsets(results_dir), models, day)
    except Exception:  # a reanálise é secundária: ausente ou incompleta, os blocos oficiais ficam
        return blocks, ["a reanálise com o início observado das falhas"]
    return blocks, []


def _reanalysis_blocks(onsets: dict, models: dict, day: str) -> list[dict]:
    """R5 e R6, da reanálise com o início observado; o R6 mostra a faixa do limiar só se houver o treino."""
    later = onsets["data"]
    source = (f"Reanálise de {_day(later)} dos mesmos escores da avaliação de {_day(day)}, com o início observado "
              "das falhas. Secundária: a avaliação oficial continua sendo a de " + _day(day))
    trial_rows = [[item["id"], item["nome"], f"{dec(item['nominal_s'], 2)} s",
                   "—" if item["observado_s"] is None else f"{dec(item['observado_s'], 2)} s", CLASSES[item["classe"]]]
                  for item in onsets["ensaios"]]
    columns = (("meio", "14 ensaios, início no meio"), ("mudanca", "14 ensaios, mudança observada"),
               ("clara_meio", "8 de mudança clara, início no meio"), ("clara_mudanca", "8 de mudança clara, mudança observada"))
    indicator_rows = []
    for key, name in MODELS:
        data = onsets["modelos"][key]
        indicator_rows.append([f"{name}: ensaios detectados",
                               *[f"{data[c]['detectados']} de {data[c]['ensaios']}" for c, _ in columns]])
        indicator_rows.append([f"{name}: atraso mediano", *[seconds(data[c]["atraso_mediano_ms"]) for c, _ in columns]])
        indicator_rows += [[f"{name}: {label}", *[dec(data[c][metric]) for c, _ in columns]]
                           for metric, label in (("sensibilidade", "sensibilidade"), ("especificidade", "especificidade"),
                                                 ("f1", "F1"), ("auc_roc", "AUC-ROC"))]
    blocks = [_block(
        "R5", "Reanálise: quando cada falha aparece nos sinais e os indicadores com esse início", source, later,
        SECONDARY, "inicio",
        _table(["Ensaio", "Falha", "Meio do registro", "Mudança observada", "Classe da mudança"], trial_rows)
        + "\n\n" + _table(["Indicador", *[label for _, label in columns]], indicator_rows)
        + "\n\nO ensaio terminado em L tem a potência limitada, e o terminado em M, a potência máxima. Só os ensaios de "
        "mudança clara passam a usar a mudança; os demais ficam no meio do registro. Nas colunas da mudança, o atraso é "
        "contado da mudança observada.",
        ("mudanca", "trecho_incerto", "sensibilidade", "especificidade", "f1", "auc_roc"))]
    rows, with_limit = [], False
    for key, name in MODELS:
        estimate, limit = models[key].get("alarmes_estimados"), models[key].get("limiar_faixa")
        if not estimate:
            continue
        with_limit = with_limit or bool(limit)
        rows.append([name, num(estimate["alarmes_por_hora"]), _spread(estimate["ic95"], num),
                     f"{num(estimate['previsto']['sequencias_de_2'])} previstas e {estimate['observado']['sequencias_de_2']} vistas",
                     f"{num(estimate['previsto']['alarmes'])} previstos e {estimate['observado']['alarmes']} vistos",
                     f"{limit['posicao']}º de {limit['n']}" if limit else "—",
                     _spread(limit["ic95"], pct) if limit else "—"])
    if not rows:
        raise KeyError("alarmes_estimados")
    blocks.append(_block(
        "R6", "Reanálise: alarmes falsos estimados por hora e faixa esperada pelo limiar", source, later, SECONDARY,
        "resumo",
        _table(["Modelo", "Alarmes falsos estimados por hora", "Intervalo de 95%", "Sequências de 2 janelas",
                "Alarmes", "Posição do limiar na calibração", "Faixa esperada de janelas acima do limiar"], rows),
        ("alarmes_estimados", *(("faixa_limiar",) if with_limit else ()))))
    return blocks


def _rate(per_hour: float | None) -> str:
    """Taxa por hora na notação da pesquisa: 63,7e-6/h."""
    return "—" if per_hour is None else f"{num(per_hour * 1e6)}e-6/h"


def _fmeca_block(reference_dir: Path) -> dict:
    from aliado.science.fmeca import evaluate_fmeca, load_table

    data = evaluate_fmeca(*load_table(reference_dir / "fmeca.json"))
    names = {item["id"]: item["nome"] for item in data["itens"]}
    rows = [[item["nome"], item["S"], item["O"], item["D"], item["npr"], f"{item['posicoes']['npr']}º",
             _rate(item["taxa_por_hora"]), f"{item['posicoes']['taxa']}º" if item["posicoes"]["taxa"] else "—"]
            for item in data["itens"]]
    pairs = "; ".join(f"{names[p['maior_O']]} tem O maior que {names[p['menor_O']]}, mas taxa menor"
                      for p in data["pares_discordantes_O_taxa"])
    return _block(
        "R7", "FMECA dos quatro grupos do inversor", f"FMECA decidida em {_day(data['decidida_em'])}. Notas: {data['fonte_notas']}",
        data["decidida_em"], OFFICIAL, "fmeca",
        _table(["Grupo", "S (severidade)", "O (ocorrência)", "D (detecção)", "NPR", "Posição pelo NPR", "Taxa de falha",
                "Posição pela taxa"], rows)
        + "\n\nAs duas ordens ficam separadas, sem nota agregada. " + (f"Discordâncias: {pairs}. " if pairs else "")
        + "As notas S, O e D refletem a percepção do levantamento de campo da fonte e não se ligam aos ensaios do GPVS.",
        ("npr",))


def _components_block(reference_dir: Path) -> dict:
    from aliado.science.components import component_view, load_repairs
    from aliado.science.fmeca import load_table

    repairs = load_repairs(reference_dir / "reparos.json")
    view = component_view(*load_table(reference_dir / "fmeca.json"), repairs, points=3)
    horizon = num(view["horizonte_anos"])
    rows = []
    for group in view["grupos"]:
        for basis, label in BASES:
            item = group["bases"][basis]
            cells = [group["nome"], label, _rate(item["taxa_por_hora"]), f"{num(item['mtbf_anos'])} anos",
                     pct(item["f_1_ano"], 4), pct(item["f_horizonte"], 4), num(item["falhas_no_horizonte"])]
            for repair in view["reparo"]:
                availability = item["disponibilidade"][repair["id"]]
                cells += [pct(availability["disponibilidade"], 5), f"{num(availability['horas_paradas_por_ano'])} h"]
            rows.append(cells)
    headers = ["Grupo", "Base de tempo", "Taxa de falha", "MTBF", "Chance de falhar em 1 ano",
               f"Chance de falhar em {horizon} anos", f"Falhas esperadas em {horizon} anos"]
    sources = []
    for repair, raw in zip(view["reparo"], repairs["cenarios"]):
        short = REPAIR_NAMES.get(repair["id"], repair["nome"])
        headers += [f"Disponibilidade · {short}", f"Horas paradas por ano · {short}"]
        hours = sorted(set(raw["reparo_horas"].values()))
        detect = f"{num(raw['deteccao_horas'])} h para notar a falha e " if raw["deteccao_horas"] else ""
        sources.append(f"{short}: {detect}{' ou '.join(num(h) for h in hours)} h de reparo por falha "
                       f"({repair['fontes'][0].split(':')[0]}).")
    return _block(
        "R8", "Confiabilidade e disponibilidade de cada grupo do inversor",
        "Taxas de falha dos cenários da pesquisa, com vida exponencial, e tempos de reparo decididos em "
        f"{_day(repairs['decidida_em'])}", repairs["decidida_em"], OFFICIAL, "confiabilidade",
        _table(headers, rows) + "\n\nTempos de reparo: " + " ".join(sources),
        ("base_tempo", "disponibilidade", "horas_paradas", "cenario_reparo"))


def build_digest(results_dir: str | Path, reference_dir: str | Path) -> dict:
    """Cabeçalho, blocos na ordem R1…R8 e o que ficou de fora, em palavras."""
    results_dir, reference_dir = Path(results_dir), Path(reference_dir)
    blocks, missing = [], []
    try:
        gpvs, partial = _gpvs_blocks(results_dir)
        blocks += gpvs
        missing += partial
    except ImportError:
        missing.append("os resultados do GPVS (falta o numpy nesta instalação)")
    except FileNotFoundError:
        missing.append("os resultados do GPVS (falta a avaliação oficial de 27/09)")
    except Exception:  # arquivo truncado ou em formato inesperado: o resto do resumo continua
        missing.append("os resultados do GPVS (os arquivos da avaliação estão incompletos)")
    for label, maker in (("a FMECA", _fmeca_block), ("a confiabilidade e a disponibilidade por grupo", _components_block)):
        try:
            blocks.append(maker(reference_dir))
        except Exception:
            missing.append(label)
    header = HEADER + (" Não entraram neste pedido: " + "; ".join(missing) + "." if missing else "")
    return {"cabecalho": header, "blocos": blocks, "faltando": missing}


def _signature(results_dir: Path, reference_dir: Path) -> tuple:
    """Caminho, data e tamanho de cada arquivo lido: o resumo só é refeito quando um deles muda."""
    files = [reference_dir / "fmeca.json", reference_dir / "reparos.json", *sorted((reference_dir / "cenarios").glob("*.json"))]
    for folder in sorted(results_dir.glob("gpvs-*")) if results_dir.is_dir() else []:
        files += [folder / name for name in ("relatorio.json", "configuracao.json", "metricas_por_ensaio.csv")]
    marks = []
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        marks.append((str(path), stat.st_mtime_ns, stat.st_size))
    return tuple(marks)


def cached(results_dir: str | Path, reference_dir: str | Path) -> dict:
    """O resumo em memória, refeito só quando algum arquivo de origem muda."""
    results_dir, reference_dir = Path(results_dir), Path(reference_dir)
    signature = _signature(results_dir, reference_dir)
    key = (str(results_dir), str(reference_dir))
    with _lock:
        if _cache.get(key, (None, None))[0] != signature:
            _cache[key] = (signature, build_digest(results_dir, reference_dir))
        return _cache[key][1]


def shared_notes(blocks) -> dict[str, str]:
    """As notas dos indicadores dos blocos, sem repetição, na ordem em que aparecem."""
    notes = {}
    for block in blocks:
        for note in block.get("notas") or ():
            notes.setdefault(note["nome"], note["texto"])
    return notes


def prompt_text(digest: dict) -> str:
    """O que vai ao modelo: o cabeçalho, as notas dos indicadores uma vez só e os blocos, cada um com a
    seção da aba Ciência onde o pesquisador o vê."""
    blocks = [{key: block[key] for key in ("citation_id", "titulo", "fonte", "data", "estatuto")}
              | {"onde_ver": f"aba Ciência, seção {SECTIONS.get(block['secao'], block['secao'])}", "texto": block["texto"]}
              for block in digest["blocos"]]
    return json.dumps({"cabecalho": digest["cabecalho"], "notas": shared_notes(digest["blocos"]), "blocos": blocks},
                      ensure_ascii=False)


def block_text(block: dict) -> str:
    """Tudo o que o bloco imprime, para a conferência dos números."""
    return "\n".join(str(block[key]) for key in ("titulo", "fonte", "data", "texto"))


def notes_text(blocks) -> str:
    """O texto das notas enviadas: os números delas valem em qualquer linha que cite um bloco."""
    return "\n".join(shared_notes(blocks).values())
