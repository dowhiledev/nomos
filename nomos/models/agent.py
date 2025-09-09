"""Flow models for Nomos's decision-making process."""

import heapq
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Union,
)
from uuid import uuid4

from pydantic import BaseModel, Field

from ..utils.utils import create_base_model, create_enum

if TYPE_CHECKING:
    from ..llms.base import LLMBase
    from ..models.flow import FlowContext


class Action(Enum):
    """
    Enum representing the possible actions in the agent's flow.

    Attributes:
        MOVE: Transition to another step.
        RESPOND: Provide or request information from the user.
        TOOL_CALL: Call a tool with arguments.
        END: End the flow.
    """

    MOVE = "MOVE"
    RESPOND = "RESPOND"
    TOOL_CALL = "TOOL_CALL"
    END = "END"


class Route(BaseModel):
    """
    Represents a route (transition) from one step to another in the flow.

    Attributes:
        target (str): The target step ID.
        condition (str): The condition for taking this route.
    """

    target: str = Field(
        ...,
        description="Target step ID to move to when this route is taken.",
        validation_alias="to",
        serialization_alias="to",
    )
    condition: str = Field(
        ...,
        description="Condition that must be met to take this route.",
        validation_alias="when",
        serialization_alias="when",
    )

    model_config = {"populate_by_name": True}

    def __str__(self) -> str:
        """Return a string representation of the route."""
        return f"- if '{self.condition}' then -> {self.target}"


class StepIdentifier(BaseModel):
    """
    Represents a step identifier in the flow.

    Attributes:
        step_id (str): Unique identifier for the step.
    """

    step_id: str


class DecisionExample(BaseModel):
    """Represents an example decision made by the agent."""

    context: str
    decision: Union["Decision", str]
    visibility: Literal["always", "never", "dynamic"] = "dynamic"
    _ctx_embedding: Optional[List[float]] = None

    def __str__(self) -> str:
        """Return a string representation of the decision example."""
        return f"{self.context} -> {self.decision}"

    def embedding(self, EmbeddingModel: "LLMBase") -> List[float]:
        """Get the context embedding if available."""
        if self._ctx_embedding is not None:
            return self._ctx_embedding
        self._ctx_embedding = EmbeddingModel.embed_text(self.context)
        return self._ctx_embedding


class StepOverrides(BaseModel):
    """
    Represents overrides for a step's configuration.

    Attributes:
        persona (Optional[str]): Override for the persona.
        llm (Optional[LLMConfig]): Override for the LLM configuration.
    """

    persona: Optional[str] = None
    llm: str = "global"


