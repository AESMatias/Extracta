"""Gemini provider (default), through the official `google-genai` SDK."""

from typing import Any

import httpx
from google import genai
from google.genai import errors, types

from app.llm.base import SYSTEM_PROMPT, LLMExtractionError, LLMTransientError, build_user_prompt, parse_response
from app.schemas import DocumentSchema

_RETRYABLE_STATUS = {408, 429}  # timeout and rate limit; every 5xx is retryable too


class GeminiExtractor:
    provider = "gemini"

    def __init__(self, *, api_key: str, model: str, client: Any = None) -> None:
        self.model = model
        self._client = client or genai.Client(api_key=api_key)  # tests pass a fake client

    def extract(self, text: str) -> DocumentSchema:
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=build_user_prompt(text),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=DocumentSchema,  # structured output: Gemini must follow this shape
                    temperature=0,  # extraction, not creativity: same input, same answer
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),  # no tools used
                ),
            )
        except errors.APIError as exc:
            retryable = exc.code in _RETRYABLE_STATUS or exc.code >= 500
            error_class = LLMTransientError if retryable else LLMExtractionError
            raise error_class(f"Gemini API error {exc.code} {exc.status}") from exc
        except httpx.TransportError as exc:  # connection refused, DNS, timeouts
            raise LLMTransientError(f"cannot reach Gemini: {type(exc).__name__}") from exc

        # Not response.parsed: it silently returns None on a mismatch. We validate ourselves.
        return parse_response(response.text)
