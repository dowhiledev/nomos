"""Session management and runtime logic for Nomos agents."""

import pickle
from typing import List, Optional, TYPE_CHECKING
import uuid

from ..memory.base import Memory
from ..models.agent import (
    Action,
    Constraints,
    Event,
    EventType,
    Response,
    State,
    Input,
)
from .sm import StateMachine

if TYPE_CHECKING:
    from .agent import Agent


class Session:
    """Manages a single agent session, including step IDs, tool calls, and history."""

    def __init__(
        self, agent: "Agent", memory: Memory, state: Optional[State] = None
    ) -> None:
        """
        Initialize a Session.

        :param agent: The Agent instance to create a session for.
        :param memory: Memory instance for the session.
        :param state: Optional initial state for the session.
        """
        self.a = agent
        self.session_id = (
            state.session_id if state else f"{self.a._globals.name}_{str(uuid.uuid4())}"
        )

        # Initialize state machine
        self.sm = StateMachine(agent=self.a, memory=memory)
        self.sm.load(state)

    def save(self) -> None:
        """Save the current session to disk as a pickle file."""
        with open(f"{self.session_id}.pkl", "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: str) -> "Session":
        """Load a session from a pickle file."""
        with open(path, "rb") as f:
            session = pickle.load(f)
        return session

    @property
    def state(self) -> State:
        """
        Get the current session state as a State object.

        :return: The current session state.
        """
        # TODO: Implement get_current_state in StateMachine
        return self.state_machine.get_current_state(self.session_id)

    async def __call__(
        self,
        input: Optional[Input] = None,
        return_at: List[Action] = [Action.RESPOND],
        constraints: Optional[Constraints] = None,
        verbose: bool = False,
        _err: int = 0,
        _count: int = 0,
    ) -> Response:
        if _err >= self.a._globals.max_errors:
            raise ValueError(
                f"Maximum errors reached ({self.a._globals.max_errors}). Stopping session."
            )
        if _count >= self.a._globals.max_iter:
            if self.sm.current.respond:  # TODO: .current should return the Current Step
                # TODO: Implement the emit method in StateMachine
                self.sm.emit(
                    Event(
                        "fallback",
                        (
                            "Maximum iterations reached. Inform the user and based on the "
                            "available context, produce a fallback response."
                        ),
                    )
                )
                return await self(
                    constraints=Constraints(
                        actions=[Action.RESPOND], fields=["response"]
                    ),
                    verbose=verbose,
                )
            raise ValueError(
                f"Maximum iterations reached ({self.a._globals.max_iter}). Stopping session."
            )

        self.sm.emit(Event(EventType.USER, input)) if input else None
        # TODO: Implement the forward method in StateMachine which should handle the flow and step transitions and return a Decision
        _decision = self.sm.forward(constraints)

        # Validating Decisions
        _constraints = None
        if _decision.action == Action.RESPOND and _decision.response is None:
            self.sm.emit(
                Event(
                    EventType.ERROR,
                    "RESPOND action requires a response, but none was provided.",
                    _decision,
                )
            )
            _constraints = Constraints(actions=["RESPOND"], fields=["response"])
        elif _decision.action == Action.MOVE and _decision.step_id is None:
            self.sm.emit(
                Event(
                    EventType.ERROR,
                    "MOVE action requires a step_id, but none was provided.",
                    _decision,
                )
            )
            _constraints = Constraints(actions=["MOVE"], fields=["step_id"])
        elif _decision.action == Action.TOOL_CALL and _decision.tool_call is None:
            self.sm.emit(
                Event(
                    EventType.ERROR,
                    "TOOL_CALL action requires a tool_call, but none was provided.",
                    _decision,
                )
            )
            _constraints = Constraints(actions=["TOOL_CALL"], fields=["tool_call"])
        if _constraints:
            return await self(
                constraints=_constraints,
                verbose=verbose,
                _err=_err + 1,
                _count=_count + 1,
            )

        # Handle Decisions
        if _decision.action == Action.RESPOND:
            self.sm.emit(Event(EventType.AGENT, _decision.response, _decision))
        elif _decision.action == Action.TOOL_CALL and _decision.tool_call:
            self.sm.emit(Event(EventType.TOOL_CALL, _decision.tool_call, _decision))
        elif _decision.action == Action.MOVE and _decision.step_id:
            self.sm.emit(Event(EventType.MOVE, _decision.step_id, _decision))
        elif _decision.action == Action.END:
            self.sm.emit(Event(EventType.END, _decision.response, _decision))
        else:
            self.sm.emit(
                Event(
                    EventType.ERROR,
                    f"Unknown action: {_decision.action}. Please check the action type.",
                    _decision,
                )
            )
            _constraints = Constraints(
                actions=["RESPOND", "MOVE", "TOOL_CALL", "END"],
                fields=["response", "step_id", "tool_call"],
            )

        if _decision.action in return_at:
            return Response.from_decision(_decision)
        return await self(
            constraints=_constraints,
            verbose=verbose,
            return_at=return_at,
            _err=_err + 1 if _constraints else 0,
            _count=_count + 1,
        )


__all__ = ["Session"]
