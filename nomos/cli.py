"""Command Line Interface for Nomos."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

import typer

from . import __version__
from .config import AgentConfig, LoggingConfig, LoggingHandler
from .constants import (
    ERROR_COLOR,
    LLM_CHOICES,
    PRIMARY_COLOR,
    SUCCESS_COLOR,
    TEMPLATES,
    WARNING_COLOR,
)
from .core import Agent
from .llms import LLMConfig
from .models.agent import Action, DecisionExample, Step, history_to_types
from .server import run_server
from .utils.generator import AgentConfiguration, AgentGenerator


console = Console()
app = typer.Typer(
    name="nomos",
    help="Nomos CLI - Build AI Agents you can audit.",
    add_completion=True,
)


def _version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(__version__)
        raise typer.Exit()


@app.callback()
def cli_app(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show Nomos version and exit",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Nomos CLI."""
    pass


def print_banner() -> None:
    """Print the Nomos banner."""
    banner = Text("🏛️ NOMOS", style=f"bold {PRIMARY_COLOR}")
    subtitle = Text("Build AI Agents you can audit.", style="dim")
    console.print()
    console.print(banner, justify="center")
    console.print(subtitle, justify="center")
    console.print()


@app.command()
def init(
    directory: Optional[str] = typer.Option(
        None, "--directory", "-d", help="Directory to create the agent project in"
    ),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Name of the agent"),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        "-t",
        help="Template to use (basic, conversational, workflow)",
    ),
    generate: bool = typer.Option(
        False, "--generate", "-g", help="Generate agent configuration using AI"
    ),
    usecase: Optional[str] = typer.Option(
        None, "--usecase", "-u", help="Use case description or path to text file"
    ),
    tools: Optional[str] = typer.Option(
        None, "--tools", help="Comma-separated list of available tools"
    ),
) -> None:
    r"""Initialize a new Nomos agent project interactively.

    Examples:\n
    # Traditional interactive setup\n
    nomos init\n
    # AI-powered generation from use case\n
    nomos init --generate --usecase "Create a weather agent" --tools "weather_api, calculator"\n
    # Load use case from file\n
    nomos init --generate --usecase "./my_usecase.txt"
    """
    print_banner()

    console.print(
        Panel(
            "Welcome to Nomos! Let's create your new agent project.",
            title="Project Initialization",
            border_style=PRIMARY_COLOR,
        )
    )

    # Get target directory
    if not directory:
        directory = Prompt.ask("📁 Project directory", default="./my-nomos-agent")

    target_dir = Path(directory).resolve()  # type: ignore

    if target_dir.exists() and any(target_dir.iterdir()):  # noqa
        if not Confirm.ask(
            f"Directory [bold]{target_dir}[/bold] already exists and is not empty. Continue?"
        ):
            console.print("❌ Project initialization cancelled.", style=ERROR_COLOR)
            raise typer.Exit(1)

    target_dir.mkdir(parents=True, exist_ok=True)

    name = None
    persona = None
    steps: List[Step] = []

    # Choose LLM provider
    llm_table = Table(title="Choose LLM Provider")
    llm_table.add_column("Option", style=PRIMARY_COLOR)
    llm_table.add_column("Provider")

    for i, choice in enumerate(LLM_CHOICES.keys(), 1):
        llm_table.add_row(str(i), choice)

    console.print(llm_table)

    llm_choice_idx = (
        int(
            Prompt.ask(
                "🧠 Select LLM provider",
                choices=[str(i) for i in range(1, len(LLM_CHOICES) + 1)],
                default="1",
            )
        )
        - 1
    )
    llm_choice = list(LLM_CHOICES.keys())[llm_choice_idx]

    if not generate and not template:
        generate = Confirm.ask(
            "🤖 Would you like to generate the agent configuration using AI?",
            default=False,
        )

    if not generate and not template:
        template = Prompt.ask(
            "Please select a template for your agent",
            choices=list(TEMPLATES.keys()),
            default="basic",
        )

    if template:
        # Load template configuration
        template_config = TEMPLATES.get(template)
        if not template_config:
            console.print(
                f"❌ Template '{template}' not found. Available templates: {', '.join(TEMPLATES.keys())}",
                style=ERROR_COLOR,
            )
            raise typer.Exit(1)
        name = template_config.get("name", "my_nomos_agent")  # type: ignore
        persona = template_config.get("persona", "A Nomos agent")  # type: ignore
        steps = template_config.get("steps", [])  # type: ignore

    if generate:
        llm_choice_idx = (
            int(
                Prompt.ask(
                    "🧠 Select LLM provider",
                    choices=[str(i) for i in range(1, len(LLM_CHOICES) + 1)],
                    default="1",
                )
            )
            - 1
        )
        _llm_choice = LLM_CHOICES[list(LLM_CHOICES.keys())[llm_choice_idx]]
        _provider = _llm_choice["provider"]
        _model = Prompt.ask(
            "Mention the model you would like to use for generation",
            default=_llm_choice["model"],
        )
        usecase = Prompt.ask(
            "Please provide a use case description or path to a text file containing the use case",
            default="Create a weather agent",
        )
        tools = Prompt.ask(
            "Mention the tools available for the agent (comma-separated, e.g. weather_api, calculator)",
            default=None,
        )
        try:
            generated_config = _handle_config_generation(
                usecase=usecase, provider=_provider, model=_model, tools=tools  # type: ignore
            )
            steps = generated_config.to_agent_steps()
            name = generated_config.name
            persona = generated_config.persona
        except Exception as e:
            console.print(
                f"❌ Failed to generate agent configuration: {e}.",
                style=ERROR_COLOR,
            )

    # Generate project files
    _generate_project_files(target_dir, name, persona, llm_choice, steps)  # type: ignore

    console.print(
        Panel(
            f"✅ Project created successfully in [bold]{target_dir}[/bold]",
            title="Success",
            border_style=SUCCESS_COLOR,
        )
    )

    # Show next steps
    next_steps = f"""
📁 Navigate to your project: [bold]cd {target_dir}[/bold]
🔧 Edit configuration: [bold]config.agent.yaml[/bold]
🛠️ Add tools: [bold]tools/[/bold] directory
🏃 Run development mode: [bold]nomos run[/bold]
🚀 Serve: [bold]nomos serve[/bold]
"""

    console.print(
        Panel(next_steps.strip(), title="Next Steps", border_style=PRIMARY_COLOR)
    )


