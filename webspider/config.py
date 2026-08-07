"""webspider.config — LLM model factory multi-proveedor.

Reads configuration from environment variables:
    LLM_BACKEND  — "openai" (default), "hf", "litellm"
    LLM_MODEL    — model ID
    LLM_API_KEY  — API key
    LLM_API_BASE — API base URL (for OpenAI-compatible endpoints)
    LLM_NUM_CTX  — context window size (default 8192)

Usage:
    from webspider.config import get_model

    model = get_model()
    agent = CodeAgent(tools=[], model=model)
"""

from __future__ import annotations

import os


def get_model() -> object:
    """Create an LLM model instance based on LLM_BACKEND env var.

    Returns:
        A smolagents model instance (OpenAIModel, InferenceClientModel, or LiteLLMModel).

    Raises:
        ValueError: If LLM_BACKEND is unknown.
        ImportError: If required dependencies for the selected backend are missing.
    """
    backend = os.environ.get("LLM_BACKEND", "openai").lower()
    model_id = os.environ.get("LLM_MODEL", "gpt-4o")
    api_key = os.environ.get("LLM_API_KEY", "")
    api_base = os.environ.get("LLM_API_BASE", "")

    if backend == "openai":
        return _get_openai_model(model_id, api_key, api_base)
    elif backend == "hf":
        return _get_hf_model(model_id, api_key)
    elif backend in ("litellm", "lite_llm", "litellm_model"):
        return _get_litellm_model(model_id, api_key, api_base)
    else:
        raise ValueError(
            f"Unknown LLM_BACKEND: {backend!r}. "
            f"Supported: openai, hf, litellm. "
            f"Set via LLM_BACKEND environment variable."
        )


def _get_openai_model(model_id: str, api_key: str, api_base: str) -> object:
    """Create an OpenAIModel for OpenAI-compatible endpoints (incl. Ollama)."""
    try:
        from smolagents import OpenAIModel
    except ImportError as e:
        raise ImportError(
            "smolagents OpenAIModel requires openai>=1.0. Install with: uv pip install -e '.[openai]'"
        ) from e

    kwargs: dict = {"model_id": model_id}
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base
    return OpenAIModel(**kwargs)


def _get_hf_model(model_id: str, token: str) -> object:
    """Create an InferenceClientModel for Hugging Face."""
    try:
        from smolagents import InferenceClientModel
    except ImportError as e:
        raise ImportError(
            "smolagents InferenceClientModel requires huggingface-hub>=0.20. Install with: uv pip install -e '.[hf]'"
        ) from e

    kwargs: dict = {}
    if model_id:
        kwargs["model_id"] = model_id
    if token:
        kwargs["token"] = token
    elif "HF_TOKEN" in os.environ:
        kwargs["token"] = os.environ["HF_TOKEN"]
    return InferenceClientModel(**kwargs)


def _get_litellm_model(model_id: str, api_key: str, api_base: str) -> object:
    """Create a LiteLLMModel for maximum provider compatibility (Ollama, Anthropic, etc.)."""
    try:
        from smolagents import LiteLLMModel
    except ImportError as e:
        raise ImportError(
            "smolagents LiteLLMModel requires litellm>=1.0. Install with: uv pip install -e '.[litellm]'"
        ) from e

    num_ctx = int(os.environ.get("LLM_NUM_CTX", "8192"))
    kwargs: dict = {
        "model_id": model_id,
        "num_ctx": num_ctx,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base
    return LiteLLMModel(**kwargs)
