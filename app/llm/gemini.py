"""Gemini provider (default), through the official `google-genai` SDK."""

import contextlib
import io
from typing import Any

import httpx
from google import genai
from google.genai import errors, types

from app.llm.base import (
    FILE_PROMPT,
    SYSTEM_PROMPT,
    LLMExtractionError,
    LLMTransientError,
    build_user_prompt,
    parse_response,
)
from app.schemas import DocumentSchema

_RETRYABLE_STATUS = {408, 429}  # timeout and rate limit; every 5xx is retryable too
# A request carries at most 20 MB and inline bytes grow by a third in base64: bigger files (long
# scanned PDFs) go through the Files API and are deleted from it right after the call.
INLINE_LIMIT_BYTES = 14 * 1024 * 1024


class GeminiExtractor:
    provider = "gemini"

    def __init__(self, *, api_key: str, model: str, client: Any = None) -> None:
        self.model = model
        self._client = client or genai.Client(api_key=api_key)  # tests pass a fake client

    def extract(self, text: str) -> DocumentSchema:
        return self._generate(build_user_prompt(text))

    def extract_file(self, data: bytes, mime_type: str) -> DocumentSchema:
        if len(data) <= INLINE_LIMIT_BYTES:
            return self._generate([types.Part.from_bytes(data=data, mime_type=mime_type), FILE_PROMPT])
        try:
            uploaded = self._client.files.upload(
                file=io.BytesIO(data), config=types.UploadFileConfig(mime_type=mime_type)
            )
        except errors.APIError as exc:
            raise LLMTransientError(f"Gemini file upload failed: {exc.code} {exc.status}") from exc
        except httpx.TransportError as exc:
            raise LLMTransientError(f"cannot reach Gemini: {type(exc).__name__}") from exc
        try:
            return self._generate([uploaded, FILE_PROMPT])
        finally:
            with contextlib.suppress(Exception):  # if this fails, Google deletes uploads after 48 h
                self._client.files.delete(name=str(uploaded.name))

    def _generate(self, contents: Any) -> DocumentSchema:
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
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
