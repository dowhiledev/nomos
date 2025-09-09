"""AgentConfig class for managing agent configurations."""

from __future__ import annotations

import importlib
import importlib.util
import os
from enum import Enum
from typing import Callable, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from .llms import LLMBase, LLMConfig
from .memory import MemoryConfig
from .models.agent import Step
from .models.flow import FlowConfig
from .models.tool import ToolDef, ToolWrapper
from .utils.utils import convert_camelcase_to_snakecase


class SessionStoreType(str, Enum):
    MEMORY = "memory"
    PRODUCTION = "production"


class SessionConfig(BaseModel):
    store_type: SessionStoreType = SessionStoreType.MEMORY
    default_ttl: int = Field(3600, description="Default session TTL")
    cache_ttl: int = Field(3600, description="Cache TTL for production store")
    database_url: Optional[str] = None
    redis_url: Optional[str] = None
    kafka_brokers: Optional[str] = None
    kafka_topic: str = "session_events"
    events_enabled: bool = False

    @classmethod
    def from_env(cls) -> "SessionConfig":
        import os

        return cls(
            store_type=SessionStoreType(os.getenv("SESSION_STORE", "memory")),
            default_ttl=int(os.getenv("SESSION_DEFAULT_TTL", "3600")),
            cache_ttl=int(os.getenv("SESSION_CACHE_TTL", "3600")),
            database_url=os.getenv("DATABASE_URL"),
            redis_url=os.getenv("REDIS_URL"),
            kafka_brokers=os.getenv("KAFKA_BROKERS"),
            kafka_topic=os.getenv("KAFKA_TOPIC", "session_events"),
            events_enabled=os.getenv("SESSION_EVENTS", "false").lower() == "true",
        )


class ServerSecurity(BaseModel):
    """Security configuration for the FastAPI server."""

    # CORS configuration
    allowed_origins: List[str] = Field(["*"], description="List of allowed origins for CORS")

    # Authentication configuration
    enable_auth: bool = False  # Flag to enable authentication
    auth_type: Optional[Literal["jwt", "api_key"]] = None  # Type of authentication to use
    jwt_secret_key: Optional[str] = None  # Secret key for JWT authentication
    api_key_url: Optional[str] = None  # URL for API key validation

    # Rate limiting configuration
    enable_rate_limiting: bool = False  # Flag to enable rate limiting
    redis_url: Optional[str] = None  # Redis URL for rate limiting
    rate_limit_times: Optional[int] = None  # Number of allowed requests per time period
    rate_limit_seconds: Optional[int] = None  # Time period for rate limiting in seconds

    # CSRF protection configuration
    enable_csrf_protection: bool = False  # Flag to enable CSRF protection
    csrf_secret_key: Optional[str] = None  # Secret key for CSRF protection

    # Development/Testing configuration
    enable_token_endpoint: bool = (
        False  # Flag to enable JWT token generation endpoint (dev/test only)
    )


class ServerConfig(BaseModel):
    """Configuration for the FastAPI server."""

    port: int = 8000
    host: str = "0.0.0.0"
    workers: int = 1
    security: ServerSecurity = ServerSecurity()
    session: SessionConfig = SessionConfig()


