"""Mistral LLM integration for Nomos."""

import os
from typing import List, Optional

from pydantic import BaseModel

from ..models.agent import Message
from .base import LLMBase

import instructor


class Mistral(LLMBase):
    """Mistral AI LLM integration for Nomos."""

    __provider__: str = "mistral"

    def __init__(
        self,
        model: str = "ministral-8b-latest",
        embedding_model: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Initialize the MistralAI LLM.

        :param model: Model name to use (default: ministral-8b-latest).
        :param embedding_model: Model name for embeddings (default: mistral-embed).
        :param kwargs: Additional parameters for Mistral API.
        """
        try:
            from mistralai import Mistral
        except ImportError:
            raise ImportError(
                "Mistral package is not installed. Please install it using 'pip install mistralai'."
            )

        self.model = model
        self.embedding_model = embedding_model or "mistral-embed"
        api_key = os.environ["MISTRAL_API_KEY"]
        self.mistral_client = Mistral(api_key=api_key, **kwargs)
        self.client = instructor.from_mistral(
            client=self.mistral_client,
            model=self.model,
            mode=instructor.Mode.MISTRAL_TOOLS,
            use_async=False,
        )

    def get_output(
        self,
        messages: List[Message],
        response_format: BaseModel,
        **kwargs: dict,
    ) -> BaseModel:
        """
        Get a structured response from the Mistral LLM.

        :param messages: List of Message objects.
        :param response_format: Pydantic model for the expected response.
        :param kwargs: Additional parameters for Mistral API.
        :return: Parsed response as a BaseModel.
        """
        _messages = [msg.model_dump() for msg in messages]
        resp = self.client.messages.create(
            response_model=response_format,
            messages=_messages,
            **kwargs,
        )
        return resp

    def generate(
        self,
        messages: List[Message],
        **kwargs: dict,
    ) -> str:
        """
        Generate a response from the Mistral LLM.

        :param messages: List of Message objects.
        :param kwargs: Additional parameters for Mistral API.
        :return: Generated response as a string.
        """
        _messages = [msg.model_dump() for msg in messages]
        comp = self.mistral_client.chat.complete(model=self.model, messages=_messages, **kwargs)
        return comp.choices[0].message.content if comp.choices else ""  # type: ignore

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts using the Mistral embedding model."""
        from mistralai import EmbeddingResponse

        response: EmbeddingResponse = self.mistral_client.embeddings.create(
            model=self.embedding_model, input=texts, output_dtype="float"
        )
        embs = [item.embedding for item in response.data]
        return embs

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text using the OpenAI embeddings API."""
        embs = self.embed_batch([text])
        return embs[0]


__all__ = ["Mistral"]
