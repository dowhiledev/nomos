# Configuration Guide

NOMOS provides flexible configuration options through both Python API and YAML files, supporting a spectrum from no-code to full-code development.

## Python API Configuration

### Basic Agent Setup

```python
from nomos import Agent, AgentConfig, Step, Route
from nomos.llms import OpenAI
from nomos.models.flow import FlowConfig
from math import sqrt, pow

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
        available_tools=["get_time", "sqrt"],
        routes=[Route(target="calculation", condition="User wants to do math"),
                Route(target="end", condition="User is done")],
    ),
    Step(
        step_id="calculation",
        description="Perform mathematical calculations for the user.",
        available_tools=["sqrt", "pow"],
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
                "retriever": {"method": "embedding", "kwargs": {"k": 3}}
            }
        }
    )
]

config = AgentConfig(
    name="clockbot",
    llm={"provider": "openai", "model": "gpt-4o-mini"},
    steps=steps,
    flows=flows,
    start_step_id="start",
    persona="You are a friendly assistant that can tell time and perform calculations.",
    max_errors=3,
    max_iter=5,
)

llm = config.get_llm()
agent = Agent.from_config(config, llm, [get_time, sqrt, pow])
session = agent.create_session()
# ... interact with session.next(user_input)
```

## YAML Configuration

### Basic YAML Config

```yaml
name: utility-bot
persona: You are a helpful utility bot that can perform various calculations and data operations.
steps:
  - step_id: start
    description: Handle user requests for mathematical operations or data processing.
    available_tools:
      - sqrt
      - load_json
      - combinations
    routes:
      - target: end
        condition: User is done with calculations
  - step_id: end
    description: Say goodbye to the user.
start_step_id: start
max_errors: 3  # Maximum consecutive errors before stopping
```

### Advanced YAML Configuration

See [`cookbook/examples/barista/config.agent.yaml`](../cookbook/examples/barista/config.agent.yaml) for a comprehensive example.

## LLM Configuration

### Supported Providers

```python
from nomos.llms import OpenAI, Mistral, Gemini, Ollama, HuggingFace

# Choose your LLM provider
llm = OpenAI(model="gpt-4o-mini")
llm = Mistral(model="mistral-medium")
llm = Gemini(model="gemini-pro")
llm = Ollama(model="llama3")
llm = HuggingFace(model="meta-llama/Meta-Llama-3-8B-Instruct")
```

### YAML LLM Configuration

```yaml
llm:
  provider: openai
  model: gpt-4o-mini
```

### Generate YAML Schema

Create a JSON schema for your configuration to enable editor validation and autocompletion:

```bash
nomos schema --output agent.schema.json
```

Include the schema in your YAML file:

```yaml
# yaml-language-server: $schema=./agent.schema.json
or
# yaml-language-server: $schema=https://https://raw.githubusercontent.com/dowhiledev/nomos/refs/heads/main/support/schemas/.nomos.json
```

## Tool Configuration

### New in v0.2.4: Integrated Tool Configuration

As of version 0.2.4, you can specify tools directly in your agent configuration file:

```yaml
name: my-agent
persona: A helpful assistant
steps:
  - step_id: start
    # ... step configuration
start_step_id: start

# Tool configuration - NEW in v0.2.4
tools:
  tool_files:
    - "barista_tools.py"    # Python module
    - "tools.my_tools"      # File path
  external_tools:
    - tag: "@pkg/itertools.combinations"
      name: "combinations"
    - tag: "@crewai/FileReadTool"
      name: "file_read_tool"
    - tag: "@langchain/google_search"
      name: "google_search"
  tool_arg_descriptions:
    add_to_cart:
      coffee_type: "Coffee type (e.g., Espresso, Latte, Cappuccino)"
      size: "Size of the coffee (Small, Medium, Large)"
```

### Custom Tool Files

You can organize your own tools in Python modules:

```python
# tools/my_tools.py
def greet(name: str) -> str:
    """Return a simple greeting."""
    return f"Hello {name}!"

tools = [greet]
```

### Tool Loading Options

**Option 1: Configuration File (Recommended)**
```yaml
# In config.agent.yaml
tools:
  tool_files:
    - "my_tools"              # Load as module
    - "tools/custom_tools.py" # Load as file path
```

**Option 2: CLI Flags (Legacy)**
```bash
nomos run --config config.agent.yaml --tools tools/my_tools.py
```

## Step Examples

You can provide decision examples for any step. Each example contains the user
context and the expected decision. NOMOS retrieves relevant examples using
embeddings and includes them in the system prompt to guide the model.

```yaml
steps:
  - step_id: start
    description: Initial step
    examples:
      - context: "User asks for the time"
        decision: "Answer with the current time."
        visibility: always
      - context: "sqrt 4"
        decision: "Call sqrt tool"
        visibility: dynamic
```

Use the `max_examples` and `threshold` settings in `AgentConfig` to control how
many examples are displayed and the minimum similarity required.

## External Tool Integration

NOMOS allows you to reference Python package functions, CrewAI tools, and LangChain tools directly in your configuration.

### Benefits

1. **No-code/low-code development**: Use existing Python functions without writing wrapper code
2. **Automatic documentation**: Function docstrings are used to generate tool descriptions and parameter documentation
3. **Simplified configuration**: Easily reference any Python function in your environment

> **NOTE**: Make sure the package is installed in your environment and function returns an output that is string representable.

## Error Handling Configuration

```yaml
name: my-agent
# ... other config
max_errors: 3  # Maximum consecutive errors before stopping
max_iter: 5   # Maximum iterations per interaction
```

## Environment Variables

Common environment variables for NOMOS agents:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | If using OpenAI |
| `MISTRAL_API_KEY` | Mistral API key | If using Mistral |
| `GOOGLE_API_KEY` | Google API key | If using Gemini |
| `HUGGINGFACE_API_TOKEN` | HuggingFace token | If using HuggingFace |

## Configuration Examples

More configuration examples are available in the [`cookbook/examples/`](../cookbook/examples/) directory:

- [Barista Agent](../cookbook/examples/barista/) - Complete coffee ordering workflow
- [Financial Advisor](../cookbook/examples/financial-advisor/) - Budget planning and financial advice
- [General Bot](../cookbook/examples/general-bot/) - Basic conversational agent
- [Travel Planner](../cookbook/examples/travel-itinery-planner/) - Travel planning assistant
