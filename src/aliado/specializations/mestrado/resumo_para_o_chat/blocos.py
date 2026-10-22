"""Resumo dos resultados do mestrado para o chat (lotes 26, 34, 36 e 55): blocos [R1]…[R10] gerados por código.

Os números saem das mesmas funções da aba Ciência (`resultados/paineis`, `fmeca` e `componentes`), nunca dos
relatórios em markdown, e vão no formato da tela. São os da rodada que a aba mostra. Cada bloco diz
a fonte, a data e o estatuto: a avaliação de 27/09/2026 é a oficial, uma rodada feita depois é
exploração, e o início observado das falhas é secundário. O que não puder ser montado (sem numpy,
sem a avaliação ou sem o início das falhas) fica de fora, com o motivo em palavras. O módulo abre
sem numpy: `resultados/paineis` só é importado dentro da função que o usa.

A evidência espectral (R9 e R10, lote 55) só entra com o arquivo dela, e os dois blocos vão "sob pedido": o
núcleo só os manda ao modelo quando a pergunta cita um dos termos deles (Fourier, harmônicos, nível DC, THD).
"""

from __future__ import annotations

import threading
from pathlib import Path

from aliado.science.resumo_citavel.formato import dec, num, pct, seconds
from aliado.specializations.mestrado.evidencia_espectral import artefatos as evidencia
from aliado.specializations.mestrado.glossario.notas import NOTES
from aliado.specializations.mestrado.resultados import rodada_atual
from aliado.specializations.mestrado.rodada import experimento
from aliado.specializations.mestrado.rodada.declaracao import EXPLORATION_DIR

MAX_CHARS = 16_000
HEADER = ("A avaliação oficial é a de 27/09/2026 (treino de referência). A reanálise de 30/09/2026, com o "
          "início observado das falhas, é secundária: complementa, não substitui.")
OFFICIAL, SECONDARY, EXPLORATION = "oficial", "secundaria", "exploracao"
MODELS = (("denso", "Denso"), ("lstm", "AE-LSTM"))
METRICS = (("sensibilidade", "Sensibilidade"), ("especificidade", "Especificidade"), ("precisao", "Precisão"),
           ("f1", "F1"), ("acuracia_balanceada", "Acurácia balanceada"), ("mcc", "MCC"), ("auc_roc", "AUC-ROC"),
           ("auc_pr", "AUC-PR"))
BASES = (("operation", "operação, 4.015 h/ano"), ("calendar", "calendário, 8.760 h/ano"))
CLASSES = {"clara": "clara", "fraca": "fraca (não usada)", "nenhuma": "nenhuma"}
REPAIR_NAMES = {"ieee493": "IEEE 493", "baschel": "Baschel"}
NOTE_NAMES = {
    "sensibilidade": "Sensibilidade", "especificidade": "Especificidade", "precisao": "Precisão", "f1": "F1",
    "acuracia_balanceada": "Acurácia balanceada", "auc_roc": "AUC-ROC", "auc_pr": "AUC-PR", "mcc": "MCC",
    "detectados": "Ensaios detectados", "atraso": "Atraso", "alarme": "Alarme", "limite_superior": "Limite superior de 95%",
    "ic95": "Intervalo de 95%", "mudanca": "Mudança observada", "trecho_incerto": "Trecho entre o meio e a mudança",
    "alarmes_estimados": "Alarmes falsos estimados", "faixa_limiar": "Faixa esperada pelo limiar", "npr": "NPR",
    "base_tempo": "Base de tempo", "disponibilidade": "Disponibilidade", "cenario_reparo": "Cenários de reparo",
    "horas_paradas": "Horas paradas por ano", "janela_alarme": "Janela do alarme",
    "fase_maior_erro": "Fase com maior erro", "maior_erro_geral": "Maior erro geral", "nivel_dc": "Nível DC / fundamental",
    "fundamental_relativa": "Fundamental / comissionamento", "thd": "THD", "harmonicas": "Harmônicas / fundamental",
    "entre_parenteses": "Valores entre parênteses", "passo_irregular": "Passo irregular", "mais_muda": "Mais muda",
    "janelas_antes_mudanca": "Janelas antes da mudança observada",
}
# Os termos que levam R9 e R10 ao modelo, sem acento e em minúsculas (o núcleo compara assim).
SPECTRAL_TERMS = ("fourier", "harmonic", "espectr", "nivel dc", "componente continua", "thd", "distorcao harmonica")
# O treino repetido, em palavras, sem o termo interno da nota da tela.
TRAININGS = ("O treino foi repetido {n} vezes, cada uma partindo de um ponto aleatório diferente. Os números são os do "
             "treino de referência, e a faixa entre parênteses vai do menor ao maior valor das {n} repetições.")