@app.command()
def run(
    config: Optional[str] = typer.Option(
        "config.agent.yaml", "--config", "-c", help="Path to agent configuration file"
    ),
    tools: Optional[List[str]] = typer.Option(
        None,
        "--tools",
        "-t",
        help="Python files containing tool definitions (can be used multiple times)",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
) -> None:
    """Run the Nomos agent in development mode."""
    print_banner()

    config_path = Path(config)  # type: ignore

    # Validate config file exists
    if not config_path.exists():
        console.print(
            f"❌ Configuration file not found: [bold]{config_path}[/bold]",
            style=ERROR_COLOR,
        )
        raise typer.Exit(1)

    tool_paths = []
    if tools:
        for tool_file in tools:
            tool_path = Path(tool_file)
            if not tool_path.exists():
                console.print(
                    f"❌ Tool file not found: [bold]{tool_path}[/bold]",
                    style=ERROR_COLOR,
                )
                raise typer.Exit(1)
            tool_paths.append(tool_path)

    try:
        _run(config_path, tool_paths, verbose)
    except KeyboardInterrupt:
        console.print("\n👋 Development Run stopped.", style=WARNING_COLOR)
    except Exception as e:
        console.print(f"❌ Error running development Run: {e}", style=ERROR_COLOR)
        raise typer.Exit(1)


@app.command()
def train(
    config: Optional[str] = typer.Option(
        "config.agent.yaml", "--config", "-c", help="Path to agent configuration file"
    ),
    tools: Optional[List[str]] = typer.Option(
        None,
        "--tools",
        "-t",
        help="Python files containing tool definitions (can be used multiple times)",
    ),
) -> None:
    """Run the Nomos agent in training mode."""
    print_banner()

    config_path = Path(config)  # type: ignore

    if not config_path.exists():
        console.print(
            f"❌ Configuration file not found: [bold]{config_path}[/bold]",
            style=ERROR_COLOR,
        )
        raise typer.Exit(1)

    tool_paths: list[Path] = []
    if tools:
        for tool_file in tools:
            tool_path = Path(tool_file)
            if not tool_path.exists():
                console.print(
                    f"❌ Tool file not found: [bold]{tool_path}[/bold]",
                    style=ERROR_COLOR,
                )
                raise typer.Exit(1)
            tool_paths.append(tool_path)

    try:
        _train(config_path, tool_paths)
    except KeyboardInterrupt:
        console.print("\n👋 Training stopped.", style=WARNING_COLOR)
    except Exception as e:
        console.print(f"❌ Error during training: {e}", style=ERROR_COLOR)
        raise typer.Exit(1)


@app.command()
def serve(
    config: Optional[str] = typer.Option(
        "config.agent.yaml", "--config", "-c", help="Path to agent configuration file"
    ),
    tools: Optional[List[str]] = typer.Option(
        None,
        "--tools",
        "-t",
        help="Python files containing tool definitions (can be used multiple times)",
    ),
    port: Optional[int] = typer.Option(
        None, "--port", "-p", help="Port to bind the server"
    ),
    workers: Optional[int] = typer.Option(
        None, "--workers", "-w", help="Number of uvicorn workers"
    ),
) -> None:
    """Serve the Nomos agent using FastAPI and Uvicorn."""
    print_banner()

    config_path = Path(config)  # type: ignore

    if not config_path.exists():
        console.print(
            f"❌ Configuration file not found: [bold]{config_path}[/bold]",
            style=ERROR_COLOR,
        )
        raise typer.Exit(1)

    tool_paths: list[Path] = []
    if tools:
        for tool_file in tools:
            tool_path = Path(tool_file)
            if not tool_path.exists():
                console.print(
                    f"❌ Tool file not found: [bold]{tool_path}[/bold]",
                    style=ERROR_COLOR,
                )
                raise typer.Exit(1)
            tool_paths.append(tool_path)

    console.print(
        Panel(
            f"🚀 Starting server on port [bold]{port or 'config'}[/bold]",
            title="Serve",
            border_style=PRIMARY_COLOR,
        )
    )

    tool_dirs: set[str] = set()
    for p in tool_paths:
        tool_dirs.add(str(p if p.is_dir() else p.parent))

    default_tool_dir = Path.cwd() / "tools"
    if not tool_dirs and default_tool_dir.exists():
        tool_dirs.add(str(default_tool_dir))

    if tool_dirs:
        os.environ["TOOLS_PATH"] = os.pathsep.join(tool_dirs)

    cfg = AgentConfig.from_yaml(str(config_path))
    run_port = port if port is not None else cfg.server.port
    worker_count = workers if workers is not None else cfg.server.workers

    run_server(config_path, port=run_port, workers=worker_count)


@app.command()
def test(
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to YAML test configuration file (defaults to tests.agent.yaml)",
    ),
    coverage: bool = typer.Option(
        True, "--coverage/--no-coverage", help="Generate coverage report"
    ),
    pytest_args: List[str] = typer.Argument(None),
) -> None:
    """Run the Nomos testing framework."""
    print_banner()

    console.print(
        Panel(
            "🧪 Running Nomos agent tests",
            title="Testing Framework",
            border_style=PRIMARY_COLOR,
        )
    )

    yaml_path = Path(config) if config else Path.cwd() / "tests.agent.yaml"

    try:
        if yaml_path.exists():
            from .testing.yaml_runner import run_yaml_tests

            result = run_yaml_tests(yaml_path, pytest_args, coverage)
            if result != 0:
                console.print("❌ Some tests failed!", style=ERROR_COLOR)
                raise typer.Exit(result)
            console.print("✅ All tests passed!", style=SUCCESS_COLOR)
        else:
            _run_tests(pytest_args, coverage)
    except Exception as e:
        console.print(f"❌ Error running tests: {e}", style=ERROR_COLOR)
        raise typer.Exit(1)


