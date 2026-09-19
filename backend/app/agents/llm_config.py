from typing import Optional
from crewai import LLM
from app.core.config import settings
import os

SUPPORTED_PROVIDERS = (
    "openai", "anthropic", "claude", "azure", "azure_openai",
    "google", "gemini", "bedrock", "aws", "openrouter",
    "deepseek", "ollama", "ollama_chat", "hosted_vllm",
    "cerebras", "dashscope", "snowflake"
)

def normalize_model_name(model: str) -> str:
    """
    Ensures model name has a provider prefix supported natively by CrewAI.
    e.g., 'qwen/qwen3.8-27b' -> 'openrouter/qwen/qwen3.8-27b'
    """
    if "/" in model:
        prefix = model.split("/")[0].lower()
        if prefix not in SUPPORTED_PROVIDERS:
            # Map un-prefixed/third-party models to openrouter provider
            return f"openrouter/{model}"
        return model
    return model


def create_llm_instance(
    model: str,
    api_key: Optional[str] = None,
    timeout: Optional[int] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> LLM:
    """
    Creates and configures a CrewAI LLM instance with specified parameters.
    """
    normalized_model = normalize_model_name(model)
    key = (
        api_key
        or os.environ.get("CREWAI_MODEL_API_KEY")
        or settings.CREWAI_MODEL_API_KEY
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("mock_api_key_for_testing")
        or "mock_api_key_for_testing"
    )
    
    return LLM(
        model=normalized_model,
        api_key=key,
        timeout=timeout or settings.LLM_TIMEOUT_SECONDS,
        temperature=temperature if temperature is not None else settings.LLM_TEMPERATURE,
        max_tokens=max_tokens or settings.LLM_MAX_TOKENS
    )

def get_primary_llm() -> LLM:
    """Returns the configured Primary LLM (default: openai/gpt-oss-120b)."""
    return create_llm_instance(
        model=settings.PRIMARY_LLM_MODEL,
        api_key=settings.PRIMARY_LLM_API_KEY
    )

def get_fallback_llm() -> LLM:
    """Returns the configured Fallback LLM (default: qwen/qwen3.8-27b via openrouter/qwen/qwen3.8-27b)."""
    return create_llm_instance(
        model=settings.FALLBACK_LLM_MODEL,
        api_key=settings.FALLBACK_LLM_API_KEY
    )
