"""Regressões de saída estruturada com clientes locais, sem chamadas pagas."""

from types import SimpleNamespace

import pytest

from aliado.llm.contracts import LLMRequest
from aliado.llm.providers.gemini import GeminiProvider
from aliado.llm.providers.openai import OpenAIProvider


def provider_with_response(provider_class, content):
    response = SimpleNamespace(output_text=content, text=content)
    client = SimpleNamespace(
        responses=SimpleNamespace(create=lambda **kwargs: response),
        models=SimpleNamespace(generate_content=lambda **kwargs: response),
    )
    return provider_class(client=client)


@pytest.mark.parametrize("provider_class", [OpenAIProvider, GeminiProvider])
@pytest.mark.parametrize("content", ["", "  ", "null", "[]", '"texto"', "0", "true", "{inválido}"])
def test_structured_output_requires_json_object(provider_class, content):
    provider = provider_with_response(provider_class, content)
    request = LLMRequest(
        task_type="evidence_audit",
        messages=[{"role": "user", "content": "audite"}],
        structured_output={"type": "object"},
    )
    with pytest.raises(ValueError):
        provider.generate(request, model_id="modelo-simulado")


@pytest.mark.parametrize("provider_class", [OpenAIProvider, GeminiProvider])
@pytest.mark.parametrize("content, expected", [("{}", {}), ('{"status":"ok"}', {"status": "ok"})])
def test_structured_output_accepts_objects_including_empty(provider_class, content, expected):
    provider = provider_with_response(provider_class, content)
    request = LLMRequest(
        task_type="evidence_audit",
        messages=[{"role": "user", "content": "audite"}],
        structured_output={"type": "object"},
    )
    result = provider.generate(request, model_id="modelo-simulado")
    assert result.content == content
    assert result.structured_data == expected


@pytest.mark.parametrize("provider_class", [OpenAIProvider, GeminiProvider])
@pytest.mark.parametrize("content", ["", "null", "resposta comum"])
def test_plain_text_is_not_interpreted_as_json(provider_class, content):
    provider = provider_with_response(provider_class, content)
    result = provider.generate(
        LLMRequest(task_type="simple_chat", messages=[{"role": "user", "content": "oi"}]),
        model_id="modelo-simulado",
    )
    assert result.content == content
    assert result.structured_data is None