@app.command()
def schema(
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write JSON schema to file instead of stdout",
    ),
) -> None:
    """Generate JSON schema for agent configuration."""
    import json

    schema = AgentConfig.model_json_schema()
    schema_json = json.dumps(schema, indent=2)
    if output:
        Path(output).write_text(schema_json)
        console.print(
            f"✅ Schema written to [bold]{output}[/bold]",
            style=SUCCESS_COLOR,
        )
    else:
        console.print_json(schema_json)


def _generate_project_files(
    target_dir: Path, name: str, persona: str, llm_choice: str, steps: List[Step]
) -> None:
    """Generate project files for the new agent."""
    # Generate config.agent.yaml
    assert len(steps) > 0, "At least one step must be defined for the agent."
    agent_config = AgentConfig(
        name=name,
        persona=persona,
        steps=steps,
        start_step_id=steps[0].step_id,
        llm=LLMConfig(
            provider=LLM_CHOICES[llm_choice]["provider"],
            model=LLM_CHOICES[llm_choice]["model"],
        ),
        logging=LoggingConfig(
            enable=True,
            handlers=[
                LoggingHandler(
                    type="stderr",
                    level="INFO",
                    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
                )
            ],
        ),
    )
    agent_config.to_yaml(str(target_dir / "config.agent.yaml"))

    # Create tools directory
    tools_dir = target_dir / "tools"
    tools_dir.mkdir(exist_ok=True)

    tools_init_content = [
        '"""This module imports all tools from the tools directory and makes them available in a list."""',
        "",
        "import os",
        "",
        "tool_list: list = []",
        "",
        "for filename in os.listdir(os.path.dirname(__file__)):",
        "    if filename.endswith('.py') and filename != '__init__.py':",
        "        module_name = filename[:-3]  # Remove the .py extension",
        "        try:",
        "            module = __import__(f'tools.{module_name}', fromlist=[''])",
        "            tool_list.extend(getattr(module, 'tools', []))",
        "        except ImportError as e:",
        "            print(f'Warning: Could not import {module_name}: {e}')",
        "",
        "__all__ = ['tool_list']",
    ]
    sample_tool_content = [
        '"""Sample tools for the Nomos agent."""',
        "",
        "def sample_tool(query: str) -> str:",
        '    """',
        "    A sample tool that echoes the input query.",
        "",
        "    Args:",
        "        query: The input query to echo",
        "",
        "    Returns:",
        "        The echoed query with a prefix",
        '   """',
        "    return f'You said: {query}'",
        "",
        "def get_current_time() -> str:",
        '    """Get the current time as a string."""',
        "",
        "    from datetime import datetime",
        "    return datetime.now().isoformat()",
        "",
        "# Export tools for discovery",
        "tools = [sample_tool, get_current_time]",
    ]
    main_content = [
        '"""Main entry point for the Nomos agent."""',
        "",
        "import os",
        "import sys",
        "from pathlib import Path",
        "from dotenv import load_dotenv",
        "",
        "# Load environment variables from .env file if it exists",
        "env_file = Path(__file__).parent / '.env'",
        "if env_file.exists():",
        "    load_dotenv(dotenv_path=env_file)",
        "else:",
        "    print('⚠️  .env file not found. Environment variables will not be loaded.')",
        "",
        "# Add tools directory to Python path",
        "sys.path.insert(0, str(Path(__file__).parent))",
        "",
        "from nomos import *",
        "from tools import tool_list",
        "",
        "def main():",
        '    """Run the agent interactively."""',
        "    # Load configuration",
        "    config_path = Path(__file__).parent / 'config.agent.yaml'",
        "    config = AgentConfig.from_yaml(str(config_path))",
        "",
        "    # Create agent",
        "    agent = Agent.from_config(config, tools=tool_list)",
        "",
        "    # Create session",
        "    session = agent.create_session(verbose=True)",
        "",
        "    print(f\"🤖 {config.name} agent is ready! Type 'quit' to exit.\\n\")"
        '    print(f"Available tools: {[tool.__name__ if callable(tool) else str(tool) for tool in tool_list]}\\n")'
        ""
        "    while True:"
        "        try:"
        "            user_input = input('You: ').strip()"
        "            if user_input.lower() in ['quit', 'exit', 'bye']:"
        "                print('👋 Goodbye!')"
        "                break",
        "            if not user_input:" "                continue",
        "            decision, *_ = session.next(user_input)",
        "            if hasattr(decision, 'response') and decision.response:",
        '                print(f"🤖 {config.name}: {decision.response}")'
        "        except KeyboardInterrupt:"
        '            print("\\n👋 Goodbye!")'
        "            break",
        "        except Exception as e:",
        '            print(f"❌ Error: {e}")',
        "",
        "if __name__ == '__main__':",
        "    main()",
    ]
    requirements_content = [
        "nomos[cli,serve,traces] >=0.2.4",
        f"nomos[{LLM_CHOICES[llm_choice]['provider'].lower()}] >=0.2.4",
    ]
    env_content = [
        "# Environment variables for your Nomos agent",
        "",
        "# LLM API Keys (uncomment the one you're using)",
        "# OPENAI_API_KEY=your_openai_api_key_here",
        "# MISTRAL_API_KEY=your_mistral_api_key_here",
        "# GOOGLE_API_KEY=your_google_api_key_here",
        "",
        "# Server configuration",
        "PORT=8000",
        "",
        "# Optional: Database configuration for persistent sessions",
        "# DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname",
        "# REDIS_URL=redis://localhost:6379/0",
        "",
        "# Optional: Tracing configuration",
        "# ENABLE_TRACING=true",
        "# ELASTIC_APM_SERVER_URL=http://localhost:8200",
        "# ELASTIC_APM_TOKEN=your_apm_token",
        "# SERVICE_NAME=my-nomos-agent",
        "# SERVICE_VERSION=1.0.0",
        "",
    ]
    readme_content = [
        "# Nomos Agent Project",
        "",
        "This is a Nomos agent project.",
        "",
        "## Configuration",
        "Edit the `config.agent.yaml` file to customize your agent.",
        "",
        "## Tools",
        "Add your custom tools in the `tools/` directory.",
        "",
        "> [!NOTE]"
        "> Copy the `.env.example` file to `.env` using `cp .env.example .env` and fill in your environment variables.",
        "",
        "## Running the Agent",
        "Run the agent in development mode with:",
        "```bash",
        "nomos run",
        "```",
        "",
        "## Serving the Agent",
        "Serve the agent using Uvicorn with:",
        "```bash",
        "nomos serve",
        "```",
    ]

    # Write files
    agent_config.to_yaml(str(target_dir / "config.agent.yaml"))
    (target_dir / "tools" / "__init__.py").write_text("\n".join(tools_init_content))
    (target_dir / "tools" / "sample_tool.py").write_text("\n".join(sample_tool_content))
    (target_dir / "main.py").write_text("\n".join(main_content))
    (target_dir / "requirements.txt").write_text("\n".join(requirements_content))
    (target_dir / ".env").write_text("\n".join(env_content))
    (target_dir / "README.md").write_text("\n".join(readme_content))
    console.print(
        f"✅ Project files generated in [bold]{target_dir}[/bold]",
        style=SUCCESS_COLOR,
    )