class ExternalTool(BaseModel):
    """Configuration for an external tool."""

    tag: str  # Tag of the external tool (eg - @pkg/itertools.combinations, @crewai/FileReadTool, @langchain/BingSearchAPIWrapper)
    name: Optional[str] = (
        None  # snake case name of the tool (eg - combinations, file_read_tool, bing_search)
    )
    kwargs: Optional[Dict[str, Union[str, int, float]]] = (
        None  # Optional keyword arguments for the Tool initialization
    )
    map: Optional[Dict[str, str]] = (
        None  # Optional mapping of method names to API endpoints (for API tools)
    )

    def get_tool_wrapper(self) -> ToolWrapper:
        """
        Get the ToolWrapper instance for the external tool.

        :return: ToolWrapper instance.
        """
        tool_type, tool_name = self.tag.split("/", 1)
        tool_type = tool_type.replace("@", "")
        if tool_type == "mcp" and not self.name:
            raise ValueError("For MCP tools, the 'name' field is required.")
        assert not (tool_type == "api" and not self.map and not self.name), (
            "For Direct API tools, the 'name' field is required."
        )
        name = (
            self.name
            or ("Multi-Endpoint API Tool" if self.map else None)
            or convert_camelcase_to_snakecase(tool_name.split(".")[-1])
        )
        assert tool_type in [
            "pkg",
            "crewai",
            "langchain",
            "mcp",
            "api",
        ], (
            f"Unsupported tool type: {tool_type}. Supported types are 'pkg', 'crewai', 'mcp', 'langchain', and 'api'."
        )
        return ToolWrapper(
            name=name,
            tool_type=tool_type,
            tool_identifier=tool_name,
            kwargs=self.kwargs,
            map=self.map,
        )


class ToolsConfig(BaseModel):
    """Configuration for tools used by the agent."""

    tool_files: List[str] = Field(
        default_factory=list, validation_alias="files", serialization_alias="files"
    )
    external_tools: Optional[List[ExternalTool]] = Field(
        None, validation_alias="ext", serialization_alias="ext"
    )  # List of external tools
    tool_defs: Optional[Dict[str, ToolDef]] = Field(
        None, validation_alias="defs", serialization_alias="defs"
    )

    model_config = {"populate_by_name": True}

    def get_tools(self) -> List[Union[Callable, ToolWrapper]]:
        """
        Load and return the tools based on the configuration.

        :return: List of tool functions.
        """
        tools_list: List = []
        # Load Tools for python files
        for tool_file in self.tool_files:
            try:
                # Handle both file paths and module names
                if tool_file.endswith(".py"):
                    # It's a file path
                    if not os.path.exists(tool_file):
                        raise FileNotFoundError(f"Tool file '{tool_file}' does not exist.")

                    # Load module from file path
                    spec = importlib.util.spec_from_file_location("tool_module", tool_file)
                    if spec is None or spec.loader is None:
                        raise ImportError(f"Could not load module from '{tool_file}'")
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                else:
                    # It's a module name, try to import it directly
                    module = importlib.import_module(tool_file)

                # Extract tools from the module
                tools = module.tools if hasattr(module, "tools") else []
                tools_list.extend(tools)

            except (ImportError, FileNotFoundError, AttributeError) as e:
                raise ImportError(f"Failed to load tools from '{tool_file}': {e}")

        # Load external tools
        for external_tool in self.external_tools or []:
            try:
                tool_wrapper = external_tool.get_tool_wrapper()
                tools_list.append(tool_wrapper)
            except ValueError as e:
                raise ValueError(f"Failed to load external tool '{external_tool.tag}': {e}")

        return tools_list


class LoggingHandler(BaseModel):
    """Configuration for a logging handler."""

    type: str  # Type of the logging handler (e.g., 'stderr', 'file')
    level: str
    format: str = "{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}"


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    enable: bool
    handlers: List[LoggingHandler] = []


