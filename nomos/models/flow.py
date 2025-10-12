 """Flow construct for encapsulating sets of steps with shared context and components."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .agent import Event, Step, Summary


class FlowContext(BaseModel):
    """Context passed between flow components."""

    flow_id: str
    entry_step: str
    previous_context: Optional[List[Union[Event, Summary]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)  # noqa: ANN401


class FlowComponent(ABC):
    """Base class for flow-specific components (memory, tools, etc.)."""

    @abstractmethod
    def enter(self, context: FlowContext) -> None:
        """Called when flow is entered."""
        pass

    @abstractmethod
    def exit(self, context: FlowContext) -> Any:  # noqa: ANN401
        """Called when flow is exited. Returns data to pass to next flow."""
        pass

    @abstractmethod
    def cleanup(self, context: FlowContext) -> None:  # noqa: ANN401
        """Called for cleanup when flow terminates."""
        pass


class FlowConfig(BaseModel):
    """Configuration for a flow."""

    flow_id: str = Field(
        ...,
        description="Unique identifier for the flow",
        validation_alias="id",
        serialization_alias="id",
    )
    enters: List[str] = Field(..., description="Step IDs that can enter this flow")
    exits: List[str] = Field(..., description="Step IDs that can exit this flow")
    description: Optional[str] = Field(None, validation_alias="desc", serialization_alias="desc")
    components: Dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Components to be used in the flow, e.g., memory, tools",
    )

    model_config = {"populate_by_name": True}


class Flow:
    """
    A flow encapsulates a set of steps with shared context and components.

    Flows can have multiple entry and exit points, and manage flow-specific
    resources like memory, tools, and other components.
    """

    def __init__(
        self,
        config: FlowConfig,
        steps: List[Step],
        component_registry: Optional[Dict[str, Callable[..., FlowComponent]]] = None,
    ) -> None:
        """
        Initialize the flow with configuration and steps.

        :param config: Flow configuration containing entry/exit steps and components.
        :param steps: List of steps that belong to this flow.
        :param component_registry: Optional registry of components to initialize.
        """
        self.config = config
        self.flow_id = config.flow_id
        self.entry_steps = set(config.enters)
        self.exit_steps = set(config.exits)
        self.steps = {step.step_id: step for step in steps}
        self.components: Dict[str, FlowComponent] = {}
        self.active_contexts: Dict[str, FlowContext] = {}

        # Initialize components
        component_registry = component_registry or self._get_default_component_registry()
        for component_name, component_config in config.components.items():
            if component_name in component_registry:
                self.components[component_name] = component_registry[component_name](
                    **component_config
                )

    def _get_default_component_registry(
        self,
    ) -> Dict[str, Callable[..., FlowComponent]]:
        """Get default component registry."""
        from ..memory.flow import FlowMemoryComponent

        return {
            "memory": FlowMemoryComponent,
            # Add other default components here
        }

    def can_enter(self, step_id: str) -> bool:
        """Check if a step can enter this flow."""
        return step_id in self.entry_steps

    def can_exit(self, step_id: str) -> bool:
        """Check if a step can exit this flow."""
        return step_id in self.exit_steps

    def contains_step(self, step_id: str) -> bool:
        """Check if a step belongs to this flow."""
        return step_id in self.steps

    def enter(
        self,
        entry_step: str,
        previous_context: Optional[List[Union[Event, Summary]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FlowContext:
        """Enter the flow at a specific step."""
        if not self.can_enter(entry_step):
            raise ValueError(
                f"Step '{entry_step}' is not a valid entry point for flow '{self.flow_id}'"
            )

        context = FlowContext(
            flow_id=self.flow_id,
            entry_step=entry_step,
            previous_context=previous_context,
            metadata=metadata or {},
        )

        # Store active context
        context_key = f"{self.flow_id}:{entry_step}"
        self.active_contexts[context_key] = context

        # Initialize all components
        for component in self.components.values():
            component.enter(context)

        return context

    def exit(self, exit_step: str, context: FlowContext) -> Dict[str, Any]:
        """Exit the flow at a specific step."""
        if not self.can_exit(exit_step):
            raise ValueError(
                f"Step '{exit_step}' is not a valid exit point for flow '{self.flow_id}'"
            )

        # Collect exit data from all components
        exit_data = {}
        for name, component in self.components.items():
            exit_data[name] = component.exit(context)

        # Clean up context
        context_key = f"{context.flow_id}:{context.entry_step}"
        if context_key in self.active_contexts:
            del self.active_contexts[context_key]

        return exit_data

    def cleanup(self, context: FlowContext) -> None:
        """Clean up flow resources."""
        for component in self.components.values():
            component.cleanup(context)

        # Remove from active contexts
        context_key = f"{context.flow_id}:{context.entry_step}"
        if context_key in self.active_contexts:
            del self.active_contexts[context_key]

    def get_component(self, name: str) -> Optional[FlowComponent]:
        """Get a flow component by name."""
        return self.components.get(name)

    def get_memory(self) -> Optional[FlowComponent]:
        """Convenience method to get flow memory."""
        return self.get_component("memory")


class FlowManager:
    """Manages multiple flows and their interactions."""

    def __init__(self) -> None:
        """Initialize the flow manager."""
        self.flows: Dict[str, Flow] = {}
        self.step_to_flows: Dict[str, List[str]] = {}

    def register_flow(self, flow: Flow) -> None:
        """Register a flow with the manager."""
        self.flows[flow.flow_id] = flow

        # Update step-to-flows mapping
        for step_id in flow.steps.keys():
            if step_id not in self.step_to_flows:
                self.step_to_flows[step_id] = []
            self.step_to_flows[step_id].append(flow.flow_id)

    def get_flows_for_step(self, step_id: str) -> List[Flow]:
        """Get all flows that contain a specific step."""
        flow_ids = self.step_to_flows.get(step_id, [])
        return [self.flows[flow_id] for flow_id in flow_ids]

    def find_entry_flows(self, step_id: str) -> List[Flow]:
        """Find flows that can be entered at this step."""
        return [flow for flow in self.flows.values() if flow.can_enter(step_id)]

    def find_exit_flows(self, step_id: str) -> List[Flow]:
        """Find flows that can be exited at this step."""
        return [flow for flow in self.flows.values() if flow.can_exit(step_id)]

    def transition_between_flows(
        self, from_flow: Flow, to_flow: Flow, transition_step: str, context: FlowContext
    ) -> FlowContext:
        """Handle transition between flows."""
        # Exit current flow
        exit_data = from_flow.exit(transition_step, context)

        # Enter new flow with data from previous flow
        new_context = to_flow.enter(
            transition_step,
            previous_context=context.previous_context,
            metadata={**context.metadata, "previous_flow_data": exit_data},
        )

        return new_context


__all__ = ["FlowContext", "FlowComponent", "FlowConfig", "Flow", "FlowManager"]
