<!-- Announcement Bar -->
<div align="center" style="margin-bottom: 1.5em;">
  <div style="
    display: inline-block;
    background: #222;
    color: #fff;
    font-weight: 500;
    padding: 0.5em 2em;
    font-size: 1em;
    margin-bottom: 1em;
    border-radius: 999px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    border: 1px solid #222;
  ">
    <b>NOMOS v0.2.1 released!</b> | <a href="https://github.com/dowhiledev/nomos/releases" style="color:#fff;text-decoration:underline;">See what's new →</a>
  </div>
</div>

<h1 align="center">
  <a href="https://github.com/dowhiledev/nomos">
    <picture>
      <source srcset="assets/dark.png" media="(prefers-color-scheme: dark)">
      <source srcset="assets/light.png" media="(prefers-color-scheme: light)">
      <img src="assets/light.png" alt="nomos" width="400">
    </picture>
  </a>
</h1>

<div align="center">

  An open-source, configurable multi-step agent framework for building advanced LLM-powered assistants
  <br />
  <br />
  <a href="#usage"><strong>Explore examples »</strong></a>
  ·
  <a href="https://nomos-builder.vercel.app"><strong>🎨 Try Visual Builder »</strong></a>
  ·
  <a href="docs-site"><strong>📚 Documentation »</strong></a>
  <br />
  <br />
  <a href="https://github.com/dowhiledev/nomos/issues/new?assignees=&labels=bug&template=01_BUG_REPORT.md&title=bug%3A+">Report a Bug</a>
  ·
  <a href="https://github.com/dowhiledev/nomos/issues/new?assignees=&labels=enhancement&template=02_FEATURE_REQUEST.md&title=feat%3A+">Request a Feature</a>
  ·
  <a href="https://github.com/dowhiledev/nomos/issues/new?assignees=&labels=question&template=04_SUPPORT_QUESTION.md&title=support%3A+">Ask a Question</a>
</div>

<div align="center">
<br />

