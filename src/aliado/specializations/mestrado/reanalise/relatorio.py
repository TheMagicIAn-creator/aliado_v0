"""O texto da reanálise em Markdown e o aviso de que a avaliação de 27/09 continua sendo a oficial."""

from __future__ import annotations

from pathlib import Path

from aliado.science.deteccao.redes.autoencoders import MODEL_NAMES, MODELS
from aliado.specializations.mestrado.avaliacao.incerteza import PAIRED_NAMES
from aliado.specializations.mestrado.avaliacao.oficial import EVALUATION
from aliado.specializations.mestrado.base import ensaios

NOTICE = ("Reanálise dos mesmos escores da avaliação de 27/09, sem rodar os modelos de novo. A avaliação de "
          "27/09 continua sendo a oficial.")


def _notice(evaluation_dir: Path, executed: str | None) -> str:
    """Na avaliação oficial, o aviso de 30/09; numa rodada nova, que os escores são os dela."""
    if evaluation_dir.name == EVALUATION:
        return NOTICE
    day = "/".join(reversed(str(executed)[:10].split("-"))) if executed else "desta rodada"
    return f"Início observado das falhas sobre os escores da avaliação de {day}, sem rodar os modelos de novo."


def _day_month(iso: str | None) -> str:
    return "/".join(reversed(str(iso)[:10].split("-")[1:])) if iso else "—"


def _number(value, digits: int = 1) -> str:
    return "—" if value is None else f"{value:.{digits}f}".replace(".", ",")


