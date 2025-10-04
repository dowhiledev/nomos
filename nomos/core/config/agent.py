"""Agent and logging configuration classes."""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings

from ...llms import LLMBase, LLMConfig
from ...memory import MemoryConfig
from ...models.agent import Step
from ...models.flow import FlowConfig
from .server import ServerConfig
from .tools import ToolsConfig

# Constants
DEFAULT_MAX_ERRORS = 3
DEFAULT_MAX_ITER = 10
DEFAULT_MAX_EXAMPLES = 5
DEFAULT_THRESHOLD = 0.5


class LoggingHandler(BaseModel):
    """Configuration for a logging handler.

    Attributes:
        type: Type of the logging handler (e.g., 'stderr', 'file').
        level: Logging level.
        format: Log message format.
    """
    type: str = Field(..., description="Type of the logging handler")
    level: str = Field(..., description="Logging level")
    format: str = Field("{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", description="Log message format")

    def __str__(self) -> str:
        return f"LoggingHandler(type={self.type}, level={self.level})"


class LoggingConfig(BaseModel):
    """Configuration for logging.

    Attributes:
        enable: Whether logging is enabled.
        handlers: List of logging handlers.
    """
    enable: bool = Field(..., description="Whether logging is enabled")
    handlers: List[LoggingHandler] = Field(default_factory=list, description="List of logging handlers")

    def __str__(self) -> str:
        return f"LoggingConfig(enable={self.enable}, handlers={len(self.handlers)})"


class AgentConfig(BaseSettings):
    """Configuration for the agent, including model settings and flow steps.

    Attributes:
        name: Name of the agent.
        persona: Optional persona of the agent.
        steps: List of steps in the flow.
        start_step_id: ID of the starting step.
        system_message: Optional system message.
        show_steps_desc: Whether to show step descriptions.
        max_errors: Maximum number of errors allowed.
        max_iter: Maximum number of iterations allowed.
        max_examples: Maximum number of examples for decision-making.
        threshold: Minimum similarity score for examples.
        llm: Optional LLM configuration(s).
        embedding_model: Optional embedding model configuration.
        memory: Optional memory configuration.
        flows: Optional flow configurations.
        schemas: Optional schema definitions (name to file path).
        server: Server configuration.
        tools: Tools configuration.
        logging: Optional logging configuration.
    """
    name: str = Field(..., description="Name of the agent")
    persona: Optional[str] = Field(None, description="Persona of the agent")
    steps: List[Step] = Field(..., description="List of steps in the flow")
    start_step_id: str = Field(..., description="ID of the starting step")
    system_message: Optional[str] = Field(None, description="System message for the agent")
    show_steps_desc: bool = Field(False, description="Flag to show step descriptions")
    max_errors: int = Field(DEFAULT_MAX_ERRORS, description="Maximum number of errors allowed")
    max_iter: int = Field(DEFAULT_MAX_ITER, description="Maximum number of iterations allowed")
    max_examples: int = Field(DEFAULT_MAX_EXAMPLES, description="Maximum number of examples for decision-making")
    threshold: float = Field(DEFAULT_THRESHOLD, description="Minimum similarity score for examples")
    llm: Optional[Union[LLMConfig, Dict[str, LLMConfig]]] = Field(None, description="LLM configuration(s)")
    embedding_model: Optional[LLMConfig] = Field(None, description="Embedding model configuration")
    memory: Optional[MemoryConfig] = Field(None, description="Memory configuration")
    flows: Optional[List[FlowConfig]] = Field(None, description="Flow configurations")
    schemas: Optional[Dict[str, str]] = Field(None, description="Schema definitions (name to file path)")
    server: ServerConfig = Field(default_factory=ServerConfig, description="Server configuration")
    tools: ToolsConfig = Field(default_factory=ToolsConfig, description="Tools configuration")
    logging: Optional[LoggingConfig] = Field(None, description="Logging configuration")

    @classmethod
    def from_yaml(cls, file_path: str) -> "AgentConfig":
        """Load configuration from a YAML file.

        Args:
            file_path: Path to the YAML file.

        Returns:
            AgentConfig: Loaded configuration instance.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValidationError: If the YAML content is invalid.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"YAML file not found: {file_path}")

        def _expand_env_vars(obj):
            """Recursively expand environment variables in nested structures."""
            if isinstance(obj, dict):
                return {k: _expand_env_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_expand_env_vars(item) for item in obj]
            elif isinstance(obj, str) and obj.startswith("$"):
                env_var = obj[1:]
                return os.getenv(env_var, obj)
            else:
                return obj

        with open(file_path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        data = _expand_env_vars(data)
        try:
            config = cls(**data)
        except ValidationError as e:
            raise ValidationError(f"Invalid configuration in {file_path}: {e}")

        if config.schemas:
            from ...utils.schema_loader import schema_registry
            base_path = os.path.dirname(file_path)
            for schema_name, schema_path in config.schemas.items():
                schema_registry.load_schema(schema_name, schema_path, base_path)

        return config

    def to_yaml(self, file_path: str) -> None:
        """Save configuration to a YAML file.

        Args:
            file_path: Path to the YAML file.
        """
        with open(file_path, "w", encoding="utf-8") as file:
            yaml.dump(self.model_dump(mode="json"), file, sort_keys=False)

    def get_llm(self) -> Optional[Dict[str, LLMBase]]:
        """Get LLM instances based on the configuration.

        Returns:
            Dict of LLM instances keyed by ID, or None if not configured.
        """
        if not self.llm:
            return None
        if isinstance(self.llm, dict):
            return {llm_id: llm_config.get_llm() for llm_id, llm_config in self.llm.items()}
        return {"global": self.llm.get_llm()}

    def get_embedding_model(self) -> Optional[LLMBase]:
        """Get the embedding model instance.

        Returns:
            LLMBase instance, or None if not configured.
        """
        return self.embedding_model.get_llm() if self.embedding_model else None

    def __str__(self) -> str:
        return f"AgentConfig(name={self.name}, start_step_id={self.start_step_id})"


__all__ = ["LoggingHandler", "LoggingConfig", "AgentConfig"]