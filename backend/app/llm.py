from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.config import Settings


def build_chat_model(settings: Settings) -> BaseChatModel | None:
    """Build the configured provider while keeping callers provider-independent."""
    if not settings.llm_provider or not settings.llm_model or not settings.llm_api_key:
        return None

    api_key = SecretStr(settings.llm_api_key)
    if settings.llm_provider == "openai":
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=api_key,
            base_url=settings.llm_base_url,
            temperature=0,
            max_retries=2,
            timeout=10,
        )

    return ChatAnthropic(
        model_name=settings.llm_model,
        api_key=api_key,
        base_url=settings.llm_base_url,
        temperature=0,
        max_retries=2,
        timeout=10,
    )
