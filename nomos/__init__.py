"""
Nomos is an open-source, configurable multi-step agent framework for building advanced LLM-powered assistants.

Define your agent's persona, tools, and step-by-step flows in Python or YAML—perfect for conversational, workflow, and automation use cases.
"""

from .client import AuthConfig, NomosClient, NomosClientSync
from .config import AgentConfig, ServerConfig
from .core import Agent
from .models.agent import Action, Route, State, Step, StepIdentifier, Summary
from .models.flow import Flow, FlowComponent, FlowConfig, FlowContext, FlowManager
from .server import run_server
from .state_machine import StateMachine
from .testing import smart_assert
from .testing.e2e import Scenario, ScenarioRunner

__version__ = "0.3.7"
__author__ = "DoWhile"

__all__ = [
    "Agent",
    "AgentConfig",
    "ServerConfig",
    "Action",
    "Step",
    "StepIdentifier",
    "Summary",
    "Route",
    "Flow",
    "FlowManager",
    "FlowContext",
    "FlowComponent",
    "FlowConfig",
    "run_server",
    "State",
    "smart_assert",
    "ScenarioRunner",
    "Scenario",
    "StateMachine",
    # Client classes
    "NomosClient",
    "NomosClientSync",
    "AuthConfig",
]
