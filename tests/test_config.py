"""Tests for webspider.config — LLM model factory."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest


def test_get_model_default_backend_openai() -> None:
    """get_model with default (openai) backend creates an OpenAIModel (may fail without API key)."""
    with patch.dict(
        os.environ,
        {
            "LLM_BACKEND": "openai",
            "LLM_MODEL": "gpt-4o",
            "OPENAI_API_KEY": "sk-test",
        },
    ):
        from webspider.config import get_model

        try:
            model = get_model()
            assert model is not None
        except ImportError as e:
            # openai not installed — still valid test outcome
            assert "openai" in str(e).lower() or "smolagents" in str(e).lower()


def test_get_model_hf_backend() -> None:
    """get_model with HF backend attempts to create InferenceClientModel."""
    with patch.dict(os.environ, {"LLM_BACKEND": "hf", "LLM_MODEL": "meta-llama/Llama-3.3-70B-Instruct"}):
        try:
            from webspider.config import get_model

            model = get_model()
            assert model is not None
        except ImportError:
            pytest.skip("huggingface_hub not installed")


def test_get_model_litellm_backend() -> None:
    """get_model with litellm backend attempts to create LiteLLMModel."""
    with patch.dict(
        os.environ,
        {"LLM_BACKEND": "litellm", "LLM_MODEL": "ollama_chat/llama3.2", "LLM_API_BASE": "http://localhost:11434"},
    ):
        try:
            from webspider.config import get_model

            model = get_model()
            assert model is not None
        except ImportError:
            pytest.skip("litellm not installed")


def test_get_model_unknown_backend_raises() -> None:
    """get_model with unknown backend raises ValueError."""
    with patch.dict(os.environ, {"LLM_BACKEND": "unknown_backend"}):
        from webspider.config import get_model

        with pytest.raises(ValueError, match="unknown_backend"):
            get_model()


def test_get_model_openai_custom_api_base() -> None:
    """OpenAI backend reads LLM_API_BASE from env."""
    with patch.dict(
        os.environ,
        {
            "LLM_BACKEND": "openai",
            "LLM_MODEL": "llama3.2",
            "LLM_API_BASE": "http://localhost:11434/v1",
            "LLM_API_KEY": "ollama",
        },
    ):
        try:
            from webspider.config import get_model

            model = get_model()
            assert model is not None
        except ImportError:
            pytest.skip("openai not installed")


def test_get_model_litellm_aliases() -> None:
    """lite_llm and litellm_model aliases work."""
    for alias in ("lite_llm", "litellm_model"):
        with patch.dict(os.environ, {"LLM_BACKEND": alias, "LLM_MODEL": "gpt-4o"}):
            try:
                from webspider.config import get_model

                model = get_model()
                assert model is not None
            except ImportError:
                pytest.skip(f"litellm not installed for alias {alias}")
