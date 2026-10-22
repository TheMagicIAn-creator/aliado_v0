"""O texto do relatório do treino em Markdown."""

from __future__ import annotations

from aliado.science.deteccao.particao.blocos import ROLES
from aliado.specializations.mestrado.treino.configuracao import ExperimentConfig

ROLE_NAMES = {"train": "Treino", "validation": "Validação", "calibration": "Calibração", "test": "Teste"}


def _markdown(summary: dict, config: ExperimentConfig) -> str:
    reference = str(config.reference_seed)
    protocol, calibration = summary["protocolo"], summary["calibracao"]
    check = protocol["verificacao_m14"]
    lines = [
        "# Treino dos autoencoders — GPVS, protocolo M14", "",
        f"Configuração congelada `{summary['configuracao_sha256'][:12]}`: separação de "
        f"{protocol['separacao_janelas']} janelas; sementes {', '.join(map(str, config.seeds))} "
        f"(referência {reference}); escore top-{config.top_k}; limiar p{config.percentile:g} na calibração.", "",
        "## Divisão saudável", "",
        "| Papel | " + " | ".join(ROLE_NAMES[role] for role in ROLES) + " |", "|---|" + "---:|" * len(ROLES),
        "| Janelas | " + " | ".join(str(protocol["papeis"][role]) for role in ROLES) + " |", "",
        f"Verificação do M14: distância entre blocos {check['distancia_entre_blocos']}, lag necessário "
        f"{check['lag_necessario']} — " + ("suficiente." if check["suficiente"] else "**insuficiente**."),
        f"A calibração tem {calibration['janelas']} janelas: {calibration['duracao_s']:.2f} s de operação "
        f"({calibration['janelas_por_segundo']:g} janelas por segundo).", "",
        f"## Modelos na semente {reference}", "",
        "| Modelo | Parâmetros | Melhor época | Épocas | Perda de validação | Limiar | Posição | "
        "Falso alarme esperado |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in summary["modelos"].values():
        run, limit = item["sementes"][reference], item["sementes"][reference]["limiar"]
        lines.append(
            f"| {item['nome']} | {item['parametros']} | {run['melhor_epoca']} | {run['epocas_executadas']} | "
            f"{run['perda_validacao_minima']:.4f} | {limit['limiar']:.4f} | {limit['posicao']}/{limit['n_calibracao']} | "
            f"{100 * limit['falso_alarme_esperado_por_janela']:.2f}% por janela "
            f"(~{limit['falso_alarme_esperado_por_hora']:.0f} por hora) |")
    lines += ["", "## Estabilidade entre sementes", "",
              "| Modelo | Semente | Melhor época | Épocas | Parada | Limiar |", "|---|---:|---:|---:|---|---:|"]
    for item in summary["modelos"].values():
        for seed, run in item["sementes"].items():
            lines.append(f"| {item['nome']} | {seed} | {run['melhor_epoca']} | {run['epocas_executadas']} | "
                         f"{'validação' if run['parada'] == 'paciencia' else '**teto**'} | "
                         f"{run['limiar']['limiar']:.4f} |")
    lines += ["", f"## Sensibilidade do k (p{config.percentile:g}, semente {reference})", "",
              "| Modelo | " + " | ".join(f"k = {k}" for k in config.sensitivity_k) + " |",
              "|---|" + "---:|" * len(config.sensitivity_k)]
    for item in summary["modelos"].values():
        grid = item["sementes"][reference]["sensibilidade_k"]
        lines.append(f"| {item['nome']} | " + " | ".join(f"{grid[str(k)]:.4f}" for k in config.sensitivity_k) + " |")
    lines += ["", f"## Autocorrelação dos escores de calibração (semente {reference})", "",
              "| Modelo | ACF de lag 1 por ensaio | n efetivo |", "|---|---|---:|"]
    for item in summary["modelos"].values():
        dependence = item["sementes"][reference]["autocorrelacao_escores"]
        acf = "; ".join(f"{block['ensaio']} {block['acf_lag1']:.2f}" for block in dependence["blocos"])
        lines.append(f"| {item['nome']} | {acf} | {dependence['n_efetivo']:.0f} de {dependence['n']} |")
    lines += [
        "",
        "O falso alarme esperado vale para janelas saudáveis permutáveis com as da calibração. "
        "Com escores autocorrelacionados, a média se mantém, mas a taxa observada num trecho curto "
        "varia muito mais; o n efetivo (aproximação AR(1)) dá a ordem de grandeza.",
        "",
        "O teste saudável e os ensaios com falha não foram pontuados: ficam fechados até o lote 15.",
    ]
    return "\n".join(lines) + "\n"