![PyPI - Version](https://img.shields.io/pypi/v/nomos)
[![codecov](https://codecov.io/gh/dowhiledev/nomos/graph/badge.svg?token=MXRK9HGE5R)](https://codecov.io/gh/dowhiledev/nomos)
[![Test](https://github.com/dowhiledev/nomos/actions/workflows/test.yml/badge.svg)](https://github.com/dowhiledev/nomos/actions/workflows/test.yml)
[![Release](https://github.com/dowhiledev/nomos/actions/workflows/publish.yml/badge.svg)](https://github.com/dowhiledev/nomos/actions/workflows/publish.yml)
[![Docker Image Version](https://img.shields.io/docker/v/chandralegend/nomos-base)](https://hub.docker.com/r/chandralegend/nomos-base)
[![License](https://img.shields.io/github/license/dowhiledev/nomos)](LICENSE)

[![Pull Requests welcome](https://img.shields.io/badge/PRs-welcome-ff69b4.svg?style=flat-square)](https://github.com/dowhiledev/nomos/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22)

</div>

<details open="open">
<summary>Table of Contents</summary>

- [About](#about)
  - [Features](#features)
  - [Built With](#built-with)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
  - [CLI Usage](#cli-usage)
  - [Python API Example](#python-api-example)
  - [YAML Config Example](#yaml-config-example)
  - [Error Handling](#error-handling)
- [Flow Management](#flow-management)
  - [What are Flows?](#what-are-flows)
  - [Flow Configuration](#flow-configuration)
  - [Flow Memory and Context](#flow-memory-and-context)
  - [Flow Benefits](#flow-benefits)
  - [Example: Barista Agent with Flows](#example-barista-agent-with-flows)
- [LLM Support](#llm-support)
  - [OpenAI](#openai)
  - [Mistral AI](#mistral-ai)
  - [Google Gemini](#google-gemini)
- [Configuration](#configuration)
- [Package Tool Integration](#package-tool-integration)
- [Examples](#examples)
  - [Barista Agent](#example-barista-agent)
  - [Financial Planning Assistant](#example-financial-planning-assistant)
- [Deployment](#deployment)
  - [Docker Base Image](#docker-base-image)
  - [Tracing and Elastic APM Integration](#tracing-and-elastic-apm-integration)
  - [Persistent Storage and Session Management](#persistent-storage-and-session-management)
  - [API Endpoints](#api-endpoints)
- [Roadmap](#roadmap)
- [Support](#support)
- [Project assistance](#project-assistance)
- [Contributing](#contributing)
- [Authors & contributors](#authors--contributors)
- [License](#license)
- [Acknowledgements](#acknowledgements)

</details>

---

## About

`NOMOS` (previously `S.O.F.I.A - Simple Orchestrated Flow Intelligence Agent`) is an open-source, configurable multi-step agent framework for building advanced LLM-powered assistants. Define your agent's persona, tools, and step-by-step flows in Python or YAML—perfect for conversational, workflow, and automation use cases.

The name `NOMOS` comes from the Greek word for "law" or "custom" - literally "the rulebook" powering every agentic step. This reflects the framework's core principle of providing structured, rule-based guidance for AI behavior.

The framework allows you to move from no-code to low-code development, making it accessible for both non-programmers and experienced developers to create sophisticated AI agents.

### Features

- **Step-based agent flows**: Define agent behavior as a sequence of steps, each with its own tools and transitions.
- **Advanced Flow Management**: Organize steps into flows with shared context, memory, and components. Perfect for complex workflows that require stateful interactions.
- **Flow-specific Memory**: Each flow maintains its own context and can transfer knowledge between flows using intelligent summarization.
- **Persona-driven**: Easily set the agent's persona for consistent, branded responses.
- **Tool integration**: Register Python functions as tools for the agent to call.
- **Package-based tools**: Reference Python package functions directly using `package_name:function` syntax.
- **Auto tool documentation**: Tool descriptions and parameter documentation are automatically generated from docstrings.
- **YAML or Python config**: Configure agents via code or declarative YAML.
- **Step-level answer models**: Specify an `answer_model` for any step to receive structured (JSON/object) responses.
- **🎨 Visual Flow Builder**: Interactive web-based tool for designing and managing agent flows with drag-and-drop interface. **[Try it live at nomos-builder.vercel.app](https://nomos-builder.vercel.app)**
- **OpenAI, Mistral, Gemini, Ollama, and HuggingFace LLM support**
- **Session management**: Save and resume conversations with Redis or PostgreSQL persistent storage.
- **Advanced error handling**: Built-in error recovery mechanisms with configurable retry limits.
- **API integration**: Ready-to-use FastAPI endpoints for web and WebSocket interaction.
- **Elastic APM tracing**: Built-in support for distributed tracing and monitoring.
- **Docker deployment**: Pre-built base image for rapid deployment.
- **Extensible**: Build your own tools, steps, and integrations.
- **Interactive CLI**: Bootstrap new agents with `nomos init` (install with `[cli]` extra).

### Built With

- Python
- OpenAI, Mistral, Gemini, Ollama, and HuggingFace LLMs
- Redis/PostgreSQL (optional for storage)
- OpenTelemetry and Elastic APM (optional for tracing)
- FastAPI & Docker (optional for deployment)

## Visual Flow Builder

For those who prefer a no-code approach, NOMOS includes a powerful Visual Flow Builder - an interactive web-based tool that lets you design agent flows using drag-and-drop.

### 🚀 Try It Now

**Live hosted version**: [nomos-builder.vercel.app](https://nomos-builder.vercel.app)

### Key Features

- **Drag & Drop Interface**: Create conversation flows visually without writing code
- **Real-time Integration**: Visual connections automatically update step configurations
- **Flow Grouping**: Organize related steps into logical flow groups
- **Tool Connections**: Visually connect steps to available tools
- **YAML Export/Import**: Generate Nomos-compatible configuration files
- **Auto-layout**: Intelligent positioning for clean flow visualization
- **Undo/Redo Support**: Full history management for editing operations

### Local Development

To run the Visual Flow Builder locally:

```bash
cd tools/visual-builder
npm install
npm run dev
```

Or use Docker:

```bash
cd tools/visual-builder
npm run docker:build-and-run
```

See [`tools/visual-builder/README.md`](tools/visual-builder/README.md) for detailed setup instructions.

## Documentation

The full documentation is available in the [docs-site](docs-site) folder. Run `npm install` and `npm run dev` inside `docs-site` to start the Nextra documentation locally.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Optional: Redis or PostgreSQL for session storage
- Optional: Elastic APM for tracing

### Installation

#### From PyPI

```bash
pip install nomos
```

#### With CLI support

```bash
pip install nomos[cli]
```

#### With LLM support

```bash
pip install nomos[openai]      # For OpenAI support
pip install nomos[mistralai]   # For Mistral AI support
pip install nomos[gemini]      # For Google Gemini support
pip install nomos[ollama]      # For Ollama support
pip install nomos[huggingface] # For HuggingFace support
```

#### With tracing support

```bash
pip install nomos[traces]
```

## Usage

NOMOS supports a spectrum of implementation approaches from no-code to low-code to full-code development.

### 🎨 No-Code: Visual Flow Builder

The easiest way to get started is with our Visual Flow Builder at [nomos-builder.vercel.app](https://nomos-builder.vercel.app). Simply drag and drop to create your agent flows, then export the configuration.

### CLI Usage

The Nomos CLI provides powerful commands to bootstrap, develop, and deploy your agents.

#### Initialize a New Agent

Create a new agent project interactively:

```bash
nomos init
```

**Options:**
- `--directory, -d`: Project directory (default: `./my-nomos-agent`)
- `--name, -n`: Agent name
- `--template, -t`: Template to use (`basic`, `conversational`, `workflow`)
- `--generate, -g`: Generate a template using AI (You are required to set the corresponding LLM API key in your environment variables, e.g., `OPENAI_API_KEY` for OpenAI)

**Example:**
```bash
nomos init --directory ./my-bot --name chatbot --template basic
# or
nomos init --directory ./my-bot --name chatbot --generate
```

#### Development Mode

Run your agent locally for development and testing:

```bash
nomos run
```

**Options:**
- `--config, -c`: Configuration file path (default: `config.agent.yaml`)
- `--tools, -t`: Python files with tool definitions (can be used multiple times)
- `--port, -p`: Development server port (default: `8000`)
- `--verbose, -v`: Enable verbose logging

**Examples:**
```bash
# Basic usage
nomos run

# With custom config and tools
nomos run --config my-config.yaml --tools tools.py --tools utils.py

# With verbose logging on custom port
nomos run --verbose --port 3000
```

#### Production Deployment

Serve your agent using Docker for production:

```bash
nomos serve
```

**Options:**
- `--config, -c`: Configuration file path (default: `config.agent.yaml`)
- `--tools, -t`: Python files with tool definitions (can be used multiple times)
- `--dockerfile, -f`: Path to custom Dockerfile
- `--env-file, -e`: Path to .env file to load environment variables
- `--tag`: Docker image tag (default: `nomos-agent`)
- `--port, -p`: Host port to bind to (default: `8000`)
- `--build/--no-build`: Build Docker image before running (default: `true`)
- `--detach/--no-detach`: Run container in detached mode (background)

**Examples:**
```bash
# Basic deployment
nomos serve

# With custom Dockerfile and tools
nomos serve --dockerfile custom.Dockerfile --tools tools.py

# Custom port without building
nomos serve --port 9000 --no-build

# Run in detached mode (background)
nomos serve --detach

# With environment file
nomos serve --env-file .env --detach
```

#### Testing

Run tests for your agent:

```bash
nomos test
```

**Options:**
- `--pattern, -p`: Test file pattern to match (default: `test_*.py`)
- `--verbose, -v`: Enable verbose test output
- `--coverage/--no-coverage`: Generate coverage report (default: `true`)

**Examples:**
```bash
# Run all tests
nomos test

# Run specific test pattern
nomos test --pattern "test_tools*"

# Verbose output without coverage
nomos test --verbose --no-coverage
```

This will interactively guide you to create a config YAML and starter Python file for your agent.

### Python API Example (Full Code)

```python
from nomos import *
from nomos.llms import OpenAIChatLLM
from nomos.models.flow import FlowConfig
from nomos.memory.flow import FlowMemoryComponent

def get_time():
    """Get the current time.

    Returns:
        str: The current time in string format.
    """
    from datetime import datetime
    return f"Current time: {datetime.now()}"

steps = [
    Step(
        step_id="start",
        description="Greet and offer to tell the time or perform calculations.",
        available_tools=["get_time", "math:sqrt"],  # Direct reference to the sqrt function from math package
        routes=[Route(target="calculation", condition="User wants to do math"),
                Route(target="end", condition="User is done")],
    ),
    Step(
        step_id="calculation",
        description="Perform mathematical calculations for the user.",
        available_tools=["math:sqrt", "math:pow"],
        routes=[Route(target="end", condition="Calculation is complete")],
    ),
    Step(
        step_id="end",
        description="Say goodbye.",
    ),
]

# Define flows for better organization
flows = [
    FlowConfig(
        flow_id="math_workflow",
        description="Handle mathematical calculations",
        enters=["calculation"],
        exits=["end"],
        components={
            "memory": {
                "llm": {"provider": "openai", "model": "gpt-4o-mini"},
                "retriever": {"method": "bm25", "kwargs": {"k": 3}}
            }
        }
    )
]

llm = OpenAIChatLLM()
agent = Nomos(
    name="clockbot",
    llm=llm,
    steps=steps,
    flows=flows,  # Add flows to the agent
    start_step_id="start",
    tools=[get_time, "math:sqrt", "math:pow"],
    persona="You are a friendly assistant that can tell time and perform calculations.",
    max_errors=3,  # Will retry up to 3 times before failing
    max_iter=5,   # Maximum number of iterations allowed in a single interaction
)
sess = agent.create_session()
# ... interact with sess.next(user_input)
```

### YAML Config Example (Low-Code)

```yaml
name: utility-bot
persona: You are a helpful utility bot that can perform various calculations and data operations.
steps:
  - step_id: start
    description: Handle user requests for mathematical operations or data processing.
    available_tools:
      - math:sqrt
      - json:loads
      - itertools:combinations
    routes:
      - target: end
        condition: User is done with calculations
  - step_id: end
    description: Say goodbye to the user.
start_step_id: start
max_errors: 3  # Maximum consecutive errors before stopping
```

See [`examples/config.barista.yaml`](examples/config.barista.yaml) for a more full-featured example.
More examples are available in the [`examples`](examples/) directory.

## Flow Management

NOMOS provides advanced flow management capabilities that allow you to organize related steps into logical groups with shared context and components. Flows are perfect for complex workflows that require stateful interactions, context preservation, and intelligent transitions between different parts of your agent's behavior.

### What are Flows?

Flows are containers that group related steps together and provide:

- **Shared Memory**: Each flow maintains its own context that persists across steps within the flow
- **Component Management**: Flows can have dedicated components like memory systems, specialized tools, or custom handlers
- **Context Transfer**: When transitioning between flows, context is intelligently summarized and passed along
- **Entry/Exit Points**: Define which steps can enter or exit a flow for better control flow management

### Flow Configuration

You can define flows in your YAML configuration:

```yaml
# Basic agent configuration
name: advanced-assistant
persona: A helpful assistant with specialized workflows
start_step_id: greeting

steps:
  - step_id: greeting
    description: Greet the user and understand their needs
    routes:
      - target: order_taking
        condition: User wants to place an order
      - target: customer_support
        condition: User needs help or support

  - step_id: order_taking
    description: Handle order details and preferences
    available_tools:
      - get_menu_items
      - add_to_cart
    routes:
      - target: order_confirmation
        condition: Order is complete

  - step_id: order_confirmation
    description: Confirm order details and process payment
    available_tools:
      - calculate_total
      - process_payment
    routes:
      - target: farewell
        condition: Order is confirmed

  - step_id: customer_support
    description: Handle customer inquiries and issues
    available_tools:
      - search_knowledge_base
      - escalate_to_human
    routes:
      - target: farewell
        condition: Issue is resolved

  - step_id: farewell
    description: Thank the user and end the conversation

# Enhanced flows configuration
flows:
  - flow_id: order_management
    description: "Complete order processing workflow"
    enters:
      - order_taking
    exits:
      - order_confirmation
      - farewell
    components:
      memory:
        llm:
          provider: openai
          model: gpt-4o-mini
        retriever:
          method: bm25
          kwargs:
            k: 5
    metadata:
      max_context_size: 50
      summary_threshold: 20

  - flow_id: support_workflow
    description: "Customer support and issue resolution"
    enters:
      - customer_support
    exits:
      - farewell
    components:
      memory:
        llm:
          provider: openai
          model: gpt-4o-mini
        retriever:
          method: bm25
```

### Flow Memory and Context

Each flow can have its own memory system that:

- **Preserves Context**: Maintains conversation history and important details within the flow
- **Intelligent Retrieval**: Uses BM25 or other retrieval methods to find relevant information
- **Context Summarization**: Automatically summarizes context when exiting a flow
- **Cross-Flow Transfer**: Passes summarized context when transitioning between flows

### Flow Benefits

1. **Organized Architecture**: Keep related functionality grouped together
2. **Context Awareness**: Maintain relevant information throughout related interactions
3. **Scalable Design**: Easily extend your agent with new flows without affecting existing ones
4. **Memory Efficiency**: Each flow only maintains context relevant to its purpose
5. **Flexible Transitions**: Define precise entry and exit conditions for better control flow

### Example: Barista Agent with Flows

The barista example demonstrates flow usage for order management:

```yaml
flows:
  - flow_id: take_coffee_order
    description: "Complete coffee ordering process"
    enters:
      - take_coffee_order
    exits:
      - finalize_order
      - end
    components:
      memory:
        llm:
          provider: openai
          model: gpt-4o-mini
        retriever:
          method: bm25
          kwargs:
            k: 5
```

This flow ensures that all order-related context (customer preferences, cart contents, order history) is maintained throughout the ordering process and properly summarized when the order is complete.

## LLM Support

### Choose Your LLM (We are adding more soon!)

```python
from nomos.llms import OpenAI, Mistral, Gemini, Ollama, HuggingFace

# Choose your LLM provider
llm = OpenAI(model="gpt-4o-mini")
llm = Mistral(model="mistral-medium")
llm = Gemini(model="gemini-pro")
llm = Ollama(model="llama3")
llm = HuggingFace(model="meta-llama/Meta-Llama-3-8B-Instruct")
```

Or You can also specify LLM configuration in your YAML config:

```yaml
# ... rest of config
llm:
  provider: openai
  model: gpt-4o-mini
# ...rest of config
```

## Package Tool Integration

NOMOS allows you to reference Python package functions directly using the `package_name:function` syntax:

```python
# Reference a function from a standard library
"math:sqrt"                      # Standard library function
"json:loads"                     # Another standard library function
"itertools:combinations"         # Complex functions work too!

# Reference nested module functions
"package_name:module.submodule.function"
```

Benefits of package tool integration:

1. **No-code/low-code development**: Use existing Python functions without writing wrapper code
2. **Automatic documentation**: Function docstrings are used to generate tool descriptions and parameter documentation
3. **Simplified configuration**: Easily reference any Python function in your environment

Tool parameter descriptions in configuration files take precedence over automatically extracted docstring descriptions.

> **NOTE**: Make sure the package is installed in your environment and function returns an output that is string representable.

## Custom Tool Files

You can organize your own tools in Python modules or keep them inside a `tools/` directory.
Each module should export a list named `tools` containing the functions you want
the agent to use.

```python
# tools/my_tools.py
def greet(name: str) -> str:
    """Return a simple greeting."""
    return f"Hello {name}!"

tools = [greet]
```

Run the CLI and provide the tool file with `--tools` (you can specify multiple
files):

```bash
nomos run --config config.agent.yaml --tools tools/my_tools.py
```

The command sets the `TOOLS_PATH` environment variable so the API server loads
your modules directly. When embedding Nomos in your own application, set
`TOOLS_PATH` to a colon-separated list of directories containing your tool
modules.

## Examples

### Example: Barista Agent

A full example is provided in [`examples/barista/barista.py`](examples/barista.py) and [`examples/config.barista.yaml`](examples/config.barista.yaml).

To run the Barista agent:

```bash
cd examples/barista
export OPENAI_API_KEY=your-api-key-here

# Run in development mode
nomos run --config config.barista.yaml --tools barista_tools.py

# Or serve with Docker
nomos serve --config config.barista.yaml --tools barista_tools.py
```

### Example: Financial Planning Assistant

A production-ready example of a Financial Planning Assistant is available in [`examples/financial-advisor/`](examples/financial-advisor/). This example demonstrates:

- Budget planning and expense tracking
- Savings goal management
- Financial health assessment
- Uses the nomos-base Docker image
- Production-ready configuration

To run the Financial Planning Assistant:

```bash
cd examples/financial-advisor

# Run in development mode
export OPENAI_API_KEY=your-api-key-here
nomos run --config config.agent.yaml --tools tools.py

# Or serve with Docker
nomos serve --config config.agent.yaml --tools tools.py

# Or serve in detached mode
nomos serve --config config.agent.yaml --tools tools.py --detach
```

## Deployment

### Docker Base Image

NOMOS provides a base Docker image that you can use to quickly containerize your agents. The base image is available on Docker Hub as `chandralegend/nomos-base`.

To use the base image in your own agent:

1. Create a Dockerfile:

```dockerfile
FROM chandralegend/nomos-base:latest

# Copy your config file
COPY config.agent.yaml /app/config.agent.yaml

# Copy your tools
COPY tools.py /app/src/tools/
```

2. Build and run your container:

```bash
docker build -t my-nomos-agent .
docker run -e OPENAI_API_KEY=your-api-key-here -p 8000:8000 my-nomos-agent
```

The base image supports configuration via environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | Yes (if using OpenAI) |
| `CONFIG_URL` | URL to download agent configuration | No |
| `CONFIG_PATH` | Path to mounted configuration file | No |
| `PORT` | Server port (default: 8000) | No |
| `DATABASE_URL` | PostgreSQL connection URL | No |
| `REDIS_URL` | Redis connection URL | No |
| `ENABLE_TRACING` | Enable OpenTelemetry tracing (`true`/`false`) | No |
| `ELASTIC_APM_SERVER_URL` | Elastic APM server URL | If tracing enabled |
| `ELASTIC_APM_TOKEN` | Elastic APM Token | If tracing enabled |
| `SERVICE_NAME` | Service name for tracing | No (default: `nomos-agent`) |
| `SERVICE_VERSION` | Service version for tracing | No (default: `1.0.0`) |
| `NOMOS_LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, etc.) | No (default: `INFO`) |
| `NOMOS_ENABLE_LOGGING` | Enable logging (`true`/`false`) | No (default: `false`) |

### Tracing and Elastic APM Integration

NOMOS supports distributed tracing using [OpenTelemetry](https://opentelemetry.io/) and can export traces to [Elastic APM](https://www.elastic.co/apm/).

To enable tracing, set the following environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `ENABLE_TRACING` | Enable OpenTelemetry tracing (`true`/`false`) | No (default: `false`) |
| `ELASTIC_APM_SERVER_URL` | Elastic APM server URL | If tracing enabled |
| `ELASTIC_APM_TOKEN` | Elastic APM Token | If tracing enabled |
| `SERVICE_NAME` | Service name for tracing | No (default: `nomos-agent`) |
| `SERVICE_VERSION` | Service version for tracing | No (default: `1.0.0`) |

Example:

```bash
docker run \
  -e ENABLE_TRACING=true \
  -e ELASTIC_APM_SERVER_URL=http://your-apm-server:8200 \
  -e ELASTIC_APM_TOKEN=your-apm-token \
  -e SERVICE_NAME=my-nomos-agent \
  -e SERVICE_VERSION=1.0.0 \
  -e OPENAI_API_KEY=your-openai-key \
  -p 8000:8000 my-nomos-agent
```

### Persistent Storage and Session Management

NOMOS base image supports multiple options for session storage:

#### In-Memory Storage

The default storage mechanism is in-memory, which does not persist sessions between container restarts.

#### Redis Session Storage

For caching and distributed deployments, you can use Redis as a session store:

```bash
docker run \
  -e REDIS_URL=redis://redis:6379/0 \
  -e OPENAI_API_KEY=your-openai-key \
  -p 8000:8000 my-nomos-agent
```

#### PostgreSQL Persistent Storage

For fully persistent sessions that survive container restarts:

```bash
docker run \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@postgres/dbname \
  -e OPENAI_API_KEY=your-openai-key \
  -p 8000:8000 my-nomos-agent
```

### API Endpoints

NOMOS base image provides the following REST and WebSocket endpoints:

#### Server-side Session Management

- `POST /session` - Create a new session
- `POST /session/{session_id}/message` - Send a message to a session
- `WS /ws/{session_id}` - WebSocket connection for real-time interaction
- `DELETE /session/{session_id}` - End a session
- `GET /session/{session_id}/history` - Get session history

#### Client-side Session Management

- `POST /chat` - Stateless chat endpoint where the client maintains session state

For more details, see the [base image README](tools/base-image/README.md).

## Roadmap

See the [open issues](https://github.com/dowhiledev/nomos/issues) for a list of proposed features and known issues.

- [Top Feature Requests](https://github.com/dowhiledev/nomos/issues?q=label%3Aenhancement+is%3Aopen+sort%3Areactions-%2B1-desc) (Add your votes using the 👍 reaction)
- [Top Bugs](https://github.com/dowhiledev/nomos/issues?q=is%3Aissue+is%3Aopen+label%3Abug+sort%3Areactions-%2B1-desc) (Add your votes using the 👍 reaction)
- [Newest Bugs](https://github.com/dowhiledev/nomos/issues?q=is%3Aopen+is%3Aissue+label%3Abug)

## Support

If you have any questions or need help with NOMOS:

- [GitHub issues](https://github.com/dowhiledev/nomos/issues/new?assignees=&labels=question&template=04_SUPPORT_QUESTION.md&title=support%3A+)
- Join our [community discussions](https://github.com/dowhiledev/nomos/discussions)

## Project assistance

If you want to say **thank you** or/and support active development of NOMOS:

- Add a [GitHub Star](https://github.com/dowhiledev/nomos) to the project.
- Tweet about NOMOS.
- Write articles about the project on [Dev.to](https://dev.to/), [Medium](https://medium.com/) or your personal blog.

Together, we can make NOMOS **better**!

## Contributing

Contributions are welcome! Please open issues or pull requests on GitHub.

First off, thanks for taking the time to contribute! Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make will benefit everybody else and are **greatly appreciated**.

Please read our contribution guidelines (coming soon), and thank you for being involved!

## Authors & contributors

For a full list of all authors and contributors, see [the contributors page](https://github.com/dowhiledev/nomos/contributors).

## License

This project is licensed under the **MIT license**.

See [LICENSE](LICENSE) for more information.

## Acknowledgements

- Inspired by the open-source LLM community.
- Built with ❤️
