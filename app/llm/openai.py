"""OpenAI provider (optional).

The `openai` SDK is an optional Poetry extra, so it is imported only when this
provider is actually used:  docker compose build --build-arg POETRY_EXTRAS=openai
"""

import base64
from typing import Any

from app.llm.base import (
    FILE_PROMPT,
    SYSTEM_PROMPT,
    LLMExtractionError,
    LLMTransientError,
    build_user_prompt,
    parse_response,
)
from app.schemas import DocumentSchema


def _import_openai() -> Any:
    try:
        import openai
    except ImportError as exc:
        raise RuntimeError(
            "LLM_PROVIDER=openai needs the optional SDK: docker compose build --build-arg POETRY_EXTRAS=openai"
        ) from exc
    return openai


class OpenAIExtractor:
    provider = "openai"

    def __init__(self, *, api_key: str, model: str, client: Any = None) -> None:
        self.model = model
        self._client = client or _import_openai().OpenAI(api_key=api_key)  # tests pass a fake client

    def extract(self, text: str) -> DocumentSchema:
        return self._parse(build_user_prompt(text))

    def extract_file(self, data: bytes, mime_type: str) -> DocumentSchema:
        url = f"data:{mime_type};base64,{base64.b64encode(data).decode()}"
        attachment: dict[str, Any] = (
            {"type": "file", "file": {"filename": "document.pdf", "file_data": url}}
            if mime_type == "application/pdf"
            else {"type": "image_url", "image_url": {"url": url}}
        )
        return self._parse([attachment, {"type": "text", "text": FILE_PROMPT}])

    def _parse(self, content: Any) -> DocumentSchema:
        openai = _import_openai()
        try:
            completion = self._client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                response_format=DocumentSchema,  # structured output in OpenAI's strict mode
                temperature=0,
            )
        except (openai.RateLimitError, openai.InternalServerError, openai.APIConnectionError) as exc:
            raise LLMTransientError(f"OpenAI temporarily unavailable: {type(exc).__name__}") from exc
        except openai.OpenAIError as exc:
            raise LLMExtractionError(f"OpenAI API error: {type(exc).__name__}") from exc

        message = completion.choices[0].message
        if message.refusal:
            raise LLMExtractionError("the model refused to process this document")
        # Same single validation path as every provider.
        return parse_response(message.content)
