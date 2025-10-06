"""Agent configuration and management for Nomos."""

import os
from typing import Dict, List, Optional, TypedDict, Union

from .config import AgentConfig
from ..constants import (
    DEFAULT_PERSONA,
    DEFAULT_SYSTEM_MESSAGE,
    DEFAULT_MAX_ERRORS,
    DEFAULT_MAX_ITER,
)
from ..llms import LLMBase
from ..memory.base import Memory
from ..models.agent import Action, DecisionConstraints, Event, Response, State, Step
from ..models.flow import Flow
from ..models.tool import ToolWrapper, get_tools
from ..utils.flow_utils import create_flows_from_config
from ..utils.logging import log_debug, log_error

from .session import Session


class GlobalConfig(TypedDict):
    """Global configuration for the agent."""

    name: str
    persona: str
    system_message: str
    max_errors: int
    max_iter: int


class Agent:
    """Main interface for creating and managing Nomos Agents."""

    def __init__(
        self,
        config: AgentConfig,
        tools: Optional[List[Union[callable, ToolWrapper]]] = None,
    ) -> None:
        self.logging.initialize()  # TODO: Implement logging initialization in config
        self.llm = config.get_llm()
        self.embedding_model = config.get_embedding_model()
        assert self.llm, "Atleast one LLM must be configured."
        assert self.embedding_model, "Embedding model must be provided or configured."

        self.steps = config.steps
        assert len(self.steps) > 0, "Atleast one step must be configured."
        for step in self.steps:
            if step.examples:
                step.batch_embed_examples(embedding_model=self.embedding_model)
        self.start_step = (
            config.get_start_step()
        )  # TODO: Implement get start step logic in config
        self._validate_steps()  # TODO: Implement step validation logic

        self.tools = tools or []
        self.tools.extend(config.tools.get_tools())
        self.tools = get_tools(self.tools, config.tools.tool_defs)

        self.global_config = GlobalConfig(
            name=config.name,
            persona=config.persona or DEFAULT_PERSONA,
            system_message=config.system_message or DEFAULT_SYSTEM_MESSAGE,
            max_errors=config.max_errors or DEFAULT_MAX_ERRORS,
            max_iter=config.max_iter or DEFAULT_MAX_ITER,
        )
        self.config = config

        self.flows = config.get_flows()  # TODO: Implement get flows logic in config

    def create(self, memory: Optional[Memory] = None) -> Session:
        """
        Create a new Session for this agent.

        :param memory: Optional Memory instance.
        :return: Session instance.
        """
        # Need to ensure memory is fresh for each session
        memory = (
            memory or self.config.memory.get_memory()
            if self.config.memory
            else Memory()
        )
        return Session(
            agent=self,
            memory=memory,
        )

    def load(self, session_id: str) -> Session:
        """
        Load a Session by session_id.

        :param session_id: The session ID string.
        :return: Loaded Session instance.
        """
        return Session.load_session(session_id)

    def from_state(self, state: State) -> Session:
        """
        Create a Session from a State object.

        :param state: The session state.
        :return: Session instance.
        """
        memory = (
            self.config.memory.get_memory()
            if self.config and self.config.memory
            else Memory()
        )
        return Session(
            agent=self,
            memory=memory,
            state=state,
        )

    def __call__(
        self,
        input: Optional[Input] = None,
        state: Optional[State] = None,
        return_at: Optional[List[Action]] = [Action.RESPOND],
        constraints: Optional[DecisionConstraints] = None,
        skip_decision: bool = True,
        verbose: bool = False,
    ) -> Response:
        """
        Advance the session to the next step based on user input and LLM decision.

        :param input: Optional user input string or Input object.
        :param state: Optional session state as a State object.
        :param return_at: List of actions at which to return.
        :param constraints: Optional constraints for the decision model on retry.
        :param skip_decision: Whether to skip decision-making and proceed to tool execution.
        :param verbose: Whether to return verbose output.
        :return: A Response containing the decision and tool output, along with the updated session state.
        :raises ValueError: If state is provided but not a valid State object.
        """
        session = self.from_state(state) if state else self.create()
        res = session(
            input=input,
            return_at=return_at,
            constraints=constraints,
            verbose=verbose,
        )

        state = session.get_state()
        if skip_decision:
            for item in state.history:
                if isinstance(item, Event):
                    item.decision = None
            if state.flow_state:
                for item in state.flow_state.flow_memory_context:
                    if isinstance(item, Event):
                        item.decision = None
        res.state = state
        return res

    def show(self, save_path: Optional[str] = None, is_notebook: bool = True) -> None:
        """
        Visualize the agent's steps and flows.

        :param save_path: Optional path to save the visualization.
        :param is_notebook: Whether the current environment is a Jupyter notebook.
        """
        from ..utils.utils import create_mermaid_graph, mermaid_svg

        if not is_notebook and not save_path:
            raise ValueError(
                "save_path must be provided if not in a notebook environment."
            )

        mm_code = create_mermaid_graph(
            steps=self.steps, flows=self.flows if self.flows else [], tools=self.tools
        )
        mermaid_svg(
            mm_code,
            save_to=(
                os.path.join(save_path, f"{self.name}_graph.svg") if save_path else None
            ),
            display=is_notebook,
        )


__all__ = ["Agent"]
