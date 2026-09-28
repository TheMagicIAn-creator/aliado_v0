"""Descoberta e carregamento de skills locais empacotadas, sem executar scripts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib.resources import files

import yaml

_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_REFERENCE = re.compile(r"[a-z0-9][a-z0-9_-]*\.md")


@dataclass(frozen=True)
class SkillSummary:
    name: str
    description: str


@dataclass(frozen=True)
class Skill:
    summary: SkillSummary
    instructions: str
    references: tuple[tuple[str, str], ...]


def _root():
    return files("aliado.skills").joinpath("builtin")


def _read_entry(name: str):
    if not _NAME.fullmatch(name) or len(name) > 64:
        raise ValueError("Nome de skill inválido.")
    folder = _root().joinpath(name)
    entry = folder.joinpath("SKILL.md")
    if not entry.is_file():
        raise ValueError(f"Skill não encontrada: {name}")
    text = entry.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        raise ValueError(f"Frontmatter inválido na skill {name}.")
    header = yaml.safe_load(parts[1])
    if not isinstance(header, dict) or header.get("name") != name:
        raise ValueError(f"Identidade inválida na skill {name}.")
    description = header.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f"Descrição ausente na skill {name}.")
    return folder, header, parts[2].strip()


def list_skills() -> tuple[SkillSummary, ...]:
    summaries = []
    for folder in sorted(_root().iterdir(), key=lambda item: item.name):
        if folder.is_dir() and folder.joinpath("SKILL.md").is_file():
            _, header, _ = _read_entry(folder.name)
            summaries.append(SkillSummary(header["name"], header["description"]))
    return tuple(summaries)


def load_skill(name: str) -> Skill:
    folder, header, body = _read_entry(name)
    metadata = header.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError(f"Metadados inválidos na skill {name}.")
    declared = metadata.get("references", "")
    if not isinstance(declared, str):
        raise ValueError("metadata.references deve ser texto.")
    references = []
    for reference in (part.strip() for part in declared.split(",")):
        if not reference:
            continue
        if not _REFERENCE.fullmatch(reference):
            raise ValueError(f"Nome de referência inválido: {reference}")
        resource = folder.joinpath("references", reference)
        if not resource.is_file():
            raise ValueError(f"Referência não encontrada: {reference}")
        references.append((reference, resource.read_text(encoding="utf-8")))
    return Skill(SkillSummary(header["name"], header["description"]), body, tuple(references))
