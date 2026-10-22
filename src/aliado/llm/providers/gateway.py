"""Provider Gateway: uma entrada única para adapters de LLM."""

from __future__ import annotations

import os
from dataclasses import replace
from time import perf_counter
from typing import Iterator

from aliado.llm.contracts import LLMRequest, LLMResult, LLMStreamChunk
from aliado.llm.providers.base import ProviderError
from aliado.llm.providers.gemini import GeminiProvider
from aliado.llm.providers.local import LocalLimit, LocalOutOfReach, LocalProvider
from aliado.llm.providers.openai import OpenAIProvider
from aliado.llm.providers.registry import (
    ModelRegistration,
    ModelStatus,
    ProviderRegistry,
)

# Lote 38: com AL_IADO_LOCAL_MODEL, o modelo local responde primeiro; no limite do raciocínio dele, o Gemini Flash.
LOCAL, ESCALATION = ("ollama", "local"), ("google", "flash")
ESCALATED = "o modelo local não deu conta ({}): o Gemini Flash respondeu"
SKIPPED = "o modelo local não alcança este pedido ({}): seguiu direto ao modelo pago"


class ProviderGateway:
    def __init__(self, registry: ProviderRegistry | None = None):
        self.registry = registry or ProviderRegistry()

    def register_provider(self, name: str, provider) -> None:
        self.registry.register_provider(name, provider)

    def register_model(self, registration: ModelRegistration) -> None:
        self.registry.register_model(registration)

    def _local(self, provider: str):
        """O adapter e o modelo local, quando ligado e o pedido não é ele mesmo; senão None."""
        if str(provider).lower() == LOCAL[0]:
            return None
        try:
            registration = self.registry.model(*LOCAL)
        except ProviderError:
            return None  # sem AL_IADO_LOCAL_MODEL no .env: tudo segue como antes
        return self.registry.provider(LOCAL[0]), str(registration.model_id)

    def execute(
        self,
        request: LLMRequest,
        *,
        provider: str,
        model_alias: str,
        allow_experimental: bool = False,
        local: bool = True,
    ) -> LLMResult:
        """Com `local` e o modelo local ligado, ele responde primeiro: no limite do raciocínio dele, o Gemini
        Flash; o que ele não alcança vai direto ao provedor pedido; fora do ar, o erro sobe, sem gastar."""
        started, marks = perf_counter(), {}
        if local and (step := self._local(provider)):
            adapter, model_id = step
            try:
                return replace(adapter.generate(request, model_id=model_id),
                               latency_ms=(perf_counter() - started) * 1000.0)
            except LocalLimit as exc:
                provider, model_alias = ESCALATION
                marks = {"escalation_used": True, "route_reason": ESCALATED.format(exc)}
            except LocalOutOfReach as exc:
                marks = {"route_reason": SKIPPED.format(exc)}
        capabilities = self.required_capabilities(request)
        registration = self.registry.model(
            provider,
            model_alias,
            allow_experimental=allow_experimental,
            capabilities=capabilities,
        )
        adapter = self.registry.provider(provider)
        if not adapter.configured:
            from aliado.llm.providers.base import ProviderNotConfiguredError

            raise ProviderNotConfiguredError(provider)
        result = adapter.generate(request, model_id=str(registration.model_id))
        latency = (perf_counter() - started) * 1000.0
        return replace(result, latency_ms=latency, **marks)

    def stream(
        self,
        request: LLMRequest,
        *,
        provider: str,
        model_alias: str,
        allow_experimental: bool = False,
        local: bool = True,
    ) -> Iterator[LLMStreamChunk]:
        """Como `execute`. A troca acontece antes do primeiro pedaço: o local guarda o começo até saber."""
        marks = {}
        if local and (step := self._local(provider)):
            adapter, model_id = step
            try:
                yield from adapter.stream(request, model_id=model_id)
                return
            except LocalLimit as exc:
                provider, model_alias = ESCALATION
                marks = {"fallback_used": True, "route_reason": ESCALATED.format(exc)}
            except LocalOutOfReach as exc:
                marks = {"route_reason": SKIPPED.format(exc)}
        capabilities = self.required_capabilities(request)
        registration = self.registry.model(
            provider,
            model_alias,
            allow_experimental=allow_experimental,
            capabilities=capabilities,
        )
        adapter = self.registry.provider(provider)
        if not adapter.configured:
            from aliado.llm.providers.base import ProviderNotConfiguredError

            raise ProviderNotConfiguredError(provider)
        for chunk in adapter.stream(request, model_id=str(registration.model_id)):
            yield replace(chunk, **marks)

    def status(self) -> dict:
        return self.registry.status()

    @staticmethod
    def required_capabilities(request: LLMRequest) -> set[str]:
        capabilities = {"text"}
        if request.multimodal:
            capabilities.add("multimodal")
        if request.structured_output:
            capabilities.add("structured_output")
        if request.web_search:
            capabilities.add("web_search")
        return capabilities


def _model_id(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return default


def build_default_gateway(*, files=None) -> ProviderGateway:
    """`files`: o registro local do que for enviado ao serviço de arquivos do Google (leitura integral, lote 30)."""
    gateway = ProviderGateway()
    gateway.register_provider("openai", OpenAIProvider())
    gateway.register_provider("google", GeminiProvider(files=files))
    gateway.register_provider(LOCAL[0], LocalProvider())
    local = _model_id("AL_IADO_LOCAL_MODEL")
    gateway.register_model(
        ModelRegistration(
            provider=LOCAL[0],
            alias=LOCAL[1],
            model_id=local,
            status=ModelStatus.OPERATIONAL if local else ModelStatus.DISABLED,
            capabilities=frozenset({"text", "structured_output", "multimodal"}),
        )
    )

    openai_models = {
        "luna": _model_id("AL_IADO_OPENAI_MODEL_LUNA"),
        "terra": _model_id("AL_IADO_OPENAI_MODEL_TERRA"),
        "sol": _model_id("AL_IADO_OPENAI_MODEL_SOL"),
    }
    for alias, model_id in openai_models.items():
        gateway.register_model(
            ModelRegistration(
                provider="openai",
                alias=alias,
                model_id=model_id,
                status=ModelStatus.OPERATIONAL if model_id else ModelStatus.DISABLED,
                capabilities=frozenset({"text", "structured_output"}),
            )
        )

    flash_lite = _model_id(
        "AL_IADO_GEMINI_MODEL_FLASH_LITE",
        "AL_IADO_GEMINI_MODEL_FUNDO",
        "AL_IADO_GEMINI_MODEL_AUDITOR",
    )
    flash = _model_id(
        "AL_IADO_GEMINI_MODEL_FLASH",
        "AL_IADO_GEMINI_MODEL",
    )
    gateway.register_model(
        ModelRegistration(
            provider="google",
            alias="flash_lite",
            model_id=flash_lite,
            status=ModelStatus.OPERATIONAL if flash_lite else ModelStatus.DISABLED,
            capabilities=frozenset({"text", "structured_output", "web_search", "multimodal"}),
        )
    )
    gateway.register_model(
        ModelRegistration(
            provider="google",
            alias="flash",
            model_id=flash,
            status=ModelStatus.OPERATIONAL if flash else ModelStatus.DISABLED,
            capabilities=frozenset({"text", "structured_output", "web_search", "multimodal"}),
        )
    )
    return gateway


__all__ = ["ProviderGateway", "build_default_gateway"]
