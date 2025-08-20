"""OpenAI LLM integration for Nomos."""

import os
from typing import List, Optional

from pydantic import BaseModel

from ..models.agent import Message
from .base import LLMBase


class OpenAI(LLMBase):
    """OpenAI Chat LLM integration for Nomos."""

    __provider__: str = "openai"

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        embedding_model: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Initialize the OpenAIChatLLM.

        :param model: Model name to use (default: gpt-4o-mini).
        :param embedding_model: Model name for embeddings (default: text-embedding-3-small).
        :param kwargs: Additional parameters for OpenAI API.
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI package is not installed. Please install it using 'pip install nomos[openai]."
            )

        self.model = model
        self.embedding_model = embedding_model or "text-embedding-3-small"
        self.client = OpenAI(**kwargs)

    def get_output(
        self,
        messages: List[Message],
        response_format: BaseModel,
        **kwargs: dict,
    ) -> BaseModel:
        """
        Get a structured response from the OpenAI LLM.

        :param messages: List of Message objects.
        :param response_format: Pydantic model for the expected response.
        :param kwargs: Additional parameters for OpenAI API.
        :return: Parsed response as a BaseModel.
        """
        _messages = [msg.model_dump() for msg in messages]
        comp = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=_messages,
            response_format=response_format,
            **kwargs,
        )
        return comp.choices[0].message.parsed

    def generate(
        self,
        messages: List[Message],
        **kwargs: dict,
    ) -> str:
        """
        Generate a response from the OpenAI LLM based on the provided messages.

        :param messages: List of Message objects.
        :param kwargs: Additional parameters for OpenAI API.
        :return: Generated response as a string.
        """
        from openai.types.chat import ChatCompletion

        _messages = [msg.model_dump() for msg in messages]
        comp: ChatCompletion = self.client.chat.completions.create(
            messages=_messages,
            model=self.model,
            **kwargs,
        )
        return comp.choices[0].message.content if comp.choices else ""  # type: ignore

    def token_counter(self, text: str) -> int:
        """Count tokens using tiktoken for the current model."""
        import tiktoken

        enc = tiktoken.encoding_for_model(self.model)
        return len(enc.encode(text))

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text using the OpenAI embeddings API."""
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text,
            encoding_format="float",
        )
        emb = response.data[0].embedding
        return emb

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts using the OpenAI embeddings API."""
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts,
            encoding_format="float",
        )
        embs = [item.embedding for item in response.data]
        return embs


class AzureOpenAI(OpenAI):
    """Azure OpenAI Chat LLM integration for Nomos."""

    __provider__: str = "azure"

    def __init__(
        self, model: str = "gpt-4o-mini", embedding_model: Optional[str] = None, **kwargs
    ) -> None:
        """
        Initialize the AzureOpenAIChatLLM.

        :param model: Model name to use (default: gpt-4o-mini).
        :param embedding_model: Model name for embeddings (default: text-embedding-3-small).
        :param kwargs: Additional parameters for Azure OpenAI API.
        """
        try:
            from openai import AzureOpenAI
        except ImportError:
            raise ImportError(
                "Azure OpenAI package is not installed. Please install it using 'pip install nomos[openai]'."
            )
        self.model = model
        self.embedding_model = embedding_model or "text-embedding-3-small"
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        api_version = os.environ.get("OPENAI_API_VERSION")
        azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")

        assert api_key is not None, "AZURE_OPENAI_API_KEY environment variable must be set."
        assert api_version is not None, "OPENAI_API_VERSION environment variable must be set."
        if api_key is None:
            raise ValueError("AZURE_OPENAI_API_KEY environment variable must be set.")
        if api_version is None:
            raise ValueError("OPENAI_API_VERSION environment variable must be set.")
        if azure_endpoint is None:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable must be set.")

        self.client = AzureOpenAI(
            api_key=api_key, azure_endpoint=azure_endpoint, api_version=api_version
        )


__all__ = ["OpenAI", "AzureOpenAI"]
