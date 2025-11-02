from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union, Dict, Any

import yaml
from pydantic import BaseModel
from pydantic.config import ConfigDict

from .spec import AgentSpec, NodeSpec, EdgeSpec, compile_agent


class Step(BaseModel):
    id: str
    prompt: Optional[str] = None
    llm: Optional[str] = None
    tools: Optional[List[object]] = None  # user-provided callables (decorated or plain)
    memory: Optional[str] = None


class Transition(BaseModel):
    from_id: str
    to_id: str
    when: Optional[str] = None


class Graph(BaseModel):
    name: str
    llm: Optional[str] = None
    memory: Optional[str] = None
    _nodes: List[Step] = []  # type: ignore[var-annotated]
    _edges: List[Transition] = []  # type: ignore[var-annotated]
    _start: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def node(self, step: Step) -> "Graph":
        if self._start is None:
            self._start = step.id
        self._nodes.append(step)
        return self

    def add(self, *items: Union[Step, Transition]) -> "Graph":
        for item in items:
            if isinstance(item, Step):
                if self._start is None:
                    self._start = item.id
                self._nodes.append(item)
            elif isinstance(item, Transition):
                self._edges.append(item)
        return self

    def edge(self, e: Transition) -> "Graph":
        self._edges.append(e)
        return self

    @classmethod
    def from_yaml(cls, yaml_path: Union[str, Path]) -> "Graph":
        """Load a graph from a YAML configuration file.
        
        Args:
            yaml_path: Path to the YAML configuration file
            
        Returns:
            Graph instance with steps and transitions loaded from YAML
        """
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")
        
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Create the graph instance
        graph = cls(
            name=config["name"],
            llm=config.get("llm", {}).get("provider"),
            memory=config.get("memory")
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
                memory=step_data.get("memory")
            )
            graph._nodes.append(step)
            
            # Set start if not already set
            if graph._start is None:
                graph._start = step_id
            
            # Process transitions from this step
            transitions = step_data.get("transitions", [])
            for trans_data in transitions:
                transition = Transition(
                    from_id=step_id,
                    to_id=trans_data["to"],
                    when=trans_data.get("when")
                )
                graph._edges.append(transition)
        
        return graph

    def compile(self) -> AgentSpec:
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
