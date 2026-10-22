"""O texto do relatório da avaliação em Markdown."""

from __future__ import annotations

from aliado.science.deteccao.redes.autoencoders import MODEL_NAMES
from aliado.specializations.mestrado.avaliacao.configuracao import EvaluationConfig
from aliado.specializations.mestrado.avaliacao.decisao import SECONDARY, SECONDS_PER_HOUR
from aliado.specializations.mestrado.avaliacao.incerteza import PAIRED_NAMES
from aliado.specializations.mestrado.avaliacao.treino_congelado import TrainedDetectors
from aliado.specializations.mestrado.base import ensaios


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
    lines += ["", f"Alarmes nas {len(trained.config.seeds)} sementes (teste saudável; pré-falha): " + "; ".join(
        f"{item['nome']} {item['faixa_sementes']['alarmes_teste_saudavel'][0]}–{item['faixa_sementes']['alarmes_teste_saudavel'][1]} e "
        f"{item['faixa_sementes']['alarmes_pre_falha'][0]}–{item['faixa_sementes']['alarmes_pre_falha'][1]}"
        for item in summary["modelos"].values()) + "."]
    for item in summary["modelos"].values():
        lines += ["", f"## Detecção por ensaio — {item['nome']} (semente {reference}, limiar {item['limiar']:.4f})", "",
                  "| Ensaio | Falha | Física | Detectada | Atraso (ms) | Sensibilidade [IC 95%] | "
                  "Especificidade [IC 95%] | Alarmes no pré-falha |",
                  "|---|---|---|---|---:|---|---|---:|"]
        for name, result in item["referencia"]["ensaios"].items():
            description, physical = ensaios.FAULTS[int(name[1])]
            lines.append(
                f"| {name} | {description} | {'sim' if physical else 'não'} | {'sim' if result['detectado'] else '**não**'} | "
                f"{_number(result['atraso_ms'])} | {result['sensibilidade']:.3f} {_interval(result['sensibilidade_ic95'], 3)} | "
                f"{result['especificidade']:.3f} {_interval(result['especificidade_ic95'], 3)} | {result['alarmes_pre_falha']} |")
    lines += ["", f"## Resumo por modelo (semente {reference}; entre parênteses, a faixa nas "
                  f"{len(trained.config.seeds)} sementes)", "",
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
