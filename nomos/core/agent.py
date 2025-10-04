"""Agent configuration and management for Nomos."""

import os
from typing import Dict, List, Optional, Union

from .config import AgentConfig
from ..llms import LLMBase
from ..memory.base import Memory
from ..models.agent import DecisionConstraints, Event, Response, State, Step
from ..models.flow import Flow
from ..models.tool import ToolWrapper, get_tools
from ..utils.flow_utils import create_flows_from_config
from ..utils.logging import log_debug, log_error

from .session import Session


class Agent:
    """Main interface for creating and managing Nomos Agents."""

    def __init__(
        self,
        llm: Union[LLMBase, Dict[str, LLMBase]],
        name: str,
        steps: List[Step],
        start_step_id: str,
        persona: Optional[str] = None,
        system_message: Optional[str] = None,
        tools: Optional[List[Union[callable, ToolWrapper]]] = None,
        flows: Optional[List[Flow]] = None,
        show_steps_desc: bool = False,
        max_errors: int = 3,
        max_iter: int = 5,
        config: Optional[AgentConfig] = None,
        embedding_model: Optional[LLMBase] = None,
    ) -> None:
        """
        Initialize an Agent.

        :param llm: LLMBase instance or dictionary of LLMs.
        :param name: Name of the agent.
        :param steps: List of Step objects.
        :param start_step_id: ID of the starting step.
        :param persona: Optional persona string.
        :param system_message: Optional system message.
        :param tools: List of tool callables or ToolWrapper instances.
        :param flows: Optional list of Flow objects.
        :param show_steps_desc: Whether to show step descriptions.
        :param max_errors: Maximum consecutive errors before stopping or fallback.
        :param max_iter: Maximum number of decision loops for single action.
        :param config: Optional AgentConfig.
        :param embedding_model: Optional LLMBase instance for embeddings.
        """
        self.llm = llm
        self.name = name
        self.steps = {s.step_id: s for s in steps}
        self.start = start_step_id
        self.system_message = system_message
        self.persona = persona
        self.show_steps_desc = show_steps_desc
        self.max_errors = max_errors
        self.max_iter = max_iter
        self.config = config
        self.embedding_model = (
            embedding_model
            or (config.get_embedding_model() if config else None)
            or (llm if isinstance(llm, LLMBase) else llm.get("global", None))
        )
        assert self.embedding_model, "Embedding model must be provided or configured."
        self._setup_logging()
        self.flows = flows or (
            list(create_flows_from_config(config).flows.values())
            if config and config.flows
            else None
        )

        # Remove duplicates of tools based on their names or IDs
        seen = set()
        _tools = []
        for tool in tools or []:
            tool_id = (
                tool.name if isinstance(tool, ToolWrapper) else getattr(tool, "__name__", None)
            )
            tool_id = tool_id or id(tool)  # Fallback to id if no name
            if tool_id not in seen:
                seen.add(tool_id)
                _tools.append(tool)

        del seen  # Clear the seen set to free memory

        self.tools = get_tools(_tools, config.tools.tool_defs if config and config.tools else None)
        del _tools  # Clear the temporary list to free memory

        # Validate start step ID
        if start_step_id not in self.steps:
            log_error(f"Start step ID {start_step_id} not found in steps")
            raise ValueError(f"Start step ID {start_step_id} not found in steps")
        # Validate step IDs in routes
        for step in self.steps.values():
            for route in step.routes:
                if route.target not in self.steps:
                    log_error(
                        f"Route target {route.target} not found in steps for step {step.step_id}"
                    )
                    raise ValueError(
                        f"Route target {route.target} not found in steps for step {step.step_id}"
                    )

        # Validate tool names
        for step in self.steps.values():
            # check if the step.available tools is subset of the session tools
            if not set(step.available_tools).issubset(set(self.tools.keys())):
                err_msg = f"Step {step.step_id} has tools that are not defined in agent tools"
                log_error(err_msg)
                raise ValueError(err_msg)

        # Go through all the steps and if there are examples in them, perform batch embedding
        for step in self.steps.values():
            if step.examples:
                log_debug(f"Step {step.step_id} has examples, performing batch embedding")
                step.batch_embed_examples(embedding_model=self.embedding_model)

    @classmethod
    def from_config(
        cls,
        config: AgentConfig,
        llm: Optional[Union[LLMBase, Dict[str, LLMBase]]] = None,
        tools: Optional[List[Union[callable, ToolWrapper]]] = None,
    ) -> "Agent":
        """
        Create an Agent from an AgentConfig object.

        :param config: AgentConfig instance.
        :param llm: Optional LLMBase instance or dictionary of LLMs.
        :param tools: List of tool callables.
        :return: Agent instance.
        """
        _llm = llm or config.get_llm()
        assert _llm, "LLM must be provided either as a parameter or in the config."

        tools = tools or []
        tools.extend(config.tools.get_tools())
        return cls(
            llm=_llm,
            name=config.name,
            steps=config.steps,
            start_step_id=config.start_step_id,
            system_message=config.system_message,
            persona=config.persona,
            tools=tools,
            show_steps_desc=config.show_steps_desc,
            max_errors=config.max_errors,
            max_iter=config.max_iter,
            config=config,
        )

    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        # temporary fix until config is made available to other parts.
        if self.config and self.config.logging:
            logging_config = self.config.logging
            os.environ.setdefault("NOMOS_ENABLE_LOGGING", str(logging_config.enable).lower())
            if logging_config.handlers:
                os.environ.setdefault("NOMOS_LOG_LEVEL", logging_config.handlers[0].level.upper())

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