_cache: dict = {}
_lock = threading.Lock()


def _header(run: dict | None) -> str:
    """O cabeçalho dos blocos: o da avaliação oficial ou o de uma rodada feita depois dela."""
    if not run or run.get("oficial"):
        return HEADER
    return (f"Os números vêm da rodada que a aba Ciência mostra: {run['rotulo']}, com o treino de referência. Ela foi "
            "feita depois da avaliação oficial de 27/09/2026, que continua sendo a oficial. O início observado das "
            "falhas é da mesma rodada e é secundário: complementa, não substitui.")


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


def _gpvs_blocks(results_dir: Path, explorer_dir: Path | None = None) -> tuple[list[dict], list[str], dict]:
    """R1 a R6, das funções da aba; o início observado (R5 e R6) só entra se existir, e a evidência espectral (R9 e
    R10), só com o arquivo dela, da própria rodada ou do explorador."""
    from aliado.specializations.mestrado.resultados import paineis  # numpy só aqui

    overview = paineis.overview(results_dir)
    faults = paineis.per_fault(results_dir)
    day, run = overview["data"], overview["rodada"]
    status = OFFICIAL if run["oficial"] else EXPLORATION
    title = "Avaliação oficial" if run["oficial"] else "Rodada atual"
    source = (f"{run['rotulo']}: os 14 ensaios com falha e o teste saudável do GPVS, em janelas de 20 ms, com o "
              "treino de referência")
    trainings = TRAININGS.format(n=overview["treinamentos"])
    models = overview["modelos"]
    rows = [["Ensaios detectados, de 14",
             *[f"{models[k]['detectados']} (faixa: {_spread(models[k]['faixa'].get('detectados'), str)})"
               for k, _ in MODELS]],
            ["Atraso mediano desde o início nominal",
             *[f"{seconds(models[k]['atraso_mediano_ms'])} (faixa: "
               f"{_spread(models[k]['faixa'].get('atraso_mediano_ms'), seconds)})" for k, _ in MODELS]]]
    rows += [[label, *[f"{dec(models[k]['metricas'][key])} (faixa: "
                       f"{_spread(models[k]['faixa'].get(key), dec)})" for k, _ in MODELS]] for key, label in METRICS]
    blocks = [_block("R1", f"{title}: detecção, atraso e métricas por janela", source, day, status, "resumo",
                     _table(["Indicador", *[name for _, name in MODELS]], rows) + "\n\nAs métricas são a média dos 14 ensaios. "
                     + trainings, ("detectados", "atraso", *[key for key, _ in METRICS]))]

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
        "R2", f"{title}: alarmes falsos na operação saudável", source, day, status, "resumo",
        _table(["Modelo", "Alarmes falsos", "Tempo saudável", "Alarmes por hora", "Limite superior de 95% por hora",
                "Janelas acima do limiar", "No teste saudável", "Antes da falha"], rows)
        + "\n\nO tempo saudável soma o teste saudável e o trecho antes da falha dos 14 ensaios.",
        ("alarme", "limite_superior")))

    rows = [[row["objetivo"], row["metrica"], num(row["diferenca"]), _spread(row["ic95"], num), row["leitura"]]
            for row in overview["comparacao"]]
    blocks.append(_block(
        "R3", f"{title}: comparação Denso − AE-LSTM por objetivo", source, day, status, "resumo",
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
        "R4", f"{title}: resultados por tipo de falha", source, day, status, "metricas",
        _table(headers, rows) + "\n\nCada falha tem dois ensaios: L, com potência limitada, e M, com potência máxima. "
        "Sensibilidade, especificidade e MCC somam as janelas dos dois; o atraso é a média dos ensaios detectados.",
        ("detectados", "sensibilidade", "especificidade", "mcc", "atraso")))

    missing = []
    try:
        blocks += _reanalysis_blocks(paineis.onsets(results_dir), models, day, run)
    except Exception:  # o início observado é secundário: ausente ou incompleto, os blocos da avaliação ficam
        missing.append("a reanálise com o início observado das falhas")
    try:
        found = evidencia.find(rodada_atual.current(results_dir), explorer_dir)
        if found:
            names = {fault["id"]: fault["nome"] for fault in faults["falhas"]}
            blocks += _spectral_blocks(run, evidencia.read(found), names)
    except Exception:  # a evidência é exploração: com o arquivo quebrado, os outros blocos ficam
        missing.append("a evidência espectral (o arquivo dela está incompleto)")
    return blocks, missing, run


def _spectral_blocks(run: dict, evidence: dict, fault_names: dict[str, str]) -> list[dict]:
    """R9 e R10: os harmônicos na janela do primeiro alarme e o que mais muda em cada ensaio, sempre exploração."""
    from aliado.specializations.mestrado.evidencia_espectral import relatorio

    origin = ("calculada na própria rodada" if evidence["origem"] == "rodada" else
              "exploração pós-teste, montada pelo Preparar da aba Ciência, sem mudar os números oficiais")
    source = f"{run['rotulo']}: harmônicos das 6 fases no primeiro alarme, com o treino de referência; {origin}"
    day = evidence["executado_em"]
    alarm = _block("R9", "Harmônicos na janela do primeiro alarme", source, day, EXPLORATION, "explorar",
                   _table(relatorio.ALARM_HEADERS, relatorio.alarm_rows(evidence)) + "\n\n" + relatorio.ALARM_TEXT,
                   ("janela_alarme", "fase_maior_erro", "maior_erro_geral", "nivel_dc", "fundamental_relativa", "thd",
                    "harmonicas", "entre_parenteses", "passo_irregular"))
    change = _block("R10", "Os dois indicadores espectrais que mais mudam em cada ensaio", source, day, EXPLORATION,
                    "explorar", _table(relatorio.CHANGE_HEADERS, relatorio.change_rows(evidence, fault_names))
                    + "\n\n" + relatorio.CHANGE_TEXT,
                    ("mais_muda", "janelas_antes_mudanca", "nivel_dc", "thd", "harmonicas"))
    return [block | {"sob_pedido": SPECTRAL_TERMS} for block in (alarm, change)]


def _reanalysis_blocks(onsets: dict, models: dict, day: str, run: dict) -> list[dict]:
    """R5 e R6, do início observado; o R6 mostra a faixa do limiar só se houver o treino."""
    later = onsets["data"]
    source = (f"Reanálise de {_day(later)} dos mesmos escores da avaliação de {_day(day)}, com o início observado "
              "das falhas. Secundária: a avaliação oficial continua sendo a de " + _day(day) if run["oficial"] else
              f"Início observado das falhas da mesma rodada ({run['rotulo']}), sobre os escores da avaliação dela. "
              "Secundário: complementa a avaliação da rodada, sem substituí-la")
    prefix = "Reanálise" if run["oficial"] else "Início das falhas"
    clear = len(onsets["clara"])
    trial_rows = [[item["id"], item["nome"], f"{dec(item['nominal_s'], 2)} s",
                   "—" if item["observado_s"] is None else f"{dec(item['observado_s'], 2)} s", CLASSES[item["classe"]]]
                  for item in onsets["ensaios"]]
    columns = (("meio", "14 ensaios, início no meio"), ("mudanca", "14 ensaios, mudança observada"),
               ("clara_meio", f"{clear} de mudança clara, início no meio"),
               ("clara_mudanca", f"{clear} de mudança clara, mudança observada"))
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
        "R5", f"{prefix}: quando cada falha aparece nos sinais e os indicadores com esse início", source, later,
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
        "R6", f"{prefix}: alarmes falsos estimados por hora e faixa esperada pelo limiar", source, later, SECONDARY,
        "resumo",
        _table(["Modelo", "Alarmes falsos estimados por hora", "Intervalo de 95%", "Sequências de 2 janelas",
                "Alarmes", "Posição do limiar na calibração", "Faixa esperada de janelas acima do limiar"], rows),
        ("alarmes_estimados", *(("faixa_limiar",) if with_limit else ()))))
    return blocks