class Step(BaseModel):
    """
    Represents a step in the agent's flow.

    Attributes:
        step_id (str): Unique identifier for the step.
        description (str): Description of the step.
        routes (List[Route]): List of possible routes from this step.
        available_tools (List[str]): List of tool names available in this step.
        tools (List[Tool]): List of Tool objects available in this step.
        answer_model (Optional[Union[str, Dict[str, Dict[str, Any]], BaseModel]]): Pydantic model for the agent's answer structure. Can be a dict, BaseModel class, or string reference to a schema.
        auto_flow (bool): Flag indicating if the step should automatically flow without additonal inputs or answering.
        provide_suggestions (bool): Flag indicating if the step should provide suggestions to the user.
    Methods:
        get_available_routes() -> List[str]: Get the list of available route targets.
    """

    step_id: str = Field(..., validation_alias="id", serialization_alias="id")
    description: str = Field(..., validation_alias="desc", serialization_alias="desc")
    routes: List[Route] = Field(
        default_factory=list,
        validation_alias="paths",
        serialization_alias="paths",
    )
    available_tools: List[str] = Field(
        default_factory=list,
        validation_alias="tools",
        serialization_alias="tools",
    )
    answer_model: Optional[Union[str, Dict[str, Dict[str, Any]], BaseModel]] = None
    auto_flow: bool = False
    quick_suggestions: bool = False
    flow_id: Optional[str] = None  # Add this to associate steps with flows
    overrides: Optional[StepOverrides] = None
    examples: Optional[List[DecisionExample]] = Field(
        None, validation_alias="eg", serialization_alias="eg"
    )

    model_config = {"populate_by_name": True}

    def __hash__(self) -> int:
        """Get the hash of the step based on its ID."""
        return hash(self.step_id)

    def __str__(self) -> str:
        """Return a string representation of the step."""
        return f"[Step] {self.step_id}: {self.description}"

    @classmethod
    def is_deferred_tool(cls, tool_identifier: str) -> bool:
        """
        Check if the tool identifier is a deferred tool. Tools of a deferred tool are fetch at runtime.

        :param tool_identifier: The identifier of the tool.
        :return: True if the tool is a deferred tool, False otherwise.
        """
        parts = tool_identifier.strip("/").split("/")
        return len(parts) == 2 and parts[0] == "@mcp"

    def model_post_init(self, __context) -> None:
        """Validate that auto_flow steps have at least one tool or route."""
        if self.auto_flow and not (self.routes or self.available_tools):
            raise ValueError(
                f"Step '{self.step_id}': When auto_flow is True, at least one tool or route must be available"
            )
        if self.auto_flow and self.quick_suggestions:
            raise ValueError(
                f"Step '{self.step_id}': When auto_flow is True, quick_suggestions cannot be True"
            )

    def get_answer_model(self) -> BaseModel:
        """
        Get the Pydantic model for the agent's answer structure.

        :return: Pydantic model for the answer structure.
        """
        if isinstance(self.answer_model, dict):
            return create_base_model("AnswerModel", self.answer_model)
        elif isinstance(self.answer_model, type) and issubclass(self.answer_model, BaseModel):
            return self.answer_model
        elif isinstance(self.answer_model, str):
            # Handle schema reference like "schema_name" or "schema_name.model_name"
            from ..utils.schema_loader import schema_registry

            parts = self.answer_model.split(".")
            if len(parts) == 1:
                # Just schema name, use the first available model or try case-insensitive match
                schema_name = parts[0]
                schema_models = schema_registry._schemas.get(schema_name, {})
                if not schema_models:
                    raise ValueError(f"Step '{self.step_id}': Schema '{schema_name}' not found")

                # Try exact match first
                if schema_name in schema_models:
                    return schema_models[schema_name]

                # Try case-insensitive match
                for model_name, model in schema_models.items():
                    if model_name.lower() == schema_name.lower():
                        return model

                # Use the first available model
                return next(iter(schema_models.values()))
            elif len(parts) == 2:
                schema_name, model_name = parts
                return schema_registry.get_model(schema_name, model_name)
            else:
                raise ValueError(
                    f"Step '{self.step_id}': answer_model string must be in format 'schema_name' or 'schema_name.model_name'"
                )
        else:
            raise ValueError(
                f"Step '{self.step_id}': answer_model must be a dictionary, BaseModel class, or string reference"
            )

    def get_available_routes(self) -> List[str]:
        """
        Get the list of available route targets from this step.

        :return: List of target step IDs.
        """
        return [route.target for route in self.routes]

    @property
    def persona(self) -> Optional[str]:
        """
        Get the persona override for this step.

        :return: Persona string if available, otherwise None.
        """
        return self.overrides.persona if self.overrides else None

    @property
    def llm(self) -> str:
        """
        Get the LLM override for this step.

        :return: LLM Id.
        """
        return self.overrides.llm if self.overrides else "global"

    @property
    def tool_ids(self) -> List[str]:
        """
        Get the list of available tool names from this step.

        :return: List of tool names.
        """
        return list(filter(lambda t: not Step.is_deferred_tool(t), self.available_tools))

    @property
    def deferred_tool_ids(self) -> List[str]:
        """
        Get the list of available tool names that are deferred tools.

        :return: List of tool names.
        """
        return list(filter(Step.is_deferred_tool, self.available_tools))

    def get_step_identifier(self) -> StepIdentifier:
        """
        Get the step identifier for this step.

        :return: StepIdentifier object.
        """
        return StepIdentifier(step_id=self.step_id)

    def extend_tools(self, tools: List[str]) -> None:
        """
        Extend the list of tools available in this step.

        :param tools: List of tool names.
        """
        self.available_tools.extend(set(tools))

    def reduce_tools(self, tools: List[str]) -> None:
        """
        Reduce the list of tools available in this step.

        :param tools: List of tool names to remove.
        """
        self.available_tools = [tool for tool in self.available_tools if tool not in tools]

    def get_examples(
        self,
        embedding_model: "LLMBase",
        similarity_fn: Callable,
        max_examples: int,
        context_emb: List[float],
        threshold: float = 0.5,
    ) -> List[DecisionExample]:
        """
        Get examples for this step based on the provided context.

        :param similarity_fn: Function to compute similarity between contexts.
        :param max_examples: Maximum number of examples to return.
        :param context_emb: Embedding of the context to compare against examples.
        :param threshold: Minimum similarity score to include an example.
        :return: List of tuples containing DecisionExample and its similarity score.
        """
        _always = [
            (example, 1.0) for example in self.examples or [] if example.visibility == "always"
        ]
        dynamic_examples = [
            example for example in self.examples or [] if example.visibility == "dynamic"
        ]
        _examples = [
            (example, similarity_fn(example.embedding(embedding_model), context_emb))
            for example in dynamic_examples
        ]
        # Only keep the top (max_examples - len(_always)) dynamic examples by similarity
        _examples = heapq.nlargest(max_examples - len(_always), _examples, key=lambda x: x[1])
        examples = _always + _examples
        return [example for example, similarity in examples if similarity >= threshold]

    def batch_embed_examples(self, embedding_model: "LLMBase") -> None:
        """
        Batch embed examples for this step.

        :param embedding_model: The LLMBase instance to use for embedding.
        :param max_examples: Maximum number of examples to embed.
        """
        if not self.examples:
            return
        ctxs = [example.context for example in self.examples]
        embeddings = embedding_model.embed_batch(ctxs)
        for example, emb in zip(self.examples, embeddings):
            example._ctx_embedding = emb


