from ..memory.base import Memory
from ..models.agent import Constraints, Decision, Event, State
from .flow import FlowManager
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .agent import Agent


class StateMachine:
    def __init__(self, agent: "Agent", memory: Memory) -> None:
        self.a = agent
        self.mem = memory
        self.fm = FlowManager(flows=self.a.flows)

    def load(self, state: Optional[State] = None) -> None:
        pass

    def get_current_state(self, session_id: str) -> State:
        pass

    def emit(self, event: Event) -> None:
        self.mem.add(event)

    def forward(self, constraints: Optional[Constraints] = None) -> Decision:
        pass