"""Adapter do modelo local (lote 38): um modelo aberto servido pelo Ollama, pela API compatível com a OpenAI.

Com `AL_IADO_LOCAL_MODEL` no .env, o modelo local (provedor `ollama`, apelido `local`) é o principal: o gateway o
tenta primeiro e só passa ao Gemini Flash quando ele não dá conta do raciocínio (`LocalLimit`) ou quando o pedido
está fora do alcance dele (`LocalOutOfReach`). Fora do ar, o erro é claro e nada vai ao Gemini (`LocalUnavailable`).
O Ollama aceita imagem só em base64 e não lê PDF. As páginas vão como o texto guardado que a leitura já traz em cada
parte, com a descrição das figuras (lote 39); só a parte sem texto vai como imagem, até `MAX_PAGES` por pedido.
"""

from __future__ import annotations

import base64
import io
import json
import os
from collections.abc import Iterator
from typing import Any

from aliado.llm.contracts import LLMRequest, LLMResult, LLMStreamChunk, LLMUsage
from aliado.llm.providers.base import (
    IMAGE_TYPES,
    ProviderError,
    document_bytes,
    is_document,
    normalized_messages,
)

BASE_URL = "http://localhost:11434/v1"
ESCALATE = "[ESCALAR]"
ESCALATE_RULE = (f"Se a pergunta pedir um raciocínio que você não consegue fazer com segurança, responda apenas "
                 f"{ESCALATE}, sem mais nada: outro modelo responderá.")
# Letras guardadas no começo do fluxo: na Etapa 3, o pedido de ajuda veio depois de um rótulo ("Resposta ao usuário:").
HOLD = 160
# Lote 39: o local lê o texto guardado das páginas, e não o PDF de que as regras falam; e, na medição do lote 38, citou
# documentos por extenso, sem as marcas, em 3 das 16 perguntas, refeitas pelo Gemini.
TEXT_NOTE = ("Para você, os PDFs vieram como o texto guardado de cada página, com o [K...] dela, e a descrição "
             "automática das figuras e tabelas; onde as regras falam em ler o PDF, leia por esse texto. A descrição é "
             "automática e deve ser conferida no original.")
CITE_RULE = ("Cite cada afirmação com o identificador entre colchetes, exatamente como veio, por exemplo [K12ab34p5], "
             "logo depois da frase; não cite só pelo nome do arquivo ou do autor.")
# O num_ctx do Modelfile: o Ollama corta em silêncio o que passa dele, então o pedido maior nem vai ao local.
CONTEXT = 16_384
MIN_ANSWER = 1_024  # tokens que precisam sobrar para a resposta
MAX_PAGES, PAGE_SIDE = 4, 1_024
CHARS_PER_TOKEN, IMAGE_TOKENS = 3, 1_800  # estimativas: texto em português e uma página a 1.024 px


class LocalLimit(ProviderError):
    """O modelo local não deu conta do raciocínio: o gateway passa ao Gemini Flash."""


class LocalOutOfReach(ProviderError):
    """O pedido está fora do alcance do modelo local (contexto, páginas ou busca na web): vai direto ao pedido."""


class LocalUnavailable(ProviderError):
    """O Ollama está fora do ar, recusou o pedido ou o modelo não foi baixado: erro claro, sem chamar o Gemini."""


def _image(mime_type: str, data: bytes) -> dict[str, Any]:
    return {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64.b64encode(data).decode()}"}}


def _page_images(pdf: bytes) -> list[bytes]:
    """As páginas de um PDF como JPEG, com o lado maior em `PAGE_SIDE` pixels."""
    import pypdfium2 as pdfium

    from aliado.knowledge.extraction import PDFIUM

    images = []
    with PDFIUM, pdfium.PdfDocument(pdf) as document:
        for index in range(len(document)):
            page = document[index]
            bitmap = page.render(scale=PAGE_SIDE / max(page.get_size()))
            buffer = io.BytesIO()
            bitmap.to_pil().convert("RGB").save(buffer, format="JPEG", quality=85)
            bitmap.close()
            page.close()
            images.append(buffer.getvalue())
    return images


def _usage(response) -> LLMUsage | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    return LLMUsage(input_tokens=getattr(usage, "prompt_tokens", None),
                    output_tokens=getattr(usage, "completion_tokens", None),
                    total_tokens=getattr(usage, "total_tokens", None))


