"""Formato dos resultados da pesquisa no chat (lotes 26 e 36): números como na tela e o texto que vai ao modelo.

Os blocos citáveis [R1]… vêm da especialização que tem resultados (`results_digest`). Aqui fica o que vale
para qualquer uma: a formatação dos números igual à da tela, o texto dos blocos para o modelo, com as notas
dos indicadores uma vez só, e o que a conferência dos números lê de cada bloco.
"""

from __future__ import annotations

import json
from decimal import Decimal

# Nomes das seções da aba Ciência, como na tela (SCIENCE_TABS em ciencia.js); um teste compara.
SECTIONS = {"resumo": "Resumo", "metricas": "Métricas por falha", "inicio": "Início das falhas", "fmeca": "FMECA",
            "confiabilidade": "Confiabilidade", "explorar": "Explorar"}


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
