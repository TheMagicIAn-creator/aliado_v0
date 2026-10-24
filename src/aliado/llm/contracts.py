"""Contratos neutros para inferência por modelos de linguagem."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MethodologicalRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class LLMRequest:
    """Pedido independente de SDK encaminhado ao Gateway/Router."""

    task_type: str
    messages: list[Any]
    context: Any | None = None
    tools: list[Any] | None = None
    structured_output: dict[str, Any] | None = None
    reasoning_level: str | None = None
    multimodal: bool = False
    methodological_risk: str = MethodologicalRisk.LOW
    max_cost: float | None = None
    max_latency: float | None = None
    max_output_tokens: int | None = None
    temperature: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    # Busca na web do provedor (grounding); só quando o usuário a liga no pedido.
    web_search: bool = False

    def __post_init__(self) -> None:
        if not str(self.task_type).strip():
            raise ValueError("task_type não pode ser vazio")
        if not isinstance(self.messages, list) or not self.messages:
            raise ValueError("messages deve ser uma lista não vazia")
        if str(self.methodological_risk) not in set(MethodologicalRisk):
            raise ValueError("methodological_risk inválido")
        if self.max_cost is not None and float(self.max_cost) < 0:
            raise ValueError("max_cost não pode ser negativo")
        if self.max_latency is not None and float(self.max_latency) <= 0:
            raise ValueError("max_latency deve ser positivo")
        if self.max_output_tokens is not None and int(self.max_output_tokens) <= 0:
            raise ValueError("max_output_tokens deve ser positivo")


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_tokens: int | None = None
    # Parte da entrada servida pelo cache do provedor (lote 26); mede o desconto real.
    cached_tokens: int | None = None


@dataclass(frozen=True)
class LLMResult:
    content: str
    provider: str
    model: str
    task_type: str
    latency_ms: float | None = None
    estimated_cost: float | None = None
    fallback_used: bool = False
    validation_used: bool = False
    structured_data: dict[str, Any] | None = None
    usage: LLMUsage | None = None
    attempts: int = 1
    route_reason: str | None = None
    fallback_kind: str | None = None
    escalation_used: bool = False
    validation_status: str | None = None
    validation_conflict: bool = False
    reviewer_provider: str | None = None
    reviewer_model: str | None = None
    # Trechos da biblioteca efetivamente citados, na ordem de aparição.
    sources: tuple[dict[str, Any], ...] = ()
    # Trechos que a busca trouxe e a resposta não citou, na ordem da busca (lote 27).
    retrieved: tuple[dict[str, Any], ...] = ()
    # O provedor parou no teto de tokens de saída: o texto ficou cortado (lote 27).
    truncated: bool = False
    # Busca na web: fontes (uri, title, domain), consultas feitas e trechos sustentados.
    web_sources: tuple[dict[str, Any], ...] = ()
    web_queries: tuple[str, ...] = ()
    web_supports: tuple[dict[str, Any], ...] = ()
    # Resultados da pesquisa (lote 26): blocos citados, estado da conferência e números que não conferem.
    result_sources: tuple[dict[str, Any], ...] = ()
    results_status: str | None = None
    unverified_numbers: tuple[str, ...] = ()
    # Quantos números ficaram em parágrafos sem marca de resultado: não foram conferidos.
    unmarked_numbers: int = 0
    # Leitura integral (lote 30): os documentos enviados inteiros ou em blocos, sem o texto das páginas.
    reading: dict[str, Any] | None = None
    # Cobertura documental por parte do pedido, distinta da validade das citações.
    coverage: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError("content deve ser texto")
        if not self.provider or not self.model or not self.task_type:
            raise ValueError("provider, model e task_type são obrigatórios")


@dataclass(frozen=True)
class LLMStreamChunk:
    content: str
    provider: str
    model: str
    task_type: str
    fallback_used: bool = False
    route_reason: str | None = None
    # Consumo acumulado informado pelo provedor; o último valor recebido vale.
    usage: LLMUsage | None = None
    # Metadados da busca na web; chegam nos últimos pedaços do fluxo.
    web_sources: tuple[dict[str, Any], ...] = ()
    web_queries: tuple[str, ...] = ()
    web_supports: tuple[dict[str, Any], ...] = ()
    # O provedor parou no teto de tokens de saída; chega no último pedaço do fluxo.
    truncated: bool = False


__all__ = [
    "LLMRequest",
    "LLMResult",
    "LLMStreamChunk",
    "LLMUsage",
    "MethodologicalRisk",
]