class LocalProvider:
    name = "ollama"

    def __init__(self, base_url: str | None = None, *, client=None, context: int | None = None):
        self.base_url = base_url or os.getenv("AL_IADO_LOCAL_BASE_URL") or BASE_URL
        self.context = int(context or os.getenv("AL_IADO_LOCAL_CONTEXT") or CONTEXT)
        self._client = client

    @property
    def configured(self) -> bool:
        return True  # sem chave: basta o Ollama no ar, conferido a cada chamada

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ModuleNotFoundError as exc:
                raise LocalUnavailable("O modelo local precisa do pacote openai: instale os extras com "
                                       "pip install -e .[llm].", unavailable=True) from exc
            # Sem repetição: com o Ollama fechado, repetir só atrasa o erro; lento, repetir triplicaria a espera.
            self._client = OpenAI(base_url=self.base_url, api_key="ollama", max_retries=0)
        return self._client

    def _messages(self, request: LLMRequest) -> tuple[list[dict[str, Any]], int]:
        """As mensagens no formato do Ollama e a estimativa de tokens da entrada; `LocalOutOfReach` se não couber."""
        instructions, messages, chars, images, converted = [], [], 0, 0, False
        for message in normalized_messages(request):
            role, content = message["role"], message["content"]
            if role in {"system", "developer"}:
                if not isinstance(content, str):
                    raise ValueError("Instruções do modelo local devem ser texto.")
                instructions.append(content)
            elif role not in {"user", "assistant"}:
                raise ValueError(f"Papel não suportado: {role}")
            elif isinstance(content, str):
                messages.append({"role": role, "content": content})
                chars += len(content)
            elif not request.multimodal or role != "user" or not isinstance(content, list) or not content:
                raise ValueError("Conteúdo do modelo local deve ser texto; imagem e documento, só em mensagem do "
                                 "usuário de um pedido multimodal.")
            else:
                parts = []
                for item in content:
                    kind = item.get("type") if isinstance(item, dict) else None
                    if kind == "text" and isinstance(item.get("text"), str):
                        parts.append({"type": "text", "text": item["text"]})
                        chars += len(item["text"])
                    elif kind == "image" and isinstance(item.get("data"), bytes) and item.get("mime_type") in IMAGE_TYPES:
                        parts.append(_image(item["mime_type"], item["data"]))
                        images += 1
                    elif is_document(item) and isinstance(item.get("text"), str):
                        # Lote 39: o texto guardado das páginas no lugar do PDF, que nem é aberto; vale o contexto.
                        if item["text"]:
                            parts.append({"type": "text", "text": item["text"]})
                            chars += len(item["text"])
                        converted = True
                    elif is_document(item):
                        # As páginas do recorte são contadas antes de abrir o PDF; depois, as que ele tem de fato.
                        if images + len(item.get("pages") or ()) > MAX_PAGES:
                            raise LocalOutOfReach(f"mais de {MAX_PAGES} páginas de documento")
                        pages = _page_images(document_bytes(item))
                        images += len(pages)
                        if images > MAX_PAGES:
                            raise LocalOutOfReach(f"mais de {MAX_PAGES} páginas de documento")
                        parts += [_image("image/jpeg", page) for page in pages]
                    else:
                        raise ValueError("Parte de mensagem não suportada: use texto, imagem PNG ou JPEG ou documento PDF.")
                messages.append({"role": role, "content": parts})
        if not messages:
            raise ValueError("O pedido precisa conter uma mensagem de conversa.")
        # A instrução do pedido de ajuda só vale para texto livre: na saída estruturada, o JSON inválido faz esse papel.
        system = "\n\n".join([*instructions, *(() if request.structured_output else (ESCALATE_RULE,)),
                              *((TEXT_NOTE,) if converted else ()),
                              *((CITE_RULE,) if request.metadata.get("citations") else ())])
        tokens = (chars + len(system)) // CHARS_PER_TOKEN + images * IMAGE_TOKENS
        if self.context - tokens < MIN_ANSWER:
            raise LocalOutOfReach(f"cerca de {tokens} tokens, acima do contexto local de {self.context}")
        return [{"role": "system", "content": system}, *messages], tokens

    def _kwargs(self, request: LLMRequest, model_id: str) -> dict[str, Any]:
        if request.web_search:
            raise LocalOutOfReach("busca na web")
        messages, tokens = self._messages(request)
        room = self.context - tokens
        kwargs: dict[str, Any] = {"model": model_id, "messages": messages,
                                  "max_tokens": min(int(request.max_output_tokens or room), room)}
        if request.temperature is not None:
            kwargs["temperature"] = float(request.temperature)
        # "none" desliga o raciocínio no Ollama: na Etapa 3, 4 tokens em 0,5 s, contra 372 tokens em 27 s. No lote 41, sem
        # raciocínio também nos trechos, o local deixou de citar (P5 e P6) e a trava de qualidade desfez essa parte.
        if request.reasoning_level == "low":
            kwargs["reasoning_effort"] = "none"
        if request.tools:
            kwargs["tools"] = request.tools
        if request.structured_output:
            kwargs["response_format"] = {"type": "json_schema", "json_schema": {
                "name": "aliado_response", "strict": True, "schema": request.structured_output}}
        return kwargs

    def _failure(self, exc: Exception) -> LocalUnavailable:
        """Toda falha técnica do local é erro claro, sem passar ao Gemini: decisão do pesquisador (lote 38)."""
        status = getattr(exc, "status_code", None)
        hint = ("o modelo do .env (AL_IADO_LOCAL_MODEL) não foi baixado no Ollama" if status == 404
                else f"o Ollama recusou o pedido (código {status}); confira a memória livre e o modelo" if status
                else "abra o Ollama e confira o endereço do .env (AL_IADO_LOCAL_BASE_URL)")
        return LocalUnavailable(f"O modelo local não respondeu em {self.base_url}: {hint}.", unavailable=True,
                                status_code=status)

    def generate(self, request: LLMRequest, *, model_id: str) -> LLMResult:
        kwargs = self._kwargs(request, model_id)
        try:
            response = self._get_client().chat.completions.create(**kwargs)
        except ProviderError:
            raise
        except Exception as exc:
            raise self._failure(exc) from exc
        choice = response.choices[0] if getattr(response, "choices", None) else None
        content = (getattr(getattr(choice, "message", None), "content", None) or "") if choice else ""
        truncated = getattr(choice, "finish_reason", None) == "length"
        structured = None
        if request.structured_output and not truncated:
            try:
                structured = json.loads(content)
            except json.JSONDecodeError as exc:
                raise LocalLimit("a saída estruturada veio inválida") from exc
            if not isinstance(structured, dict):
                raise LocalLimit("a saída estruturada não é um objeto JSON")
        elif not request.structured_output and not truncated and (not content.strip() or ESCALATE in content):
            raise LocalLimit("pediu ajuda" if content.strip() else "não respondeu nada")
        return LLMResult(content=content, provider=self.name, model=model_id, task_type=request.task_type,
                         structured_data=structured, usage=_usage(response), truncated=truncated)

    def stream(self, request: LLMRequest, *, model_id: str) -> Iterator[LLMStreamChunk]:
        if request.structured_output:
            result = self.generate(request, model_id=model_id)
            yield LLMStreamChunk(result.content, self.name, model_id, request.task_type, usage=result.usage,
                                 truncated=result.truncated)
            return
        kwargs = self._kwargs(request, model_id) | {"stream": True, "stream_options": {"include_usage": True}}
        try:
            held, shown, usage, truncated = "", False, None, False
            for event in self._get_client().chat.completions.create(**kwargs):
                choice = event.choices[0] if getattr(event, "choices", None) else None
                text = (getattr(getattr(choice, "delta", None), "content", None) or "") if choice else ""
                cut = getattr(choice, "finish_reason", None) == "length"
                usage, truncated = _usage(event) or usage, truncated or cut
                if shown:
                    if text or cut or _usage(event):
                        yield LLMStreamChunk(text, self.name, model_id, request.task_type, usage=_usage(event),
                                             truncated=cut)
                    continue
                # O começo fica guardado até mostrar se é o pedido de ajuda: assim a troca acontece antes da tela.
                # O pedido que vier depois dele a conversa ainda pega (`_local_missed`) e refaz pelo Gemini.
                held += text
                if ESCALATE in held:
                    raise LocalLimit("pediu ajuda")
                if len(held.strip()) >= HOLD:
                    shown = True
                    yield LLMStreamChunk(held, self.name, model_id, request.task_type, usage=usage, truncated=truncated)
            if not shown:
                if not held.strip() and not truncated:
                    raise LocalLimit("não respondeu nada")
                yield LLMStreamChunk(held, self.name, model_id, request.task_type, usage=usage, truncated=truncated)
        except ProviderError:
            raise
        except Exception as exc:
            raise self._failure(exc) from exc


__all__ = ["ESCALATE", "LocalLimit", "LocalOutOfReach", "LocalProvider", "LocalUnavailable"]