def _rate(per_hour: float | None) -> str:
    """Taxa por hora na notação da pesquisa: 63,7e-6/h."""
    return "—" if per_hour is None else f"{num(per_hour * 1e6)}e-6/h"


def _fmeca_block(reference_dir: Path) -> dict:
    from aliado.science.fmeca.calculo import evaluate_fmeca
    from aliado.science.fmeca.tabela import load_table

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
    from aliado.science.componentes.disponibilidade import component_view
    from aliado.science.componentes.reparos import load_repairs
    from aliado.science.fmeca.tabela import load_table

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


def build_digest(results_dir: str | Path, reference_dir: str | Path, data_dir: str | Path | None = None) -> dict:
    """Cabeçalho, blocos na ordem R1…R10 e o que ficou de fora, em palavras. `data_dir`, a pasta de dados do servidor,
    traz a evidência espectral que o explorador montou para uma rodada anterior."""
    results_dir, reference_dir = Path(results_dir), Path(reference_dir)
    explorer_dir = Path(data_dir) / EXPLORATION_DIR if data_dir else None
    blocks, missing, run = [], [], None
    try:
        gpvs, partial, run = _gpvs_blocks(results_dir, explorer_dir)
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
    blocks.sort(key=lambda block: int(block["citation_id"][1:]))  # R9 e R10 vêm depois de R7 e R8
    header = _header(run) + (" Não entraram neste pedido: " + "; ".join(missing) + "." if missing else "")
    return {"cabecalho": header, "blocos": blocks, "faltando": missing}


def _signature(results_dir: Path, reference_dir: Path, explorer_dir: Path | None) -> tuple:
    """Caminho, data e tamanho de cada arquivo lido: o resumo só é refeito quando um deles muda."""
    files = [reference_dir / "fmeca.json", reference_dir / "reparos.json", *sorted((reference_dir / "cenarios").glob("*.json"))]
    for folder in sorted(results_dir.glob("gpvs-*")) if results_dir.is_dir() else []:
        files += [folder / name for name in ("relatorio.json", "configuracao.json", "metricas_por_ensaio.csv")]
    files += sorted((results_dir / experimento.KEY).glob("rodada-*/resultado.json"))  # uma rodada nova muda tudo
    files += sorted((results_dir / experimento.KEY).glob(f"rodada-*/*/{evidencia.FILE}"))
    files += sorted(explorer_dir.glob("evidencia-espectral-*.json")) if explorer_dir else []
    marks = []
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        marks.append((str(path), stat.st_mtime_ns, stat.st_size))
    return tuple(marks)


def cached(results_dir: str | Path, reference_dir: str | Path, data_dir: str | Path | None = None) -> dict:
    """O resumo em memória, refeito só quando algum arquivo de origem muda."""
    results_dir, reference_dir = Path(results_dir), Path(reference_dir)
    explorer_dir = Path(data_dir) / EXPLORATION_DIR if data_dir else None
    signature = _signature(results_dir, reference_dir, explorer_dir)
    key = (str(results_dir), str(reference_dir), str(explorer_dir))
    with _lock:
        if _cache.get(key, (None, None))[0] != signature:
            _cache[key] = (signature, build_digest(results_dir, reference_dir, data_dir))
        return _cache[key][1]
