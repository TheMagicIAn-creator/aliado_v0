"""Adapter Gemini extraído da origem, com papéis e contexto explícitos.

Aceita texto, JSON e, num pedido multimodal, imagens na mensagem do usuário (lote 29).
Ferramentas serão adaptadas e validadas em seu próprio lote.
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Iterator
from typing import Any

from aliado.llm.contracts import LLMRequest, LLMResult, LLMStreamChunk, LLMUsage
from aliado.llm.providers.base import (
    ProviderNotConfiguredError,
    classify_provider_exception,
    normalized_messages,
)


def _usage(response) -> LLMUsage | None:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return None
    return LLMUsage(
        input_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
        total_tokens=getattr(usage, "total_token_count", None),
        # Tokens de raciocínio são cobrados, mas não entram em candidates_token_count.
        reasoning_tokens=getattr(usage, "thoughts_token_count", None),
        cached_tokens=getattr(usage, "cached_content_token_count", None),
    )


def _truncated(response) -> bool:
    """O modelo parou no teto de tokens de saída (o raciocínio conta nele): o texto ficou cortado."""
    candidates = getattr(response, "candidates", None) or []
    reason = getattr(candidates[0], "finish_reason", None) if candidates else None
    return str(getattr(reason, "name", reason) or "").upper().endswith("MAX_TOKENS")


def _grounding(response) -> dict:
    """Fontes, consultas e trechos sustentados da busca na web (grounding), se houver."""
    candidates = getattr(response, "candidates", None) or []
    metadata = getattr(candidates[0], "grounding_metadata", None) if candidates else None
    if metadata is None:
        return {}
    sources, positions = [], {}
    for index, chunk in enumerate(getattr(metadata, "grounding_chunks", None) or []):
        web = getattr(chunk, "web", None)
        if web is not None and getattr(web, "uri", None):
            positions[index] = len(sources) + 1  # número exibido: ordem entre as fontes da web
            sources.append({"uri": web.uri, "title": getattr(web, "title", None) or "",
                            "domain": getattr(web, "domain", None) or ""})
    supports = []
    for support in getattr(metadata, "grounding_supports", None) or []:
        text = getattr(getattr(support, "segment", None), "text", None)
        numbers = sorted({positions[i] for i in getattr(support, "grounding_chunk_indices", None) or []
                          if i in positions})
        if text and numbers:
            supports.append({"text": text, "sources": numbers})
    queries = tuple(q for q in getattr(metadata, "web_search_queries", None) or [] if q)
    if not (sources or queries):
        return {}
    return {"web_sources": tuple(sources), "web_queries": queries, "web_supports": tuple(supports)}


IMAGE_TYPES = {"image/png", "image/jpeg"}
MEDIA_RESOLUTIONS = {"low": "MEDIA_RESOLUTION_LOW", "medium": "MEDIA_RESOLUTION_MEDIUM", "high": "MEDIA_RESOLUTION_HIGH"}


def _parts(content, role: str, multimodal: bool) -> list[dict[str, Any]]:
    """As partes de uma mensagem: texto ou, num pedido multimodal, texto e imagens do usuário."""
    if isinstance(content, str):
        return [{"text": content}]
    if not multimodal or role != "user" or not isinstance(content, list) or not content:
        raise ValueError("Conteúdo Gemini deve ser texto; imagem, só em mensagem do usuário de um pedido multimodal.")
    parts: list[dict[str, Any]] = []
    for item in content:
        kind = item.get("type") if isinstance(item, dict) else None
        if kind == "text" and isinstance(item.get("text"), str):
            parts.append({"text": item["text"]})
        elif kind == "image" and isinstance(item.get("data"), bytes) and item.get("mime_type") in IMAGE_TYPES:
            parts.append({"inline_data": {"mime_type": item["mime_type"], "data": item["data"]}})
        else:
            raise ValueError("Parte de mensagem não suportada: use texto ou imagem PNG ou JPEG.")
    return parts


class GeminiProvider:
    name = "google"

    def __init__(self, api_key: str | None = None, *, client=None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self._client = client
        self._lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(self.api_key or self._client is not None)

    def _get_client(self):
        # Com várias threads no primeiro pedido (a descrição das figuras, lote 29), cada uma criava o seu
        # cliente, e o que era descartado fechava a conexão de um pedido em andamento.
        with self._lock:
            if self._client is not None:
                return self._client
            if not self.api_key:
                raise ProviderNotConfiguredError(self.name)
            try:
                from google import genai
            except ImportError as exc:
                raise ProviderNotConfiguredError(self.name) from exc
            self._client = genai.Client(api_key=self.api_key)
            return self._client

    @staticmethod
    def _kwargs(request: LLMRequest, model_id: str) -> dict[str, Any]:
        if request.tools:
            raise ValueError("O adapter Gemini não aceita ferramentas.")
        instructions: list[str] = []
        contents: list[dict[str, Any]] = []
        for message in normalized_messages(request):
            role, content = message["role"], message["content"]
            if role in {"system", "developer"}:
                if not isinstance(content, str):
                    raise ValueError("Instruções Gemini devem ser texto.")
                instructions.append(content)
            elif role in {"user", "assistant"}:
                contents.append({
                    "role": "model" if role == "assistant" else "user",
                    "parts": _parts(content, role, request.multimodal),
                })
            else:
                raise ValueError(f"Papel não suportado: {role}")
        if not contents:
            raise ValueError("O pedido precisa conter uma mensagem de conversa.")
        config: dict[str, Any] = {}
        if instructions:
            config["system_instruction"] = "\n\n".join(instructions)
        if request.max_output_tokens is not None:
            config["max_output_tokens"] = request.max_output_tokens
        if request.temperature is not None:
            config["temperature"] = request.temperature
        if request.reasoning_level:
            config["thinking_config"] = {"thinking_level": request.reasoning_level}
        if request.structured_output:
            config["response_mime_type"] = "application/json"
            config["response_json_schema"] = request.structured_output
        resolution = request.metadata.get("media_resolution") if request.multimodal else None
        if resolution is not None:
            if resolution not in MEDIA_RESOLUTIONS:
                raise ValueError("Resolução de imagem desconhecida: use low, medium ou high.")
            config["media_resolution"] = MEDIA_RESOLUTIONS[resolution]
        if request.web_search:
            if request.structured_output:
                raise ValueError("Busca na web e saída estruturada não são combinadas neste adapter.")
            config["tools"] = [{"google_search": {}}]
        return {"model": model_id, "contents": contents, "config": config}

    def generate(self, request: LLMRequest, *, model_id: str) -> LLMResult:
        kwargs = self._kwargs(request, model_id)
        try:
            response = self._get_client().models.generate_content(**kwargs)
            content = getattr(response, "text", "") or ""
            truncated = _truncated(response)
            try:
                structured = json.loads(content) if request.structured_output else None
            except json.JSONDecodeError:
                if not truncated:
                    raise
                # Cortada no teto de tokens, o JSON vem pela metade. A chamada foi cobrada: o resultado
                # segue, sem os dados e marcado como cortado, para o uso entrar no registro (lote 29).
                structured = None
            if request.structured_output and not truncated and not isinstance(structured, dict):
                raise ValueError("A saída estruturada Gemini deve ser um objeto JSON.")
            return LLMResult(
                content=content,
                provider=self.name,
                model=model_id,
                task_type=request.task_type,
                structured_data=structured if isinstance(structured, dict) else None,
                usage=_usage(response),
                truncated=truncated,
                **_grounding(response),
            )
        except (ProviderNotConfiguredError, ValueError):
            raise
        except Exception as exc:
            raise classify_provider_exception(exc, self.name) from exc

    def stream(self, request: LLMRequest, *, model_id: str) -> Iterator[LLMStreamChunk]:
        if request.structured_output:
            result = self.generate(request, model_id=model_id)
            yield LLMStreamChunk(result.content, self.name, model_id, request.task_type)
            return
        kwargs = self._kwargs(request, model_id)
        try:
            for item in self._get_client().models.generate_content_stream(**kwargs):
                content = getattr(item, "text", "") or ""
                usage = _usage(item)
                grounding = _grounding(item)
                truncated = _truncated(item)
                if content or usage or grounding or truncated:
                    yield LLMStreamChunk(content, self.name, model_id, request.task_type, usage=usage,
                                         truncated=truncated, **grounding)
        except ProviderNotConfiguredError:
            raise
        except Exception as exc:
            raise classify_provider_exception(exc, self.name) from exc
