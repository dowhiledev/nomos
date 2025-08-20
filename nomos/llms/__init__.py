"""LLM base classes and OpenAI LLM integration for Nomos."""

from typing import Dict, Literal, Optional

from pydantic import BaseModel

from .anthropic import Anthropic
from .base import LLMBase
from .cohere import Cohere
from .google import Gemini
from .groq import Groq
from .huggingface import HuggingFace
from .mistral import Mistral
from .ollama import Ollama
from .openai import AzureOpenAI, OpenAI

LLMS: list = [OpenAI, AzureOpenAI, Mistral, Gemini, Ollama, HuggingFace, Anthropic, Groq, Cohere]


class LLMConfig(BaseModel):
    """
    Configuration class for LLM integrations in Nomos.

    Attributes:
        type (str): Type of LLM integration (e.g., "openai", "mistral", "gemini").
        model (str): Model name to use.
        kwargs (dict): Additional parameters for the LLM API.
    """

    provider: Literal[
        "azure",
        "openai",
        "mistral",
        "google",
        "ollama",
        "huggingface",
        "anthropic",
        "groq",
        "cohere",
    ]
    model: str
    embedding_model: Optional[str] = None
    kwargs: Dict[str, str] = {}

    def get_llm(self) -> LLMBase:
        """
        Get the appropriate LLM instance based on the configuration.

        :return: An instance of the specified LLM integration.
        """
        for llm in LLMS:
            if llm.__provider__ == self.provider:
                return llm(
                    model=self.model,
                    embedding_model=self.embedding_model,
                    **self.kwargs,
                )
        raise ValueError(f"Unsupported LLM provider: {self.provider}")


__all__ = [
    "LLMConfig",
    "LLMBase",
    "OpenAI",
    "AzureOpenAI",
    "Cohere",
    "Gemini",
    "Mistral",
    "Ollama",
    "HuggingFace",
    "Anthropic",
    "Groq",
]