class Event(BaseModel):
    """An event stored in memory."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    type: str
    content: str
    decision: Optional["Decision"] = None

    def __str__(self) -> str:
        return f"[{self.type.title()}] {self.content}"


class Message(BaseModel):
    """
    Represents a message in the conversation history.

    Attributes:
        role (str): The role of the message sender (e.g., 'user', 'assistant', 'tool').
        content (str): The message content.
    """

    role: Union[Literal["user", "tool", "error", "fallback"], str]
    content: str

    def __str__(self) -> str:
        """Return a string representation of the message."""
        return f"[{self.role.title()}] {self.content}"


class Summary(BaseModel):
    """Summary of a list of messages."""

    summary: List[str] = Field(..., description="Detailed summary of the Context. (Min 5 items)")

    @property
    def content(self) -> str:
        """Get the summary content as a single string (markdown list)."""
        return "\n".join(f"- {item}" for item in self.summary if item.strip())

    def __str__(self) -> str:
        """Return a string representation of the summary."""
        return f"[Past Summary] {self.content}"


class FlowState(BaseModel):
    """Represents the state of a flow in the agent's session."""

    flow_id: str
    flow_context: "FlowContext"
    flow_memory_context: List[Union[Event, Summary, StepIdentifier]] = Field(default_factory=list)


class State(BaseModel):
    """Container for session data required by ``Agent.next``."""

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    current_step_id: str
    history: List[Union[Summary, Event, StepIdentifier]] = Field(default_factory=list)
    flow_state: Optional[FlowState] = None


class ToolCall(BaseModel):
    """
    Represents a tool call made by the agent.

    Attributes:
        tool_name (str): Name of the tool to call.
        tool_kwargs (BaseModel): Arguments to pass to the tool.
    """

    tool_name: str
    tool_kwargs: BaseModel


