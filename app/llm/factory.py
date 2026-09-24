"""Pick the LLM provider from settings: LLM_PROVIDER and LLM_MODEL in .env."""

from app.config import Settings
from app.llm.base import DocumentExtractor


def build_extractor(settings: Settings) -> DocumentExtractor:
    # config.py already guarantees the selected provider has its API key.
    if settings.llm_provider == "openai":
        from app.llm.openai import OpenAIExtractor  # imported lazily: the SDK is an optional extra

        assert settings.openai_api_key is not None
        return OpenAIExtractor(api_key=settings.openai_api_key.get_secret_value(), model=settings.llm_model)

    from app.llm.gemini import GeminiExtractor

    assert settings.gemini_api_key is not None
    return GeminiExtractor(api_key=settings.gemini_api_key.get_secret_value(), model=settings.llm_model)
