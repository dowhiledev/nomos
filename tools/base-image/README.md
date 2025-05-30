# Nomos Base Image

Official base image for building Nomos (Simple Orchestrated Flow Intelligence Agent) agents.

## Features

- Pre-installed Nomos agent framework
- Configurable via environment variables or mounted config files
- Built-in support for OpenAI, Mistral, and Gemini LLMs
- FastAPI-based HTTP and WebSocket endpoints
- Redis support for session management
- SQLModel-based persistent storage
- Session management with support for both Redis and PostgreSQL

## Quick Start

```bash
docker pull chandralegend/nomos-base:latest
```

Create a Dockerfile:
```dockerfile
FROM chandralegend/nomos-base:latest
COPY config.agent.yaml /app/config.agent.yaml
```

## Configuration Options

### Using URL Configuration
```bash
docker run -e OPENAI_API_KEY=your-key \
          -e CONFIG_URL=https://example.com/config.yaml \
          -p 8000:8000 your-image
```

### Using Local Configuration
```bash
docker run -e OPENAI_API_KEY=your-key \
          -v $(pwd)/config.agent.yaml:/app/config.agent.yaml \
          -p 8000:8000 your-image
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | Yes (if using OpenAI) |
| `CONFIG_URL` | URL to download agent configuration | No |
| `CONFIG_PATH` | Path to mounted configuration file | No |
| `PORT` | Server port (default: 8000) | No |
| `DATABASE_URL` | PostgreSQL connection URL | No |
| `REDIS_URL` | Redis connection URL | No |
| `ENABLE_TRACING` | Enable OpenTelemetry tracing (`true`/`false`) | No |
| `ELASTIC_APM_SERVER_URL` | Elastic APM server URL (e.g. `http://localhost:8200`) | If `ENABLE_TRACING` is set to `true` |
| `ELASTIC_APM_TOKEN` | Elastic APM Token | If `ENABLE_TRACING` is set to `true` |
| `SERVICE_NAME` | Name of the service for tracing | No (default: `Nomos-agent`) |
| `SERVICE_VERSION` | Version of the service for tracing | No (default: `1.0.0`) |

## Storage Options

### Redis Session Store
Enable Redis session storage by setting the `REDIS_URL` environment variable:
```bash
docker run -e REDIS_URL=redis://redis:6379/0 ...
```

### PostgreSQL Database
Enable persistent storage by setting the `DATABASE_URL` environment variable:
```bash
docker run -e DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname ...
```

## API Endpoints

### Server-side Session Management
- `POST /session` - Create a new session
- `POST /session/{session_id}/message` - Send a message to a session
- `WS /ws/{session_id}` - WebSocket connection for real-time interaction
- `DELETE /session/{session_id}` - End a session
- `GET /session/{session_id}/history` - Get session history

### Client-side Session Management
- `POST /chat` - Stateless chat endpoint where the client maintains session state

## Tracing and Elastic APM

Nomos base image supports distributed tracing using OpenTelemetry and can export traces to Elastic APM.

To enable tracing, set the following environment variables:

- `ENABLE_TRACING=true`
- `ELASTIC_APM_SERVER_URL=http://your-apm-server:8200`
- `ELASTIC_APM_TOKEN=your-apm-token`
- Optionally, set `SERVICE_NAME` and `SERVICE_VERSION` for trace metadata.

When enabled, traces for agent sessions, tool calls, and LLM interactions will be sent to your Elastic APM instance.

### Example

```bash
docker run \
  -e ENABLE_TRACING=true \
  -e ELASTIC_APM_SERVER_URL=http://localhost:8200 \
  -e ELASTIC_APM_TOKEN=your-apm-token \
  -e OPENAI_API_KEY=your-openai-key \
  -p 8000:8000 your-image
```

## Tags

- `latest`: Most recent stable version
- `x.y.z`: Specific version releases

## GitHub Repository

For more information, visit [Nomos GitHub Repository](https://github.com/Nomos-hq/Nomos)

## License

MIT License
