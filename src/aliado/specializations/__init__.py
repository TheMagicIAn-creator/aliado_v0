"""Especializações: pesquisas e projetos que o núcleo carrega sem conhecer pelo nome (spec 0034).

Cada uma é um pacote dentro desta pasta. O núcleo as acha percorrendo a pasta na primeira vez que
precisa delas e lê só atributos do pacote; nada daqui é importado ao abrir o AL-IAdo.
"""

from __future__ import annotations

import pkgutil
from functools import cache
from importlib import import_module


@cache
def installed() -> tuple:
    """Os pacotes de especialização, em ordem de nome."""
    names = sorted(item.name for item in pkgutil.iter_modules(__path__) if item.ispkg)
    return tuple(import_module(f"{__name__}.{name}") for name in names)


def gather(attribute: str) -> list:
    """O atributo de cada especialização que o tem, na mesma ordem."""
    return [getattr(package, attribute) for package in installed() if hasattr(package, attribute)]
