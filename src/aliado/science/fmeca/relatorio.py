"""O texto do relatório da FMECA em Markdown: o NPR, a leitura pelas taxas e as duas lado a lado, sem fundir."""

from __future__ import annotations

BASIS_NAMES = {"operation": "operação", "calendar": "calendário"}


def _percent(probability: float) -> str:
    return "> 99.9%" if probability > 0.999 else f"{100 * probability:.1f}%"


def _name(items: list[dict], item_id: str) -> str:
    return next(item["nome"] for item in items if item["id"] == item_id)


def _markdown(result: dict) -> str:
    items = result["itens"]
    lines = [
        f"# {result['nome']}", "",
        f"Decidida em {result['decidida_em']}. {result['criterio']} Notas: {result['fonte_notas']}", "",
        "## 1. Criticidade pelas notas (NPR)", "",
        "| Prioridade | Grupo | Item na fonte | S | O | D | NPR |", "|---:|---|---|---:|---:|---:|---:|",
        *[f"| {item['posicoes']['npr']} | {item['nome']} | {item['item_na_fonte']} | {item['S']} | {item['O']} | "
          f"{item['D']} | {item['npr']} |" for item in items],
        "", "## 2. Leitura pelas taxas de falha (separada; não altera as notas)", "",
    ]
    horizons = [str(t) for t in result["horizontes_anos"]]
    header = " | ".join(f"Chance de falhar em {t} ano(s) | Falhas esperadas em {t} ano(s)" for t in horizons)
    lines += [f"| Ordem | Grupo | λ (1/h) | Base | MTBF (h) | MTBF (anos) | {header} |",
              "|---:|---|---:|---|---:|---:|" + "---:|" * (2 * len(horizons))]
    for item in sorted((i for i in items if i["posicoes"]["taxa"]), key=lambda i: i["posicoes"]["taxa"]):
        for reading in item["leitura_pelas_taxas"]:
            values = " | ".join(f"{_percent(reading['horizontes'][t]['chance_de_falhar'])} | "
                                f"{reading['horizontes'][t]['falhas_esperadas']:.2f}" for t in horizons)
            lines.append(f"| {item['posicoes']['taxa']} | {item['nome']} | {reading['taxa_por_hora']:.3g} | "
                         f"{BASIS_NAMES[reading['base']]} ({reading['horas_por_ano']:g} h/ano) | "
                         f"{reading['mtbf_horas']:.0f} | {reading['mtbf_anos']:.1f} | {values} |")
    lines += ["", "## 3. As duas leituras lado a lado", "",
              "| Grupo | Posição pelo NPR | Posição pela ocorrência O | Posição pela taxa λ |", "|---|---:|---:|---:|",
              *[f"| {item['nome']} | {item['posicoes']['npr']} | {item['posicoes']['ocorrencia']} | "
                f"{item['posicoes']['taxa'] or '—'} |" for item in items], ""]
    if result["pares_discordantes_O_taxa"]:
        lines.append("Pares em que a ocorrência e a taxa apontam em sentidos opostos:")
        lines += [f"- {_name(items, pair['maior_O'])} tem O maior que {_name(items, pair['menor_O'])} "
                  f"({pair['O'][0]} > {pair['O'][1]}), mas taxa menor ({pair['taxas'][0]:.3g} < {pair['taxas'][1]:.3g} por hora)."
                  for pair in result["pares_discordantes_O_taxa"]]
        lines.append("")
    lines += ["As notas vêm de um levantamento de campo e as taxas, de outras fontes e populações. As duas "
              "leituras não são fundidas numa nota única.", "", "## 4. Ressalvas e limites", "",
              *[f"- {text}" for text in result["ressalvas"]],
              *[f"- {item['nome']}: {text}" for item in items for text in item["ressalvas"]],
              *[f"- {text}" for text in result["limites"]], "", "## Fontes das taxas", ""]
    for item in items:
        sources = {source for reading in item["leitura_pelas_taxas"] for source in reading["fontes"]}
        lines += [f"- {item['nome']}: " + " ".join(sorted(sources))]
    return "\n".join(lines) + "\n"
