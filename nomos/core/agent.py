"""Agent configuration and management for Nomos."""

import os
from typing import Dict, List, Optional, TypedDict, Union

from .config import AgentConfig
from ..constants import DEFAULT_PERSONA, DEFAULT_SYSTEM_MESSAGE, DEFAULT_MAX_ERRORS, DEFAULT_MAX_ITER
from ..llms import LLMBase
from ..memory.base import Memory
from ..models.agent import DecisionConstraints, Event, Response, State, Step
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
        self.logging.initialize() # TODO: Implement logging initialization in config
        self.llm = config.get_llm()
        self.embedding_model = config.get_embedding_model()
        assert self.llm, "Atleast one LLM must be configured."
        assert self.embedding_model, "Embedding model must be provided or configured."

        self.steps = config.steps
        assert len(self.steps) > 0, "Atleast one step must be configured."
        for step in self.steps:
            if step.examples:
                step.batch_embed_examples(embedding_model=self.embedding_model)
        self.start_step = config.get_start_step() # TODO: Implement get start step logic in config
        self._validate_steps() # TODO: Implement step validation logic

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

        self.flows = config.get_flows() # TODO: Implement get flows logic in config

    def create_session(self, memory: Optional[Memory] = None) -> Session:
        """
        Create a new Session for this agent.

        :param memory: Optional Memory instance.
        :return: Session instance.
        """
        log_debug("Creating new session")
        if not memory:
            memory = (
                self.config.memory.get_memory() if self.config and self.config.memory else Memory()
            )
        assert self.embedding_model, "Embedding model must be provided or configured."
        return Session(
            name=self.name,
            llm=self.llm,
            memory=memory,
            steps=self.steps,
            start_step_id=self.start,
            system_message=self.system_message,
            persona=self.persona,
            tools=self.tools,
            flows=list(self.flows) if self.flows else None,
            show_steps_desc=self.show_steps_desc,
            max_errors=self.max_errors,
            max_iter=self.max_iter,
            config=self.config,
            embedding_model=self.embedding_model,
        )

    def load_session(self, session_id: str) -> Session:
        """
        Load a Session by session_id.

        :param session_id: The session ID string.
        :return: Loaded Session instance.
        """
        log_debug(f"Loading session {session_id}")
        return Session.load_session(session_id)

    def get_session_from_state(self, state: State) -> Session:
        """
        Create a Session from a State object.

        :param state: The session state.
        :return: Session instance.
        """
        log_debug(f"Creating session from state: {state}")

        memory = self.config.memory.get_memory() if self.config and self.config.memory else Memory()

        assert self.embedding_model, "Embedding model must be provided or configured."
        session = Session(
            name=self.name,
            llm=self.llm,
            memory=memory,
            tools=self.tools,
            config=self.config,
            embedding_model=self.embedding_model,
            persona=self.persona,
            steps=self.steps,
            start_step_id=self.start,
            system_message=self.system_message,
            flows=list(self.flows) if self.flows else None,
            show_steps_desc=self.show_steps_desc,
            max_errors=self.max_errors,
            max_iter=self.max_iter,
            state=state,
        )

        return session

    def next(
        self,
        user_input: Optional[str] = None,
        session_data: Optional[Union[dict, State]] = None,
        return_tool: bool = False,
        return_step: bool = False,
        verbose: bool = False,
        decision_constraints: Optional[DecisionConstraints] = None,
        keep_event_decision: bool = False,
    ) -> Response:
        """
        Advance the session to the next step based on user input and LLM decision.

        :param user_input: Optional user input string.
        :param session_data: Optional session data as a dictionary or State object.
        :param return_tool: Whether to return tool results.
        :param return_step: Whether to return step Transitions.
        :param verbose: Whether to return verbose output.
        :param decision_constraints: Optional constraints for the decision model on retry.
        :param keep_event_decision: Whether to retain decision data in returned events.
        :return: A Response containing the decision and tool output, along with the updated session state.
        :raises ValueError: If session_data is provided but not a valid State object.
        """
        if isinstance(session_data, dict):
            session_data = State.model_validate(session_data)
        session = (
            self.get_session_from_state(session_data)
            if session_data is not None and isinstance(session_data, State)
            else self.create_session()
        )
        res = session.next(
            user_input=user_input,
            return_tool=return_tool,
            return_step=return_step,
            decision_constraints=decision_constraints,
            verbose=verbose,
        )
        state = session.get_state()
        if not keep_event_decision:
            for item in state.history:
                if isinstance(item, Event):
                    item.decision = None
            if state.flow_state:
                for item in state.flow_state.flow_memory_context:
                    if isinstance(item, Event):
                        item.decision = None
        res.state = state
        return res

    def display(self, save_path: Optional[str] = None, is_notebook: bool = True) -> None:
        """
        Visualize the agent's steps and flows.

        :param save_path: Optional path to save the visualization.
        :param is_notebook: Whether the current environment is a Jupyter notebook.
        """
        from ..utils.utils import create_mermaid_graph, mermaid_svg

        if not is_notebook and not save_path:
            raise ValueError("save_path must be provided if not in a notebook environment.")

        mm_code = create_mermaid_graph(
            steps=self.steps, flows=self.flows if self.flows else [], tools=self.tools
        )
        mermaid_svg(
            mm_code,
            save_to=os.path.join(save_path, f"{self.name}_graph.svg") if save_path else None,
            display=is_notebook,
        )


__all__ = ["Agent"]