class AgentConfig(BaseSettings):
    """
    Configuration for the agent, including model settings and flow steps.

    Attributes:
        name (str): Name of the agent.
        persona (Optional[str]): Persona of the agent. Recommended to use a default persona.
        steps (List[Step]): List of steps in the flow.
        start_step_id (str): ID of the starting step.
        tool_arg_descriptions (Dict[str, Dict[str, str]]): Descriptions for tool arguments.
        system_message (Optional[str]): System message for the agent. Default system message will be used if not provided.
        show_steps_desc (bool): Flag to show step descriptions.
        max_errors (int): Maximum number of errors allowed.
        max_examples (int): Maximum number of examples to use in decision-making.
        threshold (float): Minimum similarity score to include an example.
        max_iter (int): Maximum number of iterations allowed.
        llm (Optional[LLMConfig]): Optional LLM configuration.
        embedding_model (Optional[LLMConfig]): Optional embedding model configuration.
        memory (Optional[MemoryConfig]): Optional memory configuration.
        flows (Optional[List[FlowConfig]]): Optional flow configurations.
        schemas (Optional[Dict[str, str]]): Optional schema definitions mapping names to file paths.
        server (ServerConfig): Configuration for the FastAPI server.
        tools (ToolsConfig): Configuration for tools.
        logging (Optional[LoggingConfig]): Optional logging configuration.
    Methods:
        from_yaml(file_path: str) -> "AgentConfig": Load configuration from a YAML file.
        to_yaml(file_path: str) -> None: Save configuration to a YAML file.
    """

    name: str
    persona: Optional[str] = None  # Recommended to use a default persona
    steps: List[Step]
    start_step_id: str
    system_message: Optional[str] = None  # Default system message will be used if not provided
    show_steps_desc: bool = False
    max_errors: int = 3
    max_iter: int = 10
    max_examples: int = 5  # Maximum number of examples to use in decision-making
    threshold: float = 0.5  # Minimum similarity score to include an example

    llm: Optional[LLMConfig | Dict[str, LLMConfig]] = None  # Optional LLM configuration
    embedding_model: Optional[LLMConfig] = None  # Optional embedding model configuration
    memory: Optional[MemoryConfig] = None  # Optional memory configuration
    flows: Optional[List[FlowConfig]] = None  # Optional flow configurations
    schemas: Optional[Dict[str, str]] = (
        None  # Optional schema definitions mapping names to file paths
    )

    server: ServerConfig = ServerConfig()  # Configuration for the FastAPI server
    tools: ToolsConfig = ToolsConfig()  # Configuration for tools

    logging: Optional[LoggingConfig] = None  # Optional logging configuration

    @classmethod
    def from_yaml(cls, file_path: str) -> "AgentConfig":
        """
        Load configuration from a YAML file.

        :param file_path: Path to the YAML file.
        :return: An instance of AgentConfig with the loaded data.
        """
        import yaml

        def expand_env_vars(obj):
            """Recursively expand environment variables in nested dictionaries and lists."""
            if isinstance(obj, dict):
                return {k: expand_env_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [expand_env_vars(item) for item in obj]
            elif isinstance(obj, str) and obj.startswith("$"):
                # Extract environment variable name and get its value
                env_var = obj[1:]  # Remove the $ prefix
                return os.getenv(env_var, obj)  # Return original value if env var not found
            else:
                return obj

        with open(file_path, "r") as file:
            data = yaml.safe_load(file)

        # Expand environment variables in the entire configuration
        data = expand_env_vars(data)

        config = cls(**data)

        # Load schemas if defined
        if config.schemas:
            from .utils.schema_loader import schema_registry

            base_path = os.path.dirname(file_path)
            for schema_name, schema_path in config.schemas.items():
                schema_registry.load_schema(schema_name, schema_path, base_path)

        return config

    def to_yaml(self, file_path: str) -> None:
        """
        Save configuration to a YAML file.

        :param file_path: Path to the YAML file.
        """
        import yaml

        with open(file_path, "w") as file:
            yaml.dump(self.model_dump(mode="json"), file, sort_keys=False)

    def get_llm(self) -> Optional[Dict[str, LLMBase]]:
        """
        Get the appropriate LLM instance based on the configuration.
        :param id: ID of the LLM to retrieve.

        :return: An instance of the defined LLM integration.
        """
        if not self.llm:
            return None
        llm_dict = (
            {llm_id: llm.get_llm() for llm_id, llm in self.llm.items()}
            if isinstance(self.llm, dict)
            else {"global": self.llm.get_llm()}
        )  # type: ignore
        return llm_dict

    def get_embedding_model(self) -> Optional[LLMBase]:
        """
        Get the appropriate embedding model instance based on the configuration.

        :return: An instance of the defined embedding model integration.
        """
        return self.embedding_model.get_llm() if self.embedding_model else None


__all__ = ["AgentConfig", "ServerConfig", "SessionConfig"]