def _run(config_path: Path, tool_files: List[Path], verbose: bool) -> None:
    """Run the agent in development mode."""
    current_dir = Path.cwd()

    # Collect tool directories
    tool_dirs: set[str] = {str(p if p.is_dir() else p.parent) for p in tool_files}
    default_tool_dir = current_dir / "tools"
    if default_tool_dir.exists():
        tool_dirs.add(str(default_tool_dir))

    if tool_dirs:
        os.environ["TOOLS_PATH"] = os.pathsep.join(tool_dirs)
    else:
        console.print(
            "⚠️  No tool files provided and no tools directory found. Running without tools.",
            style=WARNING_COLOR,
        )

    # Create development server script
    dev_server_code = [
        '"""Development server for Nomos agents."""',
        "",
        "import sys",
        "import os",
        "from pathlib import Path",
        "if Path(__file__).parent / '.env':",
        "    from dotenv import load_dotenv",
        "    load_dotenv(dotenv_path=Path(__file__).parent / '.env')",
        "else:",
        "    print('⚠️  .env file not found. Environment variables will not be loaded.')",
        "",
        "sys.path.insert(0, str(Path.cwd()))",
        "",
        "from nomos import *",
        "from nomos.api.tools import tool_list",
        "",
        "def main():",
        "    try:",
        f'        config = AgentConfig.from_yaml("{config_path}")',
        "        agent = Agent.from_config(config, tools=tool_list)",
        f"        session = agent.create_session(verbose={verbose})",
        "",
        '        print(f"🤖 {config.name} agent ready in interactive mode!")',
        f'        print(f"📁 Config: {config_path}")',
        '        print(f"🔧 Tools: {len(tool_list)} loaded")',
        "        print('Type quit to exit\\n')",
        "",
        "        while True:",
        "            try:",
        "                user_input = input('You: ').strip()",
        "                if user_input.lower() in ['quit', 'exit', 'bye']:",
        "                    break",
        "                if not user_input:",
        "                    continue",
        "                decision, *_ = session.next(user_input)",
        "                print(f'Agent: {decision.response}')",
        "            except KeyboardInterrupt:",
        "                break",
        "            except Exception as e:",
        "                print(f'Error: {e}')",
        f"                if {verbose}:",
        "                    import traceback",
        "                    traceback.print_exc()",
        "    except Exception as e:",
        "        print(f'❌ Failed to start agent: {e}')",
        f"        if {verbose}:",
        "            import traceback",
        "            traceback.print_exc()",
        "",
        "if __name__ == '__main__':",
        "    main()",
    ]

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False
    ) as temp_script:
        temp_script_path = temp_script.name
        temp_script.write("\n".join(dev_server_code))

    try:
        console.print(f"📂 Working directory: [dim]{current_dir}[/dim]")
        result = subprocess.run(
            [sys.executable, temp_script_path], cwd=current_dir, check=False
        )
        if result.returncode not in (0, 130):
            console.print(
                f"❌ Development server exited with code {result.returncode}",
                style=ERROR_COLOR,
            )
    finally:
        os.unlink(temp_script_path)


