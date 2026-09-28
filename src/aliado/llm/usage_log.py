"""Registro local do consumo de tokens por chamada, sem o conteúdo da conversa."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from aliado.llm.contracts import LLMResult, LLMUsage

DEFAULT_USAGE_LOG = Path("data/uso/chamadas.jsonl")


def usage_line(result: LLMResult) -> str:
    """Resumo legível dos tokens informados pelo provedor."""
    usage = result.usage or LLMUsage()
    parts = [("entrada", usage.input_tokens), ("saída", usage.output_tokens),
             ("raciocínio", usage.reasoning_tokens), ("total", usage.total_tokens)]
    tokens = " | ".join(f"{label}: {'?' if value is None else value}" for label, value in parts)
    searches = f" | buscas na web: {len(result.web_queries)}" if result.web_queries else ""
    return f"Tokens — {tokens}{searches}"


def record_usage(result: LLMResult, path: str | Path = DEFAULT_USAGE_LOG) -> dict:
    """Acrescenta uma linha JSON com data, provedor, modelo e tokens; nunca o texto."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provider": result.provider,
        "model": result.model,
        "task_type": result.task_type,
        **asdict(result.usage or LLMUsage()),
        # A busca na web é cobrada à parte; registra-se a quantidade, nunca as consultas.
        "web_queries": len(result.web_queries),
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry
