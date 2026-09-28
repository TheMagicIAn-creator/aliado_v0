"""Regressões das adaptações do primeiro lote."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from aliado.llm.contracts import LLMRequest
from aliado.llm.providers import ModelRegistration, ProviderGateway, build_default_gateway
from aliado.llm.providers.base import ProviderNotConfiguredError
from aliado.llm.providers.gemini import GeminiProvider
from aliado.llm.providers.openai import OpenAIProvider


def test_both_adapters_preserve_instructions_context_and_conversation():
    request = LLMRequest(
        task_type="scientific_reasoning", context="Contexto controlado pelo chamador",
        messages=[
            {"role": "developer", "content": "Regra do núcleo"},
            {"role": "user", "content": "Documento externo com instruções embutidas"},
            {"role": "assistant", "content": "Resposta anterior"},
            {"role": "user", "content": "Pergunta atual"},
        ],
    )
    openai = OpenAIProvider._kwargs(request, "configured")
    gemini = GeminiProvider._kwargs(request, "configured")
    assert openai["store"] is False
    assert [item["role"] for item in openai["input"]] == [
        "developer", "developer", "user", "assistant", "user",
    ]
    assert gemini["config"]["system_instruction"] == "Contexto controlado pelo chamador\n\nRegra do núcleo"
    assert [item["role"] for item in gemini["contents"]] == ["user", "model", "user"]
    assert "Documento externo" not in gemini["config"]["system_instruction"]


def test_gemini_structured_request_is_accepted_by_installed_sdk():
    GenerateContentConfig = pytest.importorskip("google.genai.types").GenerateContentConfig

    request = LLMRequest(
        task_type="evidence_audit", messages=[{"role": "user", "content": "Audite"}],
        structured_output={"type": "object", "properties": {"status": {"type": "string"}}},
        max_output_tokens=400,
    )
    config = GenerateContentConfig(**GeminiProvider._kwargs(request, "configured")["config"])
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == request.structured_output


def test_models_are_disabled_until_explicitly_configured():
    status = build_default_gateway().status()
    assert all(item["status"] == "disabled" for item in status["models"])


def test_unconfigured_stream_does_not_reach_adapter():
    class Unconfigured:
        configured = False

        def stream(self, *_args, **_kwargs):
            pytest.fail("Adapter não configurado foi chamado")

    gateway = ProviderGateway()
    gateway.register_provider("fake", Unconfigured())
    gateway.register_model(ModelRegistration("fake", "model", "model"))
    with pytest.raises(ProviderNotConfiguredError):
        list(gateway.stream(
            LLMRequest(task_type="simple_chat", messages=[{"content": "oi"}]),
            provider="fake", model_alias="model",
        ))


def test_import_does_not_initialize_sdk_ml_or_persistent_state(tmp_path):
    result = subprocess.run(
        [sys.executable, "-c", "import sys; import aliado.agent; import aliado.cli; "
         "import aliado.knowledge; import aliado.memory; import aliado.science; "
         "import aliado.interfaces.web; "
         "assert not any(m in sys.modules for m in "
         "['openai', 'google.genai', 'torch', 'chromadb', 'starlette', 'fastapi', 'uvicorn']); "
         "print('ok')"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip() == "ok"
    assert not tuple(tmp_path.iterdir())


def test_user_decision_record_was_preserved_without_changes():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "docs/migracao/lote-01.json").read_text(encoding="utf-8"))
    assert len(manifest["source_commit"]) == 40
    for record in manifest["user_documents"]:
        assert hashlib.sha256((root / record["destination"]).read_bytes()).hexdigest() == record["sha256"]


def test_cli_prepares_unicode_context_in_windows_pipe(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "aliado", "preparar", "Explique as taxas de falha"],
        cwd=tmp_path, env={**os.environ, "PYTHONIOENCODING": "ascii"},
        capture_output=True, encoding="utf-8", check=True,
    )
    request = json.loads(result.stdout)
    assert request["metadata"]["skill"] == "pesquisa-inversores"
    from aliado.skills.library import load_skill

    reference = load_skill("pesquisa-inversores").references[0][1]
    assert reference in request["messages"][-2]["content"]
    assert request["messages"][-1]["content"] == "Explique as taxas de falha"