@dataclass
class DecisionConstraints:
    """Constraints for dynamically creating decision models."""

    actions: Optional[List[str]] = None
    fields: Optional[List[str]] = None
    tool_name: Optional[str] = None

    def __hash__(self) -> int:
        """Get the hash of the constraints based on their attributes."""
        return hash(
            (
                tuple(self.actions) if self.actions else None,
                tuple(self.fields) if self.fields else None,
                self.tool_name,
            )
        )


class Decision(BaseModel):
    """
    Represents the decision made by the agent at a step.

    Attributes:
        reasoning (List[str]): Step by step reasoning to decide.
        action (Action): The next action to take.
        response (Optional[Union[str, BaseModel]]): Response if RESPOND.
        suggestions (Optional[List[str]]): Quick user input suggestions if RESPOND.
        step_id (Optional[str]): Step ID to transition to if MOVE.
        tool_call (Optional[Dict[str, Any]]): Tool call details if TOOL_CALL.
    """

    reasoning: List[str]
    action: Action
    response: Optional[Union[str, BaseModel]] = None
    suggestions: Optional[List[str]] = None
    step_id: Optional[str] = None
    tool_call: Optional[ToolCall] = None

    def __str__(self) -> str:
        """Return a string representation of the decision."""
        if self.action == Action.RESPOND:
            return f"action: {self.action.value}, response: {self.response}"
        elif self.action == Action.MOVE:
            return f"action: {self.action.value}, step_id: {self.step_id}"
        elif self.action == Action.TOOL_CALL and self.tool_call:
            return f"action: {self.action.value}, tool_call: {self.tool_call.tool_name} with args {self.tool_call.tool_kwargs.model_dump_json()}"
        elif self.action == Action.END:
            return f"action: {self.action.value}"
        else:
            raise ValueError(f"Unknown action: {self.action}")


def create_action_enum(actions: List[str]) -> Enum:
    """
    Dynamically create an Enum class for actions.

    :param name: Name of the enum.
    :param actions: Dictionary of action names to values.
    :return: A dynamically created Enum class.
    """
    actions_dict = {action: action.upper() for action in actions if isinstance(action, str)}
    return create_enum("Action", actions_dict)


def history_to_types(
    context: List[dict],
) -> List[Union[Event, Summary, StepIdentifier]]:
    """
    Convert a list of history dictionaries to structured Event records.

    :param context: Dictionary containing the history.
    :return: List of Event, Summary, or StepIdentifier objects.
    """
    history = []
    for item in context:
        if isinstance(item, dict):
            if "type" in item and "content" in item:
                history.append(Event(**item))
            elif "role" in item and "content" in item:
                history.append(Event(type=item["role"], content=item["content"]))
            elif "summary" in item:
                history.append(Summary(**item))
            elif "step_id" in item:
                history.append(StepIdentifier(**item))
        else:
            raise ValueError(f"Unknown history item type: {type(item)}")
    return history


class Response(BaseModel):
    """
    Represents a response from the agent's session.

    Attributes:
        decision (Decision): The decision made by the agent.
        tool_output (Optional[Any]): Output from the tool call, if any.
        state (State): The updated session state after the decision.
    """

    decision: Decision
    tool_output: Optional[Any] = None
    state: Optional[State] = None

    def __str__(self) -> str:
        """Return a string representation of the response."""
        return f"Decision: {self.decision}, Tool Output: {self.tool_output}, State: {self.state}"


__all__ = [
    "Action",
    "Route",
    "Step",
    "ToolCall",
    "Event",
    "Message",
    "Response",
    "Summary",
    "State",
    "Decision",
    "DecisionConstraints",
    "create_action_enum",
    "DecisionExample",
    "StepIdentifier",
    "history_to_types",
]


# Fix forward reference after all models are defined
def _rebuild_models() -> None:
    """Rebuild models to resolve forward references."""
    try:
        from .flow import FlowContext  # noqa

        FlowState.model_rebuild()
        State.model_rebuild()
    except ImportError:
        # Handle case where flow module is not available
        pass


_rebuild_models()