def _markdown(report: dict, official: dict) -> str:
    trials = report["inicio"]["ensaios"]
    clear, evaluated = len(report["so_mudanca_clara"]["ensaios"]), _day_month(report["origem"]["avaliacao_executada_em"])
    lines = [
        "# Reanálise do GPVS com o início observado das falhas", "",
        f"{report['aviso']} Origem: `{report['origem']['avaliacao']}` (avaliação de {report['origem']['avaliacao_executada_em']}) "
        f"e o treino `{report['origem']['treino']}`.", "",
        "## Quando cada falha aparece nos sinais", "",
        "O início nominal é o meio do registro, porque os arquivos não marcam o disparo. A mudança observada é a "
        "primeira mudança na média das 24 variáveis depois do comissionamento, achada pelo PELT (Killick, Fearnhead "
        f"e Eckley, 2012) com penalidade c · 24 · ln n. O c = {report['inicio']['penalidade_c']:g} é o menor da grade "
        "sem mudança nenhuma nos dois ensaios saudáveis. Clara: a mesma mudança em todos os c maiores; fraca: some "
        "com um c maior. Os escores dos detectores não entram.", "",
        "| Ensaio | Falha | Meio (s) | Mudança (s) | Diferença (s) | Classe |", "|---|---|---:|---:|---:|---|",
    ]
    for name, trial in trials.items():
        observed = trial["observado_s"]
        lines.append(f"| {name} | {ensaios.FAULTS[int(name[1])][0]} | {_number(trial['nominal_s'], 2)} | "
                     f"{_number(observed, 2)} | "
                     f"{'—' if observed is None else _number(observed - trial['nominal_s'], 2)} | {trial['classe']} |")
    lines += ["", "Nos ensaios de mudança clara, o trecho entre os dois inícios fica fora das métricas por janela; "
              "a detecção começa no início nominal, e o atraso é medido da mudança. Os demais ficam no meio.", "",
              "## Indicadores com cada início (treino de referência)", "",
              f"| Modelo | Indicador | 14 ensaios, meio ({evaluated}) | 14 ensaios, mudança | {clear} de mudança clara, meio | "
              f"{clear} de mudança clara, mudança |", "|---|---|---:|---:|---:|---:|"]
    names = {"detectados": ("Ensaios detectados", 0), "atraso_mediano_ms": ("Atraso mediano (ms)", 1),
             "sensibilidade_media": ("Sensibilidade", 3), "especificidade_media": ("Especificidade", 3),
             **{f"{metric}_media": (label, 3) for metric, label in (
                 ("precisao", "Precisão"), ("f1", "F1"), ("mcc", "MCC"), ("auc_roc", "AUC-ROC"), ("auc_pr", "AUC-PR"))}}
    for kind in MODELS:
        before = official["modelos"][kind]["referencia"]["resumo"]
        after = report["modelos"][kind]["referencia"]["resumo"]
        clear = report["so_mudanca_clara"]["modelos"][kind]["resumo"]
        clear_before = report["so_mudanca_clara"]["meio"]["modelos"][kind]["resumo"]
        for key, (label, places) in names.items():
            lines.append(f"| {MODEL_NAMES[kind]} | {label} | {_number(before[key], places)} | "
                         f"{_number(after[key], places)} | {_number(clear_before[key], places)} | "
                         f"{_number(clear[key], places)} |")
    for kind in MODELS:
        lines += ["", f"## Por ensaio — {MODEL_NAMES[kind]}", "",
                  "| Ensaio | Detectado | Atraso desde o meio (ms) | Atraso desde a mudança (ms) | "
                  "Sensibilidade no meio | Sensibilidade com a mudança |", "|---|---|---:|---:|---:|---:|"]
        for name, result in report["modelos"][kind]["referencia"]["ensaios"].items():
            before = official["modelos"][kind]["referencia"]["ensaios"][name]
            lines.append(f"| {name} | {'sim' if result['detectado'] else 'não'} | "
                         f"{_number(result['atraso_desde_o_meio_ms'])} | {_number(result['atraso_ms'])} | "
                         f"{_number(before['sensibilidade'], 3)} | {_number(result['sensibilidade'], 3)} |")
    lines += ["", "## Comparação por objetivo (Denso − AE-LSTM, com a mudança observada)", "",
              f"| Objetivo | Métrica | 14 ensaios: diferença [IC 95%] | Leitura | {clear} de mudança clara: diferença [IC 95%] | Leitura |",
              "|---|---|---|---|---|---|"]
    for row, clear in zip(report["comparacao"], report["so_mudanca_clara"]["comparacao"]):
        def cell(item):
            if item["media"] is None:
                return "—"
            return f"{_number(item['media'], 3)} [{_number(item['ic95'][0], 3)}; {_number(item['ic95'][1], 3)}]"
        lines.append(f"| {row['objetivo']} | {PAIRED_NAMES[row['metrica']]} | {cell(row)} | {row['leitura']} | {cell(clear)} | "
                     f"{clear['leitura']} |")
    lines += ["", "## Alarmes falsos por hora, estimados", "",
              "Cadeia de Markov de dois estados (abaixo e acima do limiar), ajustada às janelas saudáveis: o teste "
              "saudável e o trecho antes da falha dos 14 ensaios. Abordagem de cadeia de Markov para o tempo até o "
              "alarme (Brook e Evans, 1972); intervalo de 95% sorteando os trechos.", "",
              "| Modelo | Janelas | Acima do limiar | Estimados por hora [IC 95%] | Sequências de 2: previstas / vistas | "
              "Alarmes: previstos / vistos |", "|---|---:|---:|---|---|---|"]
    for kind, item in report["alarmes_estimados"].items():
        lines.append(f"| {MODEL_NAMES[kind]} | {item['janelas']} | {item['janelas_acima']} | "
                     f"{_number(item['alarmes_por_hora'])} [{_number(item['ic95'][0])}; {_number(item['ic95'][1])}] | "
                     f"{_number(item['previsto']['sequencias_de_2'])} / {item['observado']['sequencias_de_2']} | "
                     f"{_number(item['previsto']['alarmes'], 2)} / {item['observado']['alarmes']} |")
    lines += ["", "## Quanto o limiar pode variar", "",
              "Com o limiar na posição r de n escores de calibração, a chance de uma janela saudável nova passar dele "
              "segue uma Beta(n + 1 − r, r) (Vovk, 2012).", "",
              "| Modelo | Posição | Faixa esperada por janela (95%) | Observado no teste saudável | Observado antes da falha |",
              "|---|---|---|---|---|"]
    for kind, item in report["limiar_incerteza"].items():
        seen = item["observado"]
        lines.append(f"| {MODEL_NAMES[kind]} | {item['posicao']} de {item['n']} | "
                     f"{_number(100 * item['ic95'][0], 2)}% a {_number(100 * item['ic95'][1], 2)}% | "
                     f"{_number(100 * seen['teste_saudavel']['fracao'], 2)}% | {_number(100 * seen['pre_falha']['fracao'], 2)}% |")
    lines += ["", "## Limiar em outros percentis (só relatado)", "",
              "| Percentil | Modelo | Posição | Alarmes no teste saudável | Alarmes antes da falha | Detectados | "
              "Atraso mediano (ms) | Sensibilidade |", "|---|---|---|---:|---:|---:|---:|---:|"]
    for percentile, row in report["sensibilidade"]["percentil"].items():
        for kind, item in row.items():
            lines.append(f"| p{percentile.replace('.', ',')} | {MODEL_NAMES[kind]} | {item['posicao']} de {item['n_calibracao']} | "
                         f"{item['alarmes_teste_saudavel']} | {item['alarmes_pre_falha']} | {item['detectados']} | "
                         f"{_number(item['atraso_mediano_ms'])} | {_number(item['sensibilidade_media'], 3)} |")
    lines += ["", "## Limites", "",
              "- A mudança observada é onde a falha aparece nas variáveis, não o instante do disparo, que os arquivos "
              "não registram. A resolução é de uma janela (20 ms).",
              "- A mudança e os detectores olham as mesmas 24 variáveis. Uma sensibilidade alta nos ensaios de mudança "
              "clara mostra que, quando a falha aparece nas variáveis, os modelos a veem logo; ela não mede a "
              "capacidade de ver falhas que não mudam as variáveis.",
              "- F4 não muda as variáveis, e F6 e F7 mudam pouco: para eles, nenhum início é confiável, e a falta de "
              "detecção é, em boa parte, dos dados e das variáveis.",
              "- A estimativa de alarmes por hora supõe que as janelas saudáveis se encadeiam como uma cadeia de Markov "
              "e que 52 s representam a operação normal."]
    return "\n".join(lines) + "\n"
