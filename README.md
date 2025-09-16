<h1>
  <a href="https://github.com/dowhiledev/nomos">
    <img src="docs/assets/banner.jpg" alt="NOMOS">
  </a>
</h1>

<div>

![PyPI - Version](https://img.shields.io/pypi/v/nomos?style=flat-square)
[![npm version](https://img.shields.io/npm/v/nomos-sdk.svg?style=flat-square)](https://www.npmjs.com/package/nomos-sdk)
[![codecov](https://codecov.io/gh/dowhiledev/nomos/graph/badge.svg?token=MXRK9HGE5R&style=flat-square)](https://codecov.io/gh/dowhiledev/nomos)
[![Test](https://github.com/dowhiledev/nomos/actions/workflows/test.yml/badge.svg?style=flat-square)](https://github.com/dowhiledev/nomos/actions/workflows/test.yml)
[![Release](https://github.com/dowhiledev/nomos/actions/workflows/publish.yml/badge.svg?style=flat-square)](https://github.com/dowhiledev/nomos/actions/workflows/publish.yml)
[![Docker Image](https://img.shields.io/badge/ghcr.io-nomos-blue?style=flat-square)](https://github.com/dowhiledev/nomos/pkgs/container/nomos)
[![Open Issues](https://img.shields.io/github/issues-raw/dowhiledev/nomos?style=flat-square)](https://github.com/dowhiledev/nomos/issues)

</div>

> [!NOTE]
> Looking for client-side integration? Check out our [TypeScript/JavaScript SDK](support/ts-sdk/README.md).

**NOMOS** is a framework for building advanced LLM-powered assistants with structured, multi-step workflows. It helps you create sophisticated AI agents through configurable flows, tools, and integrations — making complex agent development accessible from no-code to full-code approaches.

```bash
pip install nomos[cli]
```

To learn more about NOMOS, check out [the documentation](docs/md/). If you're looking for quick prototyping, try our [Playground](https://nomos-builder.vercel.app/) for drag-and-drop agent creation.

<details>
<summary>Table of Contents</summary>

- [Why use NOMOS?](#why-use-nomos)
- [NOMOS Ecosystem](#nomos-ecosystem)
- [Key Features](#key-features)
- [Documentation](#documentation)
- [Additional Resources](#additional-resources)

**[Complete Documentation](docs/md/) | [Try Playground](https://nomos-builder.vercel.app/) | [Quick Start Guide](docs/md/getting-started.md)**

</details>

---

## Why use NOMOS?

NOMOS helps developers build sophisticated AI agents through structured workflows and configurable components, making complex agent development accessible to teams of all skill levels.

| Use Case | Description |
|----------|-------------|
| **Multi-step Workflows** | Complex, stateful interactions with specialized tools and intelligent routing |
| **Structured Data** | Define reusable schemas for consistent, validated responses across agents |
| **Rapid Prototyping** | No-code Playground → YAML config → Full Python implementation |
| **Tool Integration** | Python functions, CrewAI, LangChain tools, External APIs with auto-documentation |
| **Production Deployment** | Built-in session management, error handling, and monitoring |

## NOMOS Ecosystem

| Component | Description | Link |
|-----------|-------------|------|
| **Playground** | Drag-and-drop flow designer for rapid prototyping | [Try it live →](https://nomos-builder.vercel.app/) |
| **TypeScript SDK** | Full-featured client library for web and Node.js | [Documentation →](support/ts-sdk/README.md) |
| **Docker Images** | Pre-configured containers with Redis, PostgreSQL support (GitHub Packages) | [Deployment Guide →](docs/md/deployment.md#docker-base-image) |
| **CLI Tools** | Complete toolkit: `init`, `run`, `serve`, `test`, `validate`, `schema` | [CLI Reference →](docs/md/cli-usage.md) |

## Key Features

| Category | Feature | Description |
|----------|---------|-------------|
| **Architecture** | Step-based Flows | Define agent behavior as sequences of steps with tools and transitions |
| | Advanced Flow Management | Organize steps into flows with shared context and components |
| | Flow Memory | Each flow maintains context with intelligent cross-flow summarization |
| **Development** | Multiple Config Options | Python API or declarative YAML configuration |
| | Playground | Drag-and-drop interface for designing flows **[Try it live →](https://nomos-builder.vercel.app/)** |
| | Interactive CLI | Bootstrap agents with `nomos init`, run with `nomos run` |
| **Tools & Integration** | Tool Integration | Register Python functions, packages, CrewAI, External APIs or LangChain tools |
| | Auto Documentation | Tool descriptions generated from docstrings |
| | External Packages | Reference any Python package function via configuration |
| | External API Tools | Use any REST API with ease (No wrapping needed.) |
| **LLM Support** | Multiple Providers | OpenAI, Mistral, Gemini, Ollama, and HuggingFace |
| | Structured Responses | Step-level answer models for JSON/object responses |
| | External Schemas | Define reusable schemas in JSON or Python files |
| | Persona-driven | Consistent, branded agent responses |
| | Decision Examples | Retrieve relevant examples to guide step decisions |
| **Production Ready** | Session Management | Redis/PostgreSQL storage for conversation persistence |
| | Error Handling | Built-in recovery with configurable retry limits |
| | API Integration | FastAPI endpoints for web and WebSocket interaction |
| | Monitoring | Elastic APM tracing and distributed monitoring |
| | Docker Deployment | Pre-built base image for rapid deployment |
| **Extensibility** | Custom Components | Build your own tools, steps, and integrations |
| | Scalable Design | Horizontal scaling with stateless architecture |


## Documentation

For detailed information, check out our comprehensive guides:

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/md/getting-started.md) | Installation, setup, and your first agent |
| [CLI Usage](docs/md/cli-usage.md) | Complete command-line interface guide |
| [Configuration](docs/md/configuration.md) | Python API and YAML configuration |
| [Flow Management](docs/md/flow-management.md) | Advanced workflow organization |
| [LLM Support](docs/md/llm-support.md) | Supported models and providers |
| [Examples](docs/md/examples.md) | Real-world implementation examples |
| [Deployment](docs/md/deployment.md) | Production deployment strategies |
| [Community](docs/md/community.md) | Contributing, support, and project information |

## Additional Resources

- **[Tutorials](docs/md/getting-started.md)**: Step-by-step guides for getting started with NOMOS, from installation to your first agent.
- **[How-to Guides](docs/md/)**: Quick, actionable code snippets for common tasks like tool integration, flow management, and deployment.
- **[Examples](docs/md/examples.md)**: Real-world implementations including a barista ordering system, financial advisor, and travel planner.
- **[API Reference](docs/md/configuration.md)**: Detailed documentation on Python API and YAML configuration options.
- **[CLI Reference](docs/md/cli-usage.md)**: Complete command-line interface documentation for development and deployment.

Join the NOMOS community! For roadmap, support, contributing guidelines, and more, see our [Community Guide](docs/md/community.md).

[![Discord Banner 2](https://discord.com/api/guilds/1393886830553731183/widget.png?style=banner2)](https://discord.com/invite/KEWVDFrvKS?utm_source=Discord%20Widget&utm_medium=Connect)
