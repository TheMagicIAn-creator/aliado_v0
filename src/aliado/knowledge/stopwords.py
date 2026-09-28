"""Palavras vazias em português e inglês, ignoradas na parte da busca por palavras (lote 19).

Lista fixada antes da medição com as perguntas de referência. Fica sem acento e em minúsculas,
como o índice lexical (`remove_diacritics`). Inclui palavras de pergunta ("qual", "segundo",
"according"), que não dizem nada sobre o conteúdo procurado.
"""

from __future__ import annotations

import unicodedata

_PORTUGUESE = """
a ao aos as ate com como contra da das de dela dele deles do dos e ela elas ele eles em entre era
essa essas esse esses esta estas este estes eu foi foram ha isso isto ja la lhe mais mas me mesmo
meu minha muito na nas nem no nos nossa nosso num numa o os ou para pela pelas pelo pelos por qual
quais quando que quem se sem ser seu seus sua suas sao so tambem te tem ter um uma umas uns voce
voces sobre segundo conforme onde porque qual quanto quanta quantos quantas cujo cuja ha sera
seria sido sendo estao esta estava estavam fazer faz feito pode podem deve devem via cada outro
outra outros outras todo toda todos todas apos antes depois ainda assim entao aqui ali
"""

_ENGLISH = """
a about above after again against all am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has
have having he her here hers herself him himself his how i if in into is it its itself just me
more most my myself no nor not now of off on once only or other our ours ourselves out over own
same she should so some such than that the their theirs them themselves then there these they
this those through to too under until up very was we were what when where which while who whom
why will with would you your yours yourself yourselves according whose
"""


def plain(text: str) -> str:
    """Minúsculas e sem acento, para comparar palavras como o índice lexical."""
    decomposed = unicodedata.normalize("NFKD", str(text or "").lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


STOPWORDS = frozenset(plain(word) for word in (_PORTUGUESE + _ENGLISH).split())
