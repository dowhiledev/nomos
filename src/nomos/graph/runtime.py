"""Runtime graph types and YAML loading for agent definitions.

This module provides:
- Step: A node with tools and LLM configuration
- Transition: An edge with routing condition
- Graph: A high-level builder supporting both programmatic and YAML-based definition

The Graph class can be constructed in Python or loaded from YAML configuration,
making it easy to manage agent definitions externally while keeping tools in code.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

import yaml
from pydantic import BaseModel, Field, PrivateAttr
from pydantic.config import ConfigDict

from .spec import AgentSpec, NodeSpec, EdgeSpec, compile_agent


class Step(BaseModel):
    """A node in the graph with optional LLM and tool configuration.
    
    Represents a decision or action point in the agent's workflow. Steps can
    have node-specific LLM overrides, tool availability restrictions, and memory
    configuration.
    
    Attributes:
        id: Unique step identifier.
        prompt: Optional instruction for the LLM at this step.
        llm: Optional LLM provider override for this step.
        tools: Optional list of available tool callables (decorated functions).
            Can be Python functions decorated with @tool or plain callables.
        memory: Optional memory identifier for retrieving context at this step.
    
    Example:
        >>> step = Step(
        ...     id="analyze",
        ...     prompt="Analyze the requirements",
        ...     tools=[my_analyze_function]
        ... )
    """

    id: str = Field(description="Unique step identifier")
    prompt: Optional[str] = Field(
        default=None,
        description="LLM instruction prompt"
    )
    llm: Optional[str] = Field(
        default=None,
        description="LLM provider override"
    )
    tools: Optional[List[object]] = Field(
        default=None,
        description="Available tool callables"
    )
    memory: Optional[str] = Field(
        default=None,
        description="Memory context identifier"
    )


class Transition(BaseModel):
    """A routing edge between steps.
    
    Represents a possible transition from one step to another. The "when"
    condition is a natural-language description shown to the LLM.
    
    Attributes:
        from_id: Source step ID.
        to_id: Target step ID.
        when: Natural-language condition for this transition.
    
    Example:
        >>> trans = Transition(
        ...     from_id="analyze",
        ...     to_id="implement",
        ...     when="Requirements are clear"
        ... )
    """

    from_id: str = Field(description="Source step ID")
    to_id: str = Field(description="Target step ID")
    when: Optional[str] = Field(
        default=None,
        description="Transition condition"
    )


class Graph(BaseModel):
    """High-level graph builder supporting Python and YAML definition.
    
    Provides a fluent API for constructing agent graphs, with support for:
    - Programmatic building via node() and edge()
    - YAML loading via from_yaml()
    - Compilation to AgentSpec for the orchestrator
    
    Attributes:
        name: Graph name.
        llm: Optional default LLM provider for all steps.
        memory: Optional memory configuration identifier.
    
    Example:
        >>> graph = Graph(name="assistant")
        >>> graph.node(Step(id="start", prompt="Start"))
        >>> graph.node(Step(id="end"))
        >>> graph.edge(Transition(from_id="start", to_id="end"))
        >>> spec = graph.compile()
    """

    name: str = Field(description="Graph name")
    llm: Optional[str] = Field(
        default=None,
        description="Default LLM provider"
    )
    memory: Optional[str] = Field(
        default=None,
        description="Memory configuration"
    )
    _nodes: List[Step] = PrivateAttr(default_factory=list)
    _edges: List[Transition] = PrivateAttr(default_factory=list)
    _start: Optional[str] = PrivateAttr(default=None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def node(self, step: Step) -> "Graph":
        """Add a step to the graph.
        
        The first step added becomes the start node if not already set.
        
        Args:
            step: Step object to add.
        
        Returns:
            Self for method chaining.
        """
        if self._start is None:
            self._start = step.id
        self._nodes.append(step)
        return self

    def add(self, *items: Union[Step, Transition]) -> "Graph":
        """Add one or more steps and/or transitions.
        
        Handles mixed Step and Transition objects in a single call.
        The first Step added becomes the start if not already set.
        
        Args:
            *items: Variable number of Step and/or Transition objects.
        
        Returns:
            Self for method chaining.
        """
        for item in items:
            if isinstance(item, Step):
                if self._start is None:
                    self._start = item.id
                self._nodes.append(item)
            elif isinstance(item, Transition):
                self._edges.append(item)
        return self

    def edge(self, e: Transition) -> "Graph":
        """Add a transition (routing edge).
        
        Args:
            e: Transition object.
        
        Returns:
            Self for method chaining.
        """
        self._edges.append(e)
        return self

    @classmethod
    def from_yaml(cls, yaml_path: Union[str, Path]) -> "Graph":
        """Load a graph from a YAML configuration file.
        
        The YAML should define steps with their prompts, tools, and transitions.
        Tools are referenced by name (must be registered separately in Python).
        
        YAML Structure:
            name: graph name
            entry_point: starting step id
            llm:
                provider: provider name
            memory: memory config
            steps:
                step_id:
                    prompt: instruction text
                    tools: [tool1, tool2]
                    transitions:
                        - to: target_step_id
                          when: condition text
        
        Args:
            yaml_path: Path to YAML configuration file.
        
        Returns:
            Loaded Graph instance.
        
        Raises:
            FileNotFoundError: If YAML file doesn't exist.
            KeyError: If YAML structure is invalid.
        
        Example:
            >>> graph = Graph.from_yaml("agent.yaml")
            >>> spec = graph.compile()
        """
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")

        with open(path, "r") as f:
            config = yaml.safe_load(f)

        # Create the graph instance
        graph = cls(
            name=config["name"],
            llm=config.get("llm", {}).get("provider"),
            memory=config.get("memory"),
        )

        # Set the entry point
        if "entry_point" in config:
            graph._start = config["entry_point"]

        # Process steps
        steps_config = config.get("steps", {})
        for step_id, step_data in steps_config.items():
            # Create the step
            step = Step(
                id=step_id,
                prompt=step_data.get("prompt"),
                llm=step_data.get("llm"),
                tools=step_data.get("tools", []),
                memory=step_data.get("memory"),
            )
            graph._nodes.append(step)

            # Set start if not already set
            if graph._start is None:
                graph._start = step_id

            # Process transitions from this step
            transitions = step_data.get("transitions", [])
            for trans_data in transitions:
                transition = Transition(
                    from_id=step_id, to_id=trans_data["to"], when=trans_data.get("when")
                )
                graph._edges.append(transition)

        return graph

    def compile(self) -> AgentSpec:
        """Compile the graph into an AgentSpec.
        
        Converts Steps and Transitions to NodeSpec and EdgeSpec respectively,
        then validates the resulting specification.
        
        Returns:
            Compiled AgentSpec ready for the orchestrator.
        
        Raises:
            ValueError: If no start node is set or graph is invalid.
        
        Example:
            >>> graph = Graph(name="bot")
            >>> graph.node(Step(id="start"))
            >>> spec = graph.compile()
        """
        if not self._start:
            raise ValueError("graph has no start node; add at least one node")
        spec = AgentSpec(
            name=self.name,
            start=self._start,
            nodes=[
                NodeSpec(id=n.id, prompt=n.prompt, tools=n.tools) for n in self._nodes
            ],
            edges=[
                EdgeSpec(from_id=e.from_id, to_id=e.to_id, condition=e.when)
                for e in self._edges
            ],
        )
        return compile_agent(spec)



__all__ = ["Graph", "Step", "Transition"]
