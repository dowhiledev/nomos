"""Constants for Nomos."""

from .models.agent import Route, Step

DEFAULT_SYSTEM_MESSAGE = (
    "Your task is to decide the next action based on the current step, user input and history."
)

DEFAULT_PERSONA = (
    "You are a helpful assistant, kind and polite. Use human-like natural language when responding."
)

PERIODICAL_SUMMARIZATION_SYSTEM_MESSAGE = (
    "Your task is to summarize the a list of Messages, Tool calls with results. (Context)"
    "Identify the most important information and summarize it in a concise manner."
    "Do not include unnecessary details or irrelevant information."
)

LLM_CHOICES = {
    "OpenAI": {
        "provider": "openai",
        "model": "gpt-4o-mini",
    },
    "AzureOpenAI": {
        "provider": "azure",
        "model": "gpt-4o-mini",
    },
    "Mistral": {
        "provider": "mistral",
        "model": "ministral-8b-latest",
    },
    "Google": {
        "provider": "google",
        "model": "gemini-2.0-flash",
    },
    "Ollama": {
        "provider": "ollama",
        "model": "llama3",
    },
    "Anthropic": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
    },
    "Groq": {
        "provider": "groq",
        "model": "llama3-8b-8192",
    },
    "HuggingFace": {
        "provider": "huggingface",
        "model": "",
    },
    "Cohere": {
        "provider": "cohere",
        "model": "command-a-03-2025",
    },
}

TEMPLATES = {
    "basic": {
        "name": "basic_agent",
        "persona": "A basic agent that can handle simple tasks and conversations.",
        "steps": [
            Step(
                step_id="start",
                description="Greet the user and understand their needs",
                available_tools=[],
                routes=[Route(target="help", condition="User needs assistance")],
            ),
            Step(
                step_id="help",
                description="Provide assistance to the user",
                available_tools=[],
                routes=[Route(target="end", condition="Task completed")],
            ),
            Step(
                step_id="end",
                description="End the conversation politely",
                available_tools=[],
                routes=[],
            ),
        ],
    },
}

PRIMARY_COLOR = "cyan"
SUCCESS_COLOR = "green"
WARNING_COLOR = "yellow"
ERROR_COLOR = "red"
