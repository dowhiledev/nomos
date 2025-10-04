"""Session management and runtime logic for Nomos agents."""

import asyncio
import pickle
from typing import Any, Dict, List, Optional, Tuple, Union

from .config import AgentConfig
from ..llms import LLMBase
from ..memory.base import Memory
from ..memory.flow import FlowMemoryComponent
from ..models.agent import (
    Action,
    Decision,
    DecisionConstraints,
    Event,
    Response,
    State,
    Step,
    StepIdentifier,
)
from ..models.flow import Flow
from ..models.tool import (
    FallbackError,
    InvalidArgumentsError,
    MCPServer,
    Tool,
)
from ..state_machine import StateMachine
from ..utils.logging import log_debug, log_error, pp_response


class Session:
    """Manages a single agent session, including step IDs, tool calls, and history."""

    def __init__(
        self,
        name: str,
        llm: Union[LLMBase, Dict[str, LLMBase]],
        embedding_model: LLMBase,
        memory: Memory,
        steps: Dict[str, Step],
        start_step_id: str,
        tools: Dict[str, Tool],
        system_message: Optional[str] = None,
        persona: Optional[str] = None,
        flows: Optional[List[Flow]] = None,
        show_steps_desc: bool = False,
        max_errors: int = 3,
        max_iter: int = 5,
        config: Optional[AgentConfig] = None,
        state: Optional[State] = None,
        **kwargs,
    ) -> None:
        """
        Initialize a Session.

        :param name: Name of the agent.
        :param llm: LLMBase instance or dict of LLMs.
        :param embedding_model: LLMBase for embeddings.
        :param memory: Memory instance.
        :param steps: Dictionary of step_id to Step.
        :param start_step_id: ID of the starting step.
        :param tools: Dictionary of tool names to Tool instances.
        :param system_message: Optional system message.
        :param persona: Optional persona string.
        :param flows: Optional list of Flow objects.
        :param show_steps_desc: Whether to show step descriptions.
        :param max_errors: Maximum consecutive errors before stopping or fallback.
        :param max_iter: Maximum number of decision loops for single action.
        :param config: Optional AgentConfig.
        :param state: Optional session state data.
        """
        import uuid

        self.session_id = state.session_id if state else f"{name}_{str(uuid.uuid4())}"
        self.name = name
        self.llm_dict = llm if isinstance(llm, dict) else {"global": llm}
        self.steps = steps
        self.show_steps_desc = show_steps_desc
        self.system_message = system_message
        self.persona = persona
        self.max_errors = max_errors
        self.max_iter = max_iter
        self.config = config or AgentConfig(
            name=name,
            steps=list(steps.values()),
            start_step_id=start_step_id,
            system_message=system_message,
            persona=persona,
            show_steps_desc=show_steps_desc,
            max_errors=max_errors,
            max_iter=max_iter,
        )
        self.embedding_model = embedding_model

        self.deferred_tools: Dict[str, Tool] = {}
        self.tools: Dict[str, Tool] = tools

        # Compile state machine for fast transitions and flow lookups
        self.state_machine = StateMachine(
            self.steps,
            flows=flows,
            config=self.config,
            memory=memory,
            start_step_id=start_step_id,
        )
        self.state_machine.load_state(state)

        # Optional event emitter used for analytics
        self.event_emitter: Any = None

        # For OpenTelemetry tracing context
        self._otel_root_span_ctx: Any = None

    @property
    def current_step(self) -> Step:
        """Get the current step object."""
        return self.state_machine.current_step

    @property
    def memory(self) -> Memory:
        """Get the session memory."""
        return self.state_machine.memory

    def set_event_emitter(self, emitter: Any) -> None:
        """Attach an event emitter to this session."""
        self.event_emitter = emitter

    def save_session(self) -> None:
        """Save the current session to disk as a pickle file."""
        with open(f"{self.session_id}.pkl", "wb") as f:
            pickle.dump(self, f)
        log_debug(f"Session {self.session_id} saved to disk.")

    @classmethod
    def load_session(cls, session_id: str) -> "Session":
        """
        Load a Session from disk by session_id.

        :param session_id: The session ID string.
        :return: Loaded Session instance.
        """
        with open(f"{session_id}.pkl", "rb") as f:
            log_debug(f"Session {session_id} loaded from disk.")
            return pickle.load(f)

    def get_state(self) -> State:
        """
        Get the current session state as a State object.

        :return: The current session state.
        """
        state = State(
            session_id=self.session_id,
            current_step_id=self.current_step.step_id,
            history=self.memory.context,
            flow_state=self.state_machine.get_flow_state(),
        )
        return state

    def set_deferred_tools(self, tools: List[Tool]) -> None:
        """
        Set the list of deferred tools available in this session.

        :param tools: List of Tool instances to set.
        """
        self.deferred_tools.update({tool.name: tool for tool in tools})

    def reset_deferred_tools(self) -> None:
        """
        Reset the list of deferred tools available in this session.

        This is useful to clear any previously fetched tools.
        """
        self.deferred_tools = {}

    def _run_tool(self, tool_name: str, kwargs: Dict[str, Any]) -> Any:
        """
        Run a tool with the given name and arguments.

        :param tool_name: Name of the tool to run.
        :param kwargs: Arguments to pass to the tool.
        :return: Result of the tool execution.
        """
        tool = self.tools.get(tool_name) or self.deferred_tools.get(tool_name)
        if not tool:
            log_error(f"Tool '{tool_name}' not found in session tools.")
            raise ValueError(
                f"Tool '{tool_name}' not found in session tools. Please check the tool name."
            )
        log_debug(f"Running tool: {tool_name} with args: {kwargs}")

        return tool.run(**kwargs)

    def _get_deferred_tools_for_step(self, step: Step) -> List[Tool]:
        """
        Get deferred tools for the given step.

        :param step: The Step instance to populate deferred tools for.
        :return: List of Tool instances that are deferred for this step.
        """
        if not step.deferred_tool_ids:
            return []

        deferred_tools: List[Tool] = []
        deferred_tool_names = step.deferred_tool_ids
        for deferred_tool_name in deferred_tool_names:
            tool = self.tools.get(deferred_tool_name)
            if not tool:
                log_error(
                    f"Deferred tool '{deferred_tool_name}' not found in session tools. Skipping."
                )
                continue

            if isinstance(tool, MCPServer):
                deferred_tools.extend(Tool.from_mcp_server(tool))

        return deferred_tools

    def _get_current_step_tools(self) -> Tuple[Tool, ...]:
        """
        Get the list of tools available in the current step.

        :return: Tuple of Tool instances available in the current step.
        """
        deferred_tools: List[Tool] = self._get_deferred_tools_for_step(self.current_step)
        deferred_tool_names = [tool.name for tool in deferred_tools]
        self.set_deferred_tools(deferred_tools)

        log_debug(f"Adding deferred tools to step: {deferred_tool_names}")
        self.current_step.extend_tools(deferred_tool_names)
        tools = []
        for tool in self.current_step.tool_ids:
            _tool = self.tools.get(tool) or self.deferred_tools.get(tool)
            if not _tool:
                log_error(f"Tool '{tool}' not found in session tools. Skipping.")
                continue

            tools.append(_tool)

        self.current_step.reduce_tools(deferred_tool_names)
        return tuple(tools)

    @property
    def llm(self) -> LLMBase:
        """
        Get the LLM instance for the current step.

        :return: The LLM instance.
        """
        llm_id = self.current_step.llm or "global"
        if llm_id not in self.llm_dict:
            log_error(f"LLM '{llm_id}' not found in session LLMs. Using default LLM.")
        return self.llm_dict.get(llm_id, self.llm_dict["global"])

    def _add_event(
        self, event_type: str, content: str, decision: Optional[Decision] = None
    ) -> None:
        """Add an event to the session history."""
        event_obj = Event(type=event_type, content=content, decision=decision)

        # If we're in a flow, only update flow memory
        if self.state_machine.current_flow and self.state_machine.flow_context:
            flow_memory = self.state_machine.current_flow.get_memory()
            if flow_memory and isinstance(flow_memory, FlowMemoryComponent):
                flow_memory.add_to_context(event_obj)
            # Don't update session memory while in flow
        else:
            # Only update session memory when not in a flow
            self.memory.add(event_obj)

        if self.event_emitter:
            try:
                from ..events import SessionEvent

                sess_event = SessionEvent(
                    session_id=self.session_id,
                    event_type=event_type,
                    data={"content": content},
                    decision=decision,
                )
                # Use create_task but don't await to avoid blocking
                # Add error handling for the task
                task = asyncio.create_task(self.event_emitter.emit(sess_event))
                task.add_done_callback(self._handle_event_emission_error)
            except Exception as exc:  # noqa: BLE001
                log_error(f"Failed to emit event: {exc}")
        log_debug(f"{event_type.title()} added: {content}")

    def _handle_event_emission_error(self, task: asyncio.Task) -> None:
        """Handle errors from event emission tasks."""
        try:
            task.result()  # This will raise any exception that occurred
        except Exception as exc:
            log_error(f"Event emission failed: {exc}")

    def _get_next_decision(
        self, decision_constraints: Optional[DecisionConstraints] = None
    ) -> Decision:
        """
        Get the next decision from the LLM based on the current step and history.

        :param decision_constraints: Optional constraints for the decision.
        :return: The decision made by the LLM.
        """
        _decision_model = self.llm._create_decision_model(
            current_step=self.current_step,
            current_step_tools=self._get_current_step_tools(),
            constraints=decision_constraints,
        )

        # Get memory context - use flow memory if available, otherwise use session memory
        memory_context = self.memory.get_history()
        flow_memory_context = None

        if self.state_machine.current_flow and self.state_machine.flow_context:
            flow_memory = self.state_machine.current_flow.get_memory()
            if flow_memory and isinstance(flow_memory, FlowMemoryComponent):
                flow_memory_context = flow_memory.memory.context

        _decision = self.llm._get_output(
            steps=self.steps,
            current_step=self.current_step,
            tools=self.tools,
            history=flow_memory_context if flow_memory_context else memory_context,
            response_format=_decision_model,
            system_message=self.system_message,
            persona=self.persona,
            max_examples=self.config.max_examples,
            embedding_model=self.embedding_model,
        )

        # Convert to a Decision model
        decision = self.llm._create_decision_from_output(output=_decision)
        log_debug(f"Model decision: {decision}")
        return decision

    def next(
        self,
        user_input: Optional[str] = None,
        no_errors: int = 0,
        next_count: int = 0,
        return_tool: bool = False,
        return_step: bool = False,
        verbose: bool = False,
        decision_constraints: Optional[DecisionConstraints] = None,
    ) -> Response:
        """
        Advance the session to the next step based on user input and LLM decision.

        :param user_input: Optional user input string.
        :param no_errors: Number of consecutive errors encountered.
        :param next_count: Number of times the next function has been called.
        :param return_tool: Whether to return tool results.
        :param return_step: Whether to return step Transitions.
        :param verbose: Whether to print verbose output.
        :param decision_constraints: Optional constraints for the decision model on retry.
        :return: A Response containing the decision and any tool results.
        """
        if no_errors >= self.max_errors:
            raise ValueError(f"Maximum errors reached ({self.max_errors}). Stopping session.")
        if next_count >= self.max_iter:
            if not self.current_step.auto_flow:
                self._add_event(
                    "fallback",
                    (
                        "Maximum iterations reached. Inform the user and based on the "
                        "available context, produce a fallback response."
                    ),
                )
                return self.next(
                    verbose=verbose,
                    decision_constraints=DecisionConstraints(
                        actions=["RESPOND"], fields=["response"]
                    ),
                )
            else:
                raise RecursionError(
                    f"Maximum iterations reached ({self.max_iter}). Stopping session."
                )

        self.reset_deferred_tools()
        log_debug(f"User input received: {user_input}")
        self._add_event("user", user_input) if user_input else None
        log_debug(f"Current step: {self.current_step.step_id}")

        # Check for flow transitions
        self.state_machine.handle_flow_transitions(
            self.current_step.step_id, self.session_id, verbose=verbose
        )

        decision = self._get_next_decision(decision_constraints=decision_constraints)
        log_debug(str(decision))
        log_debug(f"Action decided: {decision.action}")

        # Validate decision
        if decision.action == Action.RESPOND and decision.response is None:
            self._add_event(
                "error",
                "RESPOND action requires a response, but none was provided.",
                decision,
            )
            return self.next(
                no_errors=no_errors + 1,
                next_count=next_count + 1,
                decision_constraints=DecisionConstraints(actions=["RESPOND"], fields=["response"]),
                verbose=verbose,
            )
        if decision.action == Action.MOVE and decision.step_id is None:
            self._add_event(
                "error",
                "MOVE action requires a step_id, but none was provided.",
                decision,
            )
            return self.next(
                no_errors=no_errors + 1,
                next_count=next_count + 1,
                decision_constraints=DecisionConstraints(actions=["MOVE"], fields=["step_id"]),
                verbose=verbose,
            )
        if decision.action == Action.TOOL_CALL and decision.tool_call is None:
            self._add_event(
                "error",
                "TOOL_CALL action requires a tool_call, but none was provided.",
                decision,
            )
            return self.next(
                no_errors=no_errors + 1,
                next_count=next_count + 1,
                decision_constraints=DecisionConstraints(
                    actions=["TOOL_CALL"], fields=["tool_call"]
                ),
                verbose=verbose,
            )

        self._add_step_identifier(self.current_step.get_step_identifier())
        if decision.action == Action.RESPOND:
            self._add_event(self.name, str(decision.response), decision)
            res = Response(decision=decision)
            if verbose:
                pp_response(res)
            return res
        elif decision.action == Action.TOOL_CALL and decision.tool_call:
            _error: Optional[Exception] = None
            tool_results = None
            try:
                tool_name = decision.tool_call.tool_name
                tool_kwargs: dict = decision.tool_call.tool_kwargs.model_dump()
                log_debug(f"Running tool: {tool_name} with args: {tool_kwargs}")
                try:
                    tool_results = self._run_tool(tool_name, tool_kwargs)
                    self._add_event(
                        "tool",
                        f"Tool {tool_name} executed successfully with args {tool_kwargs}.\nResults: {tool_results}",
                        decision,
                    )
                except Exception as e:
                    self._add_event(
                        "tool",
                        f"Running tool {tool_name} with args {tool_kwargs}",
                        decision,
                    )
                    raise e
                log_debug(f"Tool Results: {tool_results}")
            except FallbackError as e:
                _error = e
                self._add_event("fallback", str(e), decision)
            except InvalidArgumentsError as e:
                _error = e
                self._add_event("error", str(e), decision)
            except Exception as e:
                _error = e
                self._add_event("error", str(e), decision)

            res = Response(decision=decision, tool_output=tool_results)
            if verbose:
                pp_response(res)
            if return_tool and _error is None:
                return res
            return self.next(
                no_errors=no_errors + 1 if _error else 0,
                next_count=next_count + 1,
                decision_constraints=(
                    DecisionConstraints(
                        actions=["TOOL_CALL"],
                        fields=["tool_call"],
                        tool_name=decision.tool_call.tool_name,
                    )
                    if (_error and isinstance(_error, InvalidArgumentsError) and decision.tool_call)
                    else None
                ),
                verbose=verbose,
            )
        elif decision.action == Action.MOVE and decision.step_id:
            _error = None
            if self.state_machine.can_transition(
                self.state_machine.current_step_id, decision.step_id
            ):
                # Check if we need to exit current flow before moving
                if self.state_machine.current_flow and self.state_machine.flow_context:
                    _, exits = self.state_machine.get_flow_transitions(
                        self.state_machine.current_step_id
                    )
                    if self.state_machine.current_flow.flow_id in exits:
                        self.state_machine._exit_flow(self.state_machine.current_step_id)

                self.state_machine.move(decision.step_id)
                log_debug(f"Moving to next step: {self.state_machine.current_step_id}")
                self._add_step_identifier(self.current_step.get_step_identifier())

            else:
                allowed = self.state_machine.transitions.get(self.state_machine.current_step_id, [])
                self._add_event(
                    "error",
                    f"Invalid route: {decision.step_id} not in {allowed}",
                    decision,
                )
                _error = ValueError(f"Invalid route: {decision.step_id} not in {allowed}")
            res = Response(decision=decision)
            if verbose:
                pp_response(res)
            if return_step:
                self.state_machine.handle_flow_transitions(
                    self.state_machine.current_step_id, self.session_id, verbose=verbose
                )
                return res
            return self.next(
                no_errors=no_errors + 1 if _error else 0,
                next_count=next_count + 1,
                decision_constraints=(
                    DecisionConstraints(actions=["MOVE"], fields=["step_id"]) if _error else None
                ),
                verbose=verbose,
            )
        elif decision.action == Action.END:
            # Clean up any active flows before ending
            if self.state_machine.current_flow and self.state_machine.flow_context:
                try:
                    self.state_machine.current_flow.cleanup(self.state_machine.flow_context)
                    log_debug(
                        f"Cleaned up flow '{self.state_machine.current_flow.flow_id}' on session end"
                    )
                except Exception as e:
                    log_error(f"Error cleaning up flow on session end: {e}")
                finally:
                    self.state_machine.current_flow = None
                    self.state_machine.flow_context = None

            self._add_event("end", "Session ended.", decision)
            res = Response(decision=decision)
            if verbose:
                pp_response(res)
            return res
        else:
            self._add_event(
                "error",
                f"Unknown action: {decision.action}. Please check the action type.",
                decision,
            )
            return self.next(
                no_errors=no_errors + 1,
                next_count=next_count + 1,
                verbose=verbose,
            )

    def _add_step_identifier(self, step_identifier: StepIdentifier) -> None:
        """
        Add a step identifier to the appropriate memory.

        :param step_identifier: The step identifier to add.
        """
        # If we're in a flow, only update flow memory
        if self.state_machine.current_flow and self.state_machine.flow_context:
            flow_memory = self.state_machine.current_flow.get_memory()
            if flow_memory and isinstance(flow_memory, FlowMemoryComponent):
                flow_memory.add_to_context(step_identifier)
            # Don't update session memory while in flow
        else:
            # Only update session memory when not in a flow
            self.memory.add(step_identifier)

        if self.event_emitter:
            try:
                from ..events import SessionEvent

                sess_event = SessionEvent(
                    session_id=self.session_id,
                    event_type="step",
                    data={"step_id": step_identifier.step_id},
                )
                # Use create_task but add error handling
                task = asyncio.create_task(self.event_emitter.emit(sess_event))
                task.add_done_callback(self._handle_event_emission_error)
            except Exception as exc:  # noqa: BLE001
                log_error(f"Failed to emit step event: {exc}")

        log_debug(f"Step identifier added: {step_identifier.step_id}")


__all__ = ["Session"]