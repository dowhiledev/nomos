"""Flow-specific memory module that preserves complete information within an specified flow."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from .base import Memory
from ..constants import PERIODICAL_SUMMARIZATION_SYSTEM_MESSAGE
from ..llms import LLMConfig
from ..models.agent import Message, StepIdentifier, Summary
from ..models.flow import FlowComponent, FlowContext


class Retriver:
    """Base class for retrievers."""

    def __init__(self) -> None:
        """Initialize retriever."""
        self.context: list[str] = []

    def index(self, items: List[str], **kwargs) -> None:
        """Index items for retrieval."""
        raise NotImplementedError("Subclasses should implement this method.")

    def update(self, items: List[str], **kwargs) -> None:
        """Update indexed items."""
        raise NotImplementedError("Subclasses should implement this method.")

    def retrieve(self, query: str, **kwargs) -> list:
        """Retrieve items from memory based on a query."""
        raise NotImplementedError("Subclasses should implement this method.")


class BM25Retriever(Retriver):

    def __init__(self, **kwargs) -> None:
        """Initialize BM25 retriever."""
        import bm25s

        super().__init__()
        self.retriever = bm25s.BM25(**kwargs)

    def index(self, items: List[str], **kwargs) -> None:
        """Index items using BM25."""
        self.context.extend(items)
        self.retriever.index(self.context)

    def update(self, items: List[str], **kwargs) -> None:
        """Update indexed items."""
        self.context.extend(items)
        self.retriever.index(self.context)

    def retrieve(self, query: str, **kwargs) -> list:
        """Retrieve items using BM25 based on a query."""
        import bm25s

        if not self.context:
            return []
        query_tokens = bm25s.tokenize(query)
        results = self.retriever.retrieve(query_tokens, corpus=self.context, **kwargs)
        return results


class EmbeddingRetriever(Retriver):
    """Retriever that uses embeddings for similarity search."""

    def __init__(self, embedding_model, **kwargs) -> None:
        super().__init__()
        self.embedding_model = embedding_model
        self.embeddings: list[list[float]] = []

    def index(self, items: List[str], **kwargs) -> None:
        self.context = items
        self.embeddings = self.embedding_model.embed_batch(items)

    def update(self, items: List[str], **kwargs) -> None:
        self.context.extend(items)
        self.embeddings.extend(self.embedding_model.embed_batch(items))

    def retrieve(self, query: str, top_k: int = 5, **kwargs) -> list:
        if not self.context:
            return []
        query_emb = self.embedding_model.embed_text(query)
        scores = [
            (item, self.embedding_model.text_similarity(query_emb, emb))
            for item, emb in zip(self.context, self.embeddings)
        ]
        scores.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in scores[:top_k]]


class RetrieverConfig(BaseModel):
    """Configuration for a retriever."""

    method: str
    kwargs: Dict[str, Any] = {}

    def get_retriever(self, embedding_model: Optional[Any] = None) -> Retriver:
        """Get an instance of the retriever based on the configuration."""
        if self.method == "bm25":
            return BM25Retriever(**self.kwargs)
        if self.method == "embedding":
            if embedding_model is None:
                raise ValueError("Embedding model required for embedding retriever")
            return EmbeddingRetriever(embedding_model, **self.kwargs)
        raise ValueError(f"Unsupported retriever method: {self.method}")


class FlowMemory(Memory):
    """Memory that preserves complete information within an flow."""

    def __init__(
        self,
        llm: Optional[LLMConfig] = None,
        retriever: Optional[RetrieverConfig] = None,
    ) -> None:
        """Initialize FlowMemory."""
        super().__init__()
        retriever = retriever or RetrieverConfig(method="embedding")
        llm = llm or LLMConfig(provider="openai", model="gpt-4o-mini")
        self.llm = llm.get_llm()
        self.retriever = retriever.get_retriever(self.llm)
        self.context = []

    def _enter(
        self, previous_context: Optional[List[Union[Message, Summary]]] = None
    ) -> None:
        """Enter the flow memory, optionally using previous context."""
        if previous_context:
            self.context.append(self._generate_summary(previous_context))
            self._index()

    def _exit(self) -> Summary:
        """Exit the flow memory and return a summary of the context."""
        return self._generate_summary(
            [item for item in self.context if isinstance(item, (Message, Summary))]
        )

    def _index(self) -> None:
        """Index the current context for retrieval."""
        context_items = [str(item) for item in self.context]
        self.retriever.index(context_items)

    def _generate_summary(self, items: List[Union[Message, Summary]]) -> Summary:
        """Generate a summary from a list of items."""
        items_str = "\n".join([str(item) for item in items])
        summary = self.llm.get_output(
            messages=[
                Message(role="system", content=PERIODICAL_SUMMARIZATION_SYSTEM_MESSAGE),
                Message(
                    role="user",
                    content=f"Summarize the following Context:\n\n{items_str}",
                ),
            ],
            response_format=Summary,
        )
        assert isinstance(summary, Summary), "Summary generation failed."
        return summary

    def _search(self, query: str, **kwargs) -> list:
        """Search for items in memory that match the query."""
        return self.retriever.retrieve(query, **kwargs)

    def add_message(self, message: Message) -> None:
        """Add a message to the flow context."""
        self.context.append(message)
        self.retriever.update([str(message)])

    def get_context_summary(self) -> str:
        """Get a summary of the current context."""
        if not self.context:
            return "No context available."

        return "\n".join([str(item) for item in self.context[-10:]])  # Last 10 items


class FlowMemoryComponent(FlowComponent):
    """Flow-specific memory component."""

    def __init__(
        self,
        llm: Optional[Dict[str, Any]] = None,
        retriever: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """Initialize FlowMemoryComponent."""
        llm = LLMConfig(**llm) if llm else None
        retriever = RetrieverConfig(**retriever) if retriever else None
        self.memory = FlowMemory(llm=llm, retriever=retriever)

    def enter(self, context: FlowContext) -> None:
        """Initialize memory when entering flow."""
        self.memory._enter(context.previous_context)

    def exit(self, context: FlowContext) -> Summary:
        """Generate summary when exiting flow."""
        return self.memory._exit()

    def cleanup(self, context: FlowContext) -> None:
        """Clean up memory resources."""
        # Clear context or perform other cleanup
        self.memory.context.clear()

    def search(self, query: str, **kwargs) -> list:
        """Search in flow memory."""
        return self.memory._search(query, **kwargs)

    def add_to_context(self, item: Union[Message, Summary, StepIdentifier]) -> None:
        """Add item to flow memory context."""
        self.memory.context.append(item)
        self.memory.retriever.update([str(item)])


__all__ = [
    "FlowMemory",
    "RetrieverConfig",
    "FlowMemoryComponent",
    "EmbeddingRetriever",
]
