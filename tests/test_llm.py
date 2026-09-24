import json
from types import SimpleNamespace
from typing import Any

import httpx
import httpx2  # the OpenAI SDK v3 builds its errors on httpx2
import openai
import pytest
from google.genai import errors as genai_errors
from pydantic import SecretStr

from app.config import Settings
from app.llm import (
    SYSTEM_PROMPT,
    LLMExtractionError,
    LLMTransientError,
    build_extractor,
    parse_response,
)
from app.llm.gemini import GeminiExtractor
from app.llm.openai import OpenAIExtractor
from app.schemas import DocumentSchema, DocumentType

VALID_INVOICE = {
    "document_type": "invoice",
    "summary": "Invoice from Acme SpA.",
    "commercial": {"issuer": {"name": "Acme SpA"}, "currency": "CLP", "total_amount": 119000},
}


# --------------------------------------------------------------------------- parse_response


def test_parse_response_returns_a_validated_schema() -> None:
    doc = parse_response(json.dumps(VALID_INVOICE))

    assert isinstance(doc, DocumentSchema)
    assert doc.document_type is DocumentType.INVOICE


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_parse_response_rejects_empty_output(raw: str | None) -> None:
    with pytest.raises(LLMExtractionError, match="empty"):
        parse_response(raw)


def test_parse_response_rejects_invalid_json() -> None:
    with pytest.raises(LLMExtractionError, match="DocumentSchema"):
        parse_response('{"document_type": "invoice", "summary": ')  # truncated output


def test_parse_response_rejects_json_that_breaks_the_schema() -> None:
    # Valid JSON, but "invoice" without its "commercial" section.
    raw = json.dumps({"document_type": "invoice", "summary": "An invoice."})

    with pytest.raises(LLMExtractionError, match="DocumentSchema") as exc_info:
        parse_response(raw)

    assert not isinstance(exc_info.value, LLMTransientError)  # retrying would not help


def test_parse_response_error_does_not_leak_document_content() -> None:
    raw = json.dumps({"document_type": "invoice", "summary": "SECRET-CUSTOMER-DATA", "commercial": {"issuer": {}}})

    with pytest.raises(LLMExtractionError) as exc_info:
        parse_response(raw)

    assert "SECRET-CUSTOMER-DATA" not in str(exc_info.value)
    assert "commercial.issuer.name" in str(exc_info.value)


# --------------------------------------------------------------------------- Gemini


class FakeGeminiModels:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return SimpleNamespace(text=self.result)


def gemini_with(result: Any) -> tuple[GeminiExtractor, FakeGeminiModels]:
    models = FakeGeminiModels(result)
    extractor = GeminiExtractor(api_key="test", model="gemini-test", client=SimpleNamespace(models=models))
    return extractor, models


def test_gemini_sends_the_schema_as_structured_output() -> None:
    extractor, models = gemini_with(json.dumps(VALID_INVOICE))

    doc = extractor.extract("--- Page 1 ---\nFactura 1234")

    assert doc.commercial is not None
    assert doc.commercial.total_amount == 119000
    call = models.calls[0]
    assert call["model"] == "gemini-test"
    assert "Factura 1234" in call["contents"]
    config = call["config"]
    assert config.response_schema is DocumentSchema
    assert config.response_mime_type == "application/json"
    assert config.temperature == 0
    assert config.system_instruction == SYSTEM_PROMPT


def test_gemini_invalid_output_is_rejected() -> None:
    extractor, _ = gemini_with('{"document_type": "invoice", "summary": "no section"}')

    with pytest.raises(LLMExtractionError):
        extractor.extract("text")


@pytest.mark.parametrize(
    "error",
    [
        genai_errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}}),
        genai_errors.ServerError(503, {"error": {"code": 503, "status": "UNAVAILABLE"}}),
        httpx.ConnectError("network down"),
        httpx.ReadTimeout("slow"),
    ],
)
def test_gemini_rate_limits_outages_and_network_errors_are_transient(error: Exception) -> None:
    extractor, _ = gemini_with(error)

    with pytest.raises(LLMTransientError):
        extractor.extract("text")


@pytest.mark.parametrize("code", [400, 401, 403, 404])
def test_gemini_client_errors_are_permanent(code: int) -> None:
    extractor, _ = gemini_with(genai_errors.ClientError(code, {"error": {"code": code, "status": "BAD"}}))

    with pytest.raises(LLMExtractionError) as exc_info:
        extractor.extract("text")

    assert not isinstance(exc_info.value, LLMTransientError)


# --------------------------------------------------------------------------- OpenAI


class FakeOpenAICompletions:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        content, refusal = self.result
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, refusal=refusal))])


def openai_with(result: Any) -> tuple[OpenAIExtractor, FakeOpenAICompletions]:
    completions = FakeOpenAICompletions(result)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return OpenAIExtractor(api_key="test", model="gpt-test", client=client), completions


def test_openai_sends_the_schema_as_structured_output() -> None:
    extractor, completions = openai_with((json.dumps(VALID_INVOICE), None))

    doc = extractor.extract("Factura 1234")

    assert doc.document_type is DocumentType.INVOICE
    call = completions.calls[0]
    assert call["model"] == "gpt-test"
    assert call["response_format"] is DocumentSchema
    assert call["temperature"] == 0
    assert call["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert "Factura 1234" in call["messages"][1]["content"]


def test_openai_refusal_is_rejected() -> None:
    extractor, _ = openai_with((None, "I can't help with that."))

    with pytest.raises(LLMExtractionError, match="refused"):
        extractor.extract("text")


def _openai_response(status: int) -> httpx2.Response:
    return httpx2.Response(status, request=httpx2.Request("POST", "https://api.openai.com/v1/chat/completions"))


@pytest.mark.parametrize(
    "error",
    [
        openai.RateLimitError("rate limited", response=_openai_response(429), body=None),
        openai.InternalServerError("down", response=_openai_response(503), body=None),
        openai.APIConnectionError(request=httpx2.Request("POST", "https://api.openai.com")),
    ],
)
def test_openai_rate_limits_and_outages_are_transient(error: Exception) -> None:
    extractor, _ = openai_with(error)

    with pytest.raises(LLMTransientError):
        extractor.extract("text")


def test_openai_bad_request_is_permanent() -> None:
    error = openai.BadRequestError("bad", response=_openai_response(400), body=None)
    extractor, _ = openai_with(error)

    with pytest.raises(LLMExtractionError) as exc_info:
        extractor.extract("text")

    assert not isinstance(exc_info.value, LLMTransientError)


# --------------------------------------------------------------------------- factory


def settings_for(provider: str, **keys: str) -> Settings:
    values: dict[str, Any] = {
        "llm_provider": provider,
        "llm_model": "some-model",
        "database_url": SecretStr("postgresql+psycopg://u:p@h:5432/d"),
        "secret_key": SecretStr("k" * 32),
        **{name: SecretStr(value) for name, value in keys.items()},
    }
    return Settings(_env_file=None, **values)  # type: ignore[call-arg]


def test_factory_builds_gemini_from_settings() -> None:
    extractor = build_extractor(settings_for("gemini", gemini_api_key="g-key"))

    assert isinstance(extractor, GeminiExtractor)
    assert (extractor.provider, extractor.model) == ("gemini", "some-model")


def test_factory_builds_openai_from_settings() -> None:
    extractor = build_extractor(settings_for("openai", openai_api_key="o-key"))

    assert isinstance(extractor, OpenAIExtractor)
    assert (extractor.provider, extractor.model) == ("openai", "some-model")