def _train(config_path: Path, tool_files: List[Path]) -> None:
    """Interactive training loop for refining agent decisions."""
    current_dir = Path.cwd()

    tool_dirs: set[str] = {str(p if p.is_dir() else p.parent) for p in tool_files}
    default_tool_dir = current_dir / "tools"
    if default_tool_dir.exists():
        tool_dirs.add(str(default_tool_dir))

    if tool_dirs:
        os.environ["TOOLS_PATH"] = os.pathsep.join(tool_dirs)
    else:
        console.print(
            "⚠️  No tool files provided and no tools directory found. Running without tools.",
            style=WARNING_COLOR,
        )

    from nomos.api.tools import tool_list

    config = AgentConfig.from_yaml(str(config_path))
    agent = Agent.from_config(config, tools=tool_list)

    console.print(
        f"🤖 [bold]{config.name}[/bold] agent loaded in training mode.",
        style=PRIMARY_COLOR,
    )
    console.print("Type quit to exit\n")

    session_data: Optional[dict] = None
    last_action: Action = Action.RESPOND
    while True:
        # print(session_data)
        if last_action == Action.RESPOND:
            user_input = Prompt.ask("You").strip()
            if user_input.lower() in {"quit", "exit", "bye"}:
                break
        else:
            user_input = None
        decision, tool_output, session_data = agent.next(
            user_input, session_data, verbose=True
        )
        if decision.action == Action.RESPOND:
            console.print(
                "Agent:\nReasoning:{}\nResponse: {}".format(
                    "\n".join(decision.reasoning), decision.response
                ),
                style=PRIMARY_COLOR,
            )
        elif decision.action == Action.TOOL_CALL:
            console.print(
                "Agent:\nReasoning:{}\nTool call: {}\nTool Result: {}".format(
                    "\n".join(decision.reasoning), decision.tool_call, tool_output
                ),
                style=PRIMARY_COLOR,
            )
        elif decision.action == Action.MOVE:
            console.print(
                "Agent:\nReasoning:{}\nMoving to step: {}".format(
                    "\n".join(decision.reasoning), decision.step_id
                ),
                style=PRIMARY_COLOR,
            )
        elif decision.action == Action.END:
            console.print(
                "Agent:\nReasoning:{}\nEnding session.".format(
                    "\n".join(decision.reasoning)
                ),
                style=PRIMARY_COLOR,
            )
            break
        else:
            console.print(
                "Agent:\nReasoning:{}\nUnknown action: {}".format(
                    "\n".join(decision.reasoning), decision.action
                ),
                style=ERROR_COLOR,
            )

        if Confirm.ask("Are you satisfied with this decision?", default=True):
            last_action = decision.action
            continue

        feedback = Prompt.ask("What should have happened?")

        history = session_data.get("history")  # type: ignore
        flow_state = session_data.get("flow_state")
        flow_memory_context = (
            flow_state.get("flow_memory_context") if flow_state else None
        )
        step_id = session_data.get("current_step_id")  # type: ignore

        # Take step back
        history = history[:-1] if len(history) > 1 else []  # type: ignore
        flow_memory_context = (
            flow_memory_context[:-1]
            if flow_memory_context and len(flow_memory_context) > 1
            else []
        )

        session_data["history"] = history
        if flow_state:
            session_data["flow_state"]["context"] = flow_memory_context

        context_summary = config.get_llm().generate_summary(
            history_to_types(
                flow_memory_context if flow_state else session_data["history"]
            )
        )

        for step in config.steps:
            if step.step_id == step_id:
                if step.examples is None:
                    step.examples = []
                step.examples.append(
                    DecisionExample(
                        context=" ".join(context_summary.summary), decision=feedback
                    )
                )
                break

        config.to_yaml(str(config_path))
        agent = Agent.from_config(config, tools=tool_list)
        console.print(f"✅ Example added for step {step_id}. Agent reloaded.")


def _run_tests(pytest_args: Optional[List[str]] = None, coverage: bool = False) -> None:
    """Run tests using pytest."""
    cmd = ["python", "-m", "pytest"] + (pytest_args or ["."])

    if coverage:
        cmd.extend(["--cov=.", "--cov-report=term-missing"])

    console.print(
        f"Running tests with command: [bold]{' '.join(cmd)}[/bold]",
        style=PRIMARY_COLOR,
    )

    result = subprocess.run(cmd)

    if result.returncode == 0:
        console.print("✅ All tests passed!", style=SUCCESS_COLOR)
    else:
        console.print("❌ Some tests failed!", style=ERROR_COLOR)
        raise typer.Exit(result.returncode)


def _handle_config_generation(
    usecase: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    tools: Optional[str] = None,
) -> AgentConfiguration:
    """Handle AI generation of agent configuration."""
    llm_config: Optional[LLMConfig] = None
    if provider or model:
        llm_config = LLMConfig(
            provider=provider,
            model=model,
        )
    generator = AgentGenerator(
        console=console,
        llm_config=llm_config,
    )
    return generator.generate(usecase=usecase, tools_available=tools)


def main() -> None:
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()
