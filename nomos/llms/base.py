"""LLMBase class for Nomos agent framework."""

from typing import Dict, List, Literal, Optional, Type, Union

from pydantic import BaseModel

from ..constants import (
    DEFAULT_PERSONA,
    DEFAULT_SYSTEM_MESSAGE,
    PERIODICAL_SUMMARIZATION_SYSTEM_MESSAGE,
)
from ..models.agent import (
    Decision,
    Message,
    Step,
    StepIdentifier,
    Summary,
    ToolCall,
    create_action_enum,
)
from ..models.tool import Tool
from ..utils.logging import log_error
from ..utils.utils import create_base_model


class LLMBase:
    """Abstract base class for LLM integrations in Nomos."""

    __provider__: str = "base"
    _decision_model_cache: Dict[str, Type[BaseModel]] = {}

    def __init__(self) -> None:
        """Initialize the LLMBase class."""
        raise NotImplementedError("Subclasses should implement this method.")

    @staticmethod
    def get_routes_desc(current_step: Step) -> str:
        """
        Get a string description of available routes from the current step.

        :param current_step: The current step.
        :return: String description of routes.
        """
        routes_desc = [str(route) for route in current_step.routes]
        return "\n".join(routes_desc)

    @staticmethod
    def get_tools_desc(tools: Dict[str, Tool], available_tools: List[str]) -> str:
        """
        Get a string description of available tools for the current step.

        :param tools: Dictionary of tool name to Tool.
        :param available_tools: List of tool names available in this step.
        :return: String description of tools.
        """
        tools_desc = []
        for tool_name in available_tools:
            tool = tools.get(tool_name)
            if not tool:
                log_error(f"Tool '{tool_name}' not found in session tools. Skipping.")
                continue
            tools_desc.append(f"- {str(tool)}")
        return "\n".join(tools_desc)

    @staticmethod
    def format_history(
        history: List[Union[Message, Step, Summary]], max_errors: int = 3
    ) -> str:
        """
        Format the chat history for display or LLM input.

        :param history: List of Message or Step objects.
        :param max_errors: Maximum number of consecutive errors to display.
        :return: String representation of the history.
        """
        history_str = []
        # log_debug(f"Formatting chat history: {history}")
        n_last_consecutive_errors = 0
        for item in history:
            if isinstance(item, Message):
                if item.role == "error":
                    n_last_consecutive_errors += 1
                else:
                    n_last_consecutive_errors = 0
            elif isinstance(item, Step):
                n_last_consecutive_errors = 0
        if n_last_consecutive_errors > max_errors:
            log_error(
                f"Too many consecutive errors in history. Only showing the last {max_errors} errors out of  {n_last_consecutive_errors}"
            )
        for i, item in enumerate(history):
            # If the error message is not within the last max_errors, skip it
            if (
                isinstance(item, Message)
                and item.role == "error"
                and n_last_consecutive_errors > max_errors
                and i < len(history) - max_errors
            ):
                continue
            # If the fallback message is not the last one in the history, skip it
            if (
                isinstance(item, Message)
                and item.role == "fallback"
                and i < len(history) - 1
            ):
                continue
            history_str.append(str(item))
        return "\n".join(history_str)

    def get_messages(
        self,
        current_step: Step,
        tools: Dict[str, Tool],
        history: List[Union[Message, Step, Summary]],
        system_message: str,
        persona: str,
        max_examples: int = 5,
        embedding_model: Optional["LLMBase"] = None,
    ) -> List[Message]:
        """
        Construct the list of messages to send to the LLM.

        :param current_step: Current step.
        :param tools: Dictionary of tools.
        :param history: Conversation history.
        :param system_message: System prompt.
        :param persona: Agent persona.
        :return: List of Message objects.
        """
        messages = []
        system_prompt = system_message + "\n"
        system_prompt += f"{persona}\n\n"
        system_prompt += f"Instructions: {current_step.description.strip()}\n"
        system_prompt += (
            f"Available Routes:\n{self.get_routes_desc(current_step)}\n"
            if current_step.routes
            else ""
        )
        system_prompt += (
            f"\nAvailable Tools:\n{self.get_tools_desc(tools, current_step.tool_ids)}\n"
            if current_step.tool_ids
            else ""
        )
        if current_step.examples:
            example_str = ["\nExamples:"]
            for i, example in enumerate(
                current_step.get_examples(
                    embedding_model=embedding_model or self,
                    similarity_fn=self.text_similarity,
                    context_emb=self.embed_text(self.format_history(history)),
                    max_examples=max_examples,
                )
            ):
                example_str.append(f"{i + 1}. {str(example)}")
            system_prompt += "\n".join(example_str) + "\n"

        user_prompt = f"History:\n{self.format_history(history)}"

        messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=user_prompt))
        return messages

    def get_output(
        self,
        messages: List[Message],
        response_format: BaseModel,
        **kwargs: dict,
    ) -> BaseModel:
        """
        Get a structured response from the LLM.

        :param messages: List of Message objects.
        :param response_format: Pydantic model for the expected response.
        :param kwargs: Additional parameters for the LLM.
        :return: Parsed response as a BaseModel.
        """
        raise NotImplementedError("Subclasses should implement this method.")

    def _get_output(
        self,
        steps: Dict[str, Step],
        current_step: Step,
        tools: Dict[str, Tool],
        history: List[Union[Message, StepIdentifier, Summary]],
        response_format: BaseModel,
        system_message: Optional[str] = None,
        persona: Optional[str] = None,
        max_examples: int = 5,
        embedding_model: Optional["LLMBase"] = None,
    ) -> BaseModel:
        """
        Get a structured response from the LLM using the agent's context.

        :param steps: Dictionary of all steps. (step_id -> Step)
        :param current_step: Current step.
        :param tools: Dictionary of tools.
        :param history: Conversation history.
        :param response_format: Pydantic model for the expected response.
        :param system_message: Optional system prompt.
        :param persona: Optional agent persona.
        :param max_examples: Maximum number of examples to include.
        :return: Parsed response as a BaseModel.
        """
        history = [
            steps[item.step_id] if isinstance(item, StepIdentifier) else item
            for item in history
        ]
        messages = self.get_messages(
            current_step=current_step,
            tools=tools,
            history=history,
            system_message=(
                system_message if system_message else DEFAULT_SYSTEM_MESSAGE.strip()
            ),
            persona=persona if persona else DEFAULT_PERSONA.strip(),
            max_examples=max_examples,
            embedding_model=embedding_model,
        )
        return self.get_output(messages=messages, response_format=response_format)

    def generate(
        self,
        messages: List[Message],
        **kwargs: dict,
    ) -> str:
        """
        Generate a response from the LLM based on the provided messages.

        :param messages: List of Message objects.
        :param kwargs: Additional parameters for the LLM.
        :return: Generated response as a string.
        """
        raise NotImplementedError("Subclasses should implement this method.")

    def token_counter(self, text: str) -> int:
        """Count the number of tokens in a string."""
        return len(text.split())

    @staticmethod
    def _create_decision_model(
        current_step: Step, current_step_tools: List[Tool]
    ) -> Type[BaseModel]:
        """
        Dynamically create a Pydantic model for route/tool decision output.

        :param available_step_ids: List of available step IDs for routing.
        :param tool_ids: List of available tool names.
        :param tool_models: List of Pydantic models for tool arguments.
        :return: A dynamically created Pydantic BaseModel for the decision.
        """
        cache_key = current_step.step_id
        cached = LLMBase._decision_model_cache.get(cache_key)
        if cached is not None:
            return cached

        available_step_ids = current_step.get_available_routes()
        tool_ids = [tool.name for tool in current_step_tools]
        tool_models = [tool.get_args_model() for tool in current_step_tools]
        action_ids = (
            (["ASK", "ANSWER", "END"] if not current_step.auto_flow else ["END"])
            + (["MOVE"] if available_step_ids else [])
            + (["TOOL_CALL"] if tool_ids else [])
        )
        ActionEnum = create_action_enum(action_ids)  # noqa

        params = {
            "reasoning": {
                "type": List[str],
                "description": "Step by Step Reasoning to Decide",
            },
            "action": {"type": ActionEnum, "description": "Next Action"},
        }

        if not current_step.auto_flow:
            if current_step.answer_model:
                answer_model = current_step.get_answer_model()
                response_type = Union.__getitem__((str, answer_model))
                response_desc = (
                    f"Response as string if ASK or {answer_model.__name__} if ANSWER."
                )
            else:
                response_type = str
                response_desc = "Response (String) if ASK or ANSWER."
            params["response"] = {
                "type": response_type,
                "description": response_desc,
                "optional": True,
                "default": None,
            }
            if current_step.quick_suggestions:
                params["suggestions"] = {
                    "type": List[str],
                    "description": "Quick User Input Suggestions for the User to Choose if ASK.",
                    "optional": True,
                    "default": None,
                }

        if len(available_step_ids) > 0:
            params["step_transition"] = {
                "type": Literal.__getitem__(tuple(available_step_ids)),
                "description": "Step Id (String) if MOVE.",
                "optional": True,
                "default": None,
            }

        if len(tool_ids) > 0 and len(tool_models) > 0:
            tool_call_model = create_base_model(
                "ToolCall",
                {
                    "tool_name": {
                        "type": Literal.__getitem__(tuple(tool_ids)),
                        "description": "Tool name for TOOL_CALL.",
                    },
                    "tool_kwargs": {
                        "type": (
                            tool_models[0]
                            if len(tool_models) == 1
                            else Union.__getitem__(tuple(tool_models))
                        ),
                        "description": "Corresponding Tool arguments for TOOL_CALL.",
                    },
                },
            )
            params["tool_call"] = {
                "type": tool_call_model,
                "description": "Tool Call (ToolCall) if TOOL_CALL.",
                "optional": True,
                "default": None,
            }

        assert (
            len(params) > 2
        ), "Something went wrong, Please check the step configuration."

        model = create_base_model(
            "Decision",
            params,
        )
        LLMBase._decision_model_cache[cache_key] = model
        return model

    @staticmethod
    def _create_decision_from_output(
        output: BaseModel,
    ) -> Decision:
        """
        Create a Decision object from the LLM output.

        :param output: LLM output as a BaseModel.
        :return: Decision object.
        """
        return Decision(
            reasoning=output.reasoning,
            action=output.action.value,
            response=output.response if hasattr(output, "response") else None,
            suggestions=output.suggestions if hasattr(output, "suggestions") else None,
            step_transition=(
                output.step_transition if hasattr(output, "step_transition") else None
            ),
            tool_call=(
                ToolCall(
                    tool_name=output.tool_call.tool_name,
                    tool_kwargs=output.tool_call.tool_kwargs,
                )
                if hasattr(output, "tool_call") and output.tool_call
                else None
            ),
        )

    def embed_text(self, text: str) -> List[float]:
        """
        Generate an embedding for the given text.

        :param text: Text to embed.
        :return: List of floats representing the embedding.
        """
        raise NotImplementedError(
            "This LLM does not support text embedding. Please Specify an embedding model."
        )

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.

        :param texts: List of texts to embed.
        :return: List of embeddings, each embedding is a list of floats.
        """
        raise NotImplementedError(
            "This LLM does not support batch text embedding. Please Specify an embedding model."
        )

    def text_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """
        Calculate the similarity between two text embeddings (cosine similarity).

        :param emb1: Embedding of the first text.
        :param emb2: Embedding of the second text.
        :return: Similarity score as a float.
        """
        import numpy as np

        if len(emb1) != len(emb2):
            raise ValueError("Embeddings must be of the same length.")
        emb1 = np.array(emb1)
        emb2 = np.array(emb2)
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)

    def generate_summary(
        self, history: List[Union[Message, StepIdentifier, Summary]]
    ) -> Summary:
        """
        Generate a summary of the conversation history.

        :param history: List of Message or StepIdentifier objects.
        :return: Summary object containing the summarized content.
        """
        items_str = "\n".join([str(item) for item in history])
        summary = self.get_output(
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


__all__ = ["LLMBase"]
