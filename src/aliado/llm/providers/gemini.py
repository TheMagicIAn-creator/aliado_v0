"""Adapter Gemini extraído da origem, com papéis e contexto explícitos.

Aceita texto, JSON e, num pedido multimodal, imagens (lote 29) e documentos em PDF (lote 30) na
mensagem do usuário. Ferramentas serão adaptadas e validadas em seu próprio lote.
"""

from __future__ import annotations

import io
import json
import os
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
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
DOCUMENT_TYPES = {"application/pdf"}
MEDIA_RESOLUTIONS = {"low": "MEDIA_RESOLUTION_LOW", "medium": "MEDIA_RESOLUTION_MEDIUM", "high": "MEDIA_RESOLUTION_HIGH"}
# Documentos em PDF (lote 30). Havendo registro de envios, todo PDF sobe pelo serviço de arquivos: cada um
# sobe uma vez e serve às perguntas seguintes enquanto durar, e as leituras do piloto de 03/10/2026 tinham de
# 18 a 93 MB, acima do que cabe num pedido direto. Sem registro, o PDF segue dentro do pedido, que aceita
# cerca de 20 MB com os arquivos um terço maiores e o texto: daí o limite abaixo.
INLINE_BYTES = 12 * 1024 * 1024
# O serviço guarda um arquivo por 48 horas; um envio só é reaproveitado com esta folga antes do fim.
FILE_MARGIN = timedelta(hours=1)
FILE_LIFE = timedelta(hours=47)
FILE_WAIT = 60.0  # segundos à espera de o serviço terminar de receber um arquivo
UPLOAD_WORKERS = 4  # envios ao serviço de arquivos ao mesmo tempo


def _is_document(item) -> bool:
    """Documento em PDF: o conteúdo ou uma função que o lê só se for preciso."""
    if not isinstance(item, dict) or item.get("type") != "document" or item.get("mime_type") not in DOCUMENT_TYPES:
        return False
    data = item.get("data")
    return callable(data) or (isinstance(data, bytes) and bool(data))


def _document_bytes(item: dict) -> bytes:
    data = item["data"]
    if callable(data):
        try:
            data = data()
        except Exception as exc:  # leitura ou recorte do arquivo local: não é falha do provedor
            raise ValueError("Não foi possível ler um documento do pedido.") from exc
    if not isinstance(data, bytes) or not data:
        raise ValueError("Documento do pedido sem conteúdo.")
    return data


def _state(file) -> str:
    state = getattr(file, "state", None)
    return str(getattr(state, "name", state) or "").upper()


def _parts(content, role: str, multimodal: bool, documents: dict | None = None) -> list[dict[str, Any]]:
    """As partes de uma mensagem: texto ou, num pedido multimodal, texto, imagens e documentos do usuário.

    `documents` diz, pela chave, os documentos que estão no serviço de arquivos; os outros seguem no pedido."""
    if isinstance(content, str):
        return [{"text": content}]
    if not multimodal or role != "user" or not isinstance(content, list) or not content:
        raise ValueError("Conteúdo Gemini deve ser texto; imagem e documento, só em mensagem do usuário de um "
                         "pedido multimodal.")
    parts: list[dict[str, Any]] = []
    for item in content:
        kind = item.get("type") if isinstance(item, dict) else None
        if kind == "text" and isinstance(item.get("text"), str):
            parts.append({"text": item["text"]})
        elif kind == "image" and isinstance(item.get("data"), bytes) and item.get("mime_type") in IMAGE_TYPES:
            parts.append({"inline_data": {"mime_type": item["mime_type"], "data": item["data"]}})
        elif _is_document(item):
            parts.append((documents or {}).get(item.get("key"))
                         or {"inline_data": {"mime_type": item["mime_type"], "data": _document_bytes(item)}})
        else:
            raise ValueError("Parte de mensagem não suportada: use texto, imagem PNG ou JPEG ou documento PDF.")
    return parts


class UploadedFiles:
    """O que foi enviado ao serviço de arquivos do Google (lote 30): chave do conteúdo, nome, endereço e validade.

    O registro fica num arquivo local, sem o conteúdo dos documentos. Ele deixa um envio ser reaproveitado
    enquanto vale e diz o que apagar do serviço."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.Lock()

    def entries(self) -> dict[str, dict]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))["arquivos"]
        except (OSError, ValueError, KeyError, TypeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self, entries: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"arquivos": entries}, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

    @staticmethod
    def expires(entry) -> datetime | None:
        """Até quando o serviço guarda este envio; None se o registro não diz."""
        try:
            moment = datetime.fromisoformat(entry["expira"])
        except (KeyError, TypeError, ValueError):
            return None
        return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)

    def get(self, key: str) -> dict | None:
        """O envio ainda válido deste conteúdo, se houver."""
        entry = self.entries().get(key)
        moment = self.expires(entry)
        return entry if moment is not None and moment > datetime.now(timezone.utc) + FILE_MARGIN else None

    def put(self, key: str, entry: dict) -> None:
        """Registra um envio; os que o serviço já apagou, pelo prazo, saem do registro."""
        now = datetime.now(timezone.utc)
        with self._lock:
            kept = {name: old for name, old in self.entries().items() if (self.expires(old) or now) >= now}
            self._write(kept | {key: entry})

    def drop(self, keys) -> None:
        with self._lock:
            remove = set(keys)
            self._write({key: entry for key, entry in self.entries().items() if key not in remove})


class GeminiProvider:
    name = "google"

    def __init__(self, api_key: str | None = None, *, client=None, files: str | Path | None = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self._client = client
        self._lock = threading.Lock()
        # Registro dos envios ao serviço de arquivos; sem ele, um pedido acima do limite direto é recusado.
        self.files = UploadedFiles(files) if files is not None else None

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

    def _documents(self, request: LLMRequest) -> dict[str, dict[str, Any]]:
        """Como segue cada documento do pedido, pela chave: pelo serviço de arquivos ou dentro dele.

        Vale o envio anterior do mesmo conteúdo, enquanto durar: o documento nem é lido de novo. Os outros
        sobem pelo serviço de arquivos. Sem registro de envios, seguem dentro do pedido, se couberem."""
        items: dict[str, dict] = {}
        for message in request.messages:
            content = message.get("content") if isinstance(message, dict) else None
            for item in content if isinstance(content, list) else ():
                if _is_document(item) and isinstance(item.get("key"), str):
                    items.setdefault(item["key"], item)
        placed, waiting = {}, []
        for key, item in items.items():
            entry = self.files.get(key) if self.files is not None else None
            if entry is not None:
                placed[key] = {"file_data": {"file_uri": entry["endereco"], "mime_type": item["mime_type"]}}
            else:
                waiting.append((key, item["mime_type"], _document_bytes(item)))
        if self.files is not None:
            uploads = waiting
        elif sum(len(data) for _, _, data in waiting) > INLINE_BYTES:
            raise ValueError("Os documentos passam do tamanho de um pedido direto, e o serviço de arquivos "
                             "não está configurado.")
        else:
            uploads = []
            placed |= {key: {"inline_data": {"mime_type": mime_type, "data": data}} for key, mime_type, data in waiting}

        def send(item: tuple[str, str, bytes]) -> dict:
            key, mime_type, data = item
            entry = self._upload(data, mime_type)
            self.files.put(key, entry)  # registrado na hora: o que subiu pode ser apagado mesmo se outro falhar
            return {"file_data": {"file_uri": entry["endereco"], "mime_type": mime_type}}

        if uploads:
            self._get_client()  # um cliente só, criado antes das threads
            try:
                with ThreadPoolExecutor(max_workers=UPLOAD_WORKERS) as pool:
                    sent = list(pool.map(send, uploads))
            except ProviderNotConfiguredError:
                raise
            except Exception as exc:
                raise classify_provider_exception(exc, self.name) from exc
            placed |= {item[0]: part for item, part in zip(uploads, sent)}
        return placed

    def _upload(self, data: bytes, mime_type: str) -> dict:
        """Envia um documento ao serviço de arquivos e espera ele ficar pronto; devolve a linha do registro."""
        files = self._get_client().files
        sent = files.upload(file=io.BytesIO(data), config={"mime_type": mime_type})
        deadline = time.monotonic() + FILE_WAIT
        while _state(sent) == "PROCESSING":
            if time.monotonic() > deadline:
                raise TimeoutError("timeout: o serviço de arquivos não terminou de receber o documento")
            time.sleep(1.0)
            sent = files.get(name=sent.name)
        if _state(sent) == "FAILED":
            raise RuntimeError("o serviço de arquivos recusou o documento")
        now = datetime.now(timezone.utc)
        expires = getattr(sent, "expiration_time", None)
        if not isinstance(expires, datetime):
            expires = now + FILE_LIFE
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return {"nome": sent.name, "endereco": sent.uri, "bytes": len(data),
                "enviado": now.isoformat(timespec="seconds"), "expira": expires.isoformat(timespec="seconds")}

    def uploaded(self) -> list[dict]:
        """O que o registro local diz estar no serviço de arquivos, com a chave de cada envio."""
        return [] if self.files is None else [{"chave": key} | entry for key, entry in self.files.entries().items()]

    def forget_uploads(self) -> dict:
        """Apaga do serviço de arquivos o que este computador enviou e limpa o registro.

        Um arquivo que o serviço já não tem (o prazo passou) sai do registro do mesmo jeito."""
        counts = {"apagados": 0, "falhas": 0}
        if self.files is None:
            return counts
        done = []
        for key, entry in self.files.entries().items():
            moment = self.files.expires(entry)
            if moment is None or moment > datetime.now(timezone.utc):
                try:
                    self._get_client().files.delete(name=entry["nome"])
                except ProviderNotConfiguredError:
                    raise
                except Exception as exc:
                    if not classify_provider_exception(exc, self.name).unavailable:
                        counts["falhas"] += 1
                        continue
            counts["apagados"] += 1
            done.append(key)
        self.files.drop(done)
        return counts

    @staticmethod
    def _kwargs(request: LLMRequest, model_id: str, documents: dict | None = None) -> dict[str, Any]:
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
                    "parts": _parts(content, role, request.multimodal, documents),
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
        kwargs = self._kwargs(request, model_id, self._documents(request))
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
        kwargs = self._kwargs(request, model_id, self._documents(request))
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
