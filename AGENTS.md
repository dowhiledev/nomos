# Repository Guidelines

## Project Structure & Module Organization
- Source: `nomos/` (core logic in `core.py`, CLI in `cli.py`, API server in `api/app.py`, models in `models/`, LLM providers in `llms/`, utilities in `utils/`, tools in `tools/`).
- Tests: `tests/` (pytest suite, fixtures in `tests/fixtures/`).
- Docs & Examples: `docs/`, examples/recipes in `cookbook/`.
- Dev tooling: `pyproject.toml` (ruff, pytest), `.pre-commit-config.yaml`, `Dockerfile`.

## Build, Test, and Development Commands
- Create env & install (dev): `uv sync --group dev` or `pip install -e .[dev]`.
- Lint: `ruff check .` (auto-fix: `ruff check . --fix`).
- Format: `ruff format .`.
- Type check: `mypy nomos tests`.
- Run tests: `pytest` (uses coverage by default via `pyproject.toml`).
- Fast tests: `pytest -q -n auto` (requires `pytest-xdist`).
- Run CLI: `nomos --help` or `python -m nomos.cli ...`.
- Run API (dev): `uvicorn nomos.api.app:app --reload`.

## Coding Style & Naming Conventions
- Python 3.10+. Indentation: 4 spaces. Line length: 100.
- Names: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Imports: sorted and grouped (ruff/isort). Prefer explicit exports and type hints; public APIs should be annotated (`py.typed` is included).
- Keep functions small and composable; avoid side effects in utilities.

## Testing Guidelines
- Framework: pytest with coverage (`--cov=nomos --cov-report=term-missing` via config).
- Location: place tests under `tests/` mirroring package paths; name files `test_*.py`.
- Use fixtures from `tests/fixtures/`; add new ones in that folder when shared.
- Aim for meaningful coverage on new/changed code; include API/CLI integration tests when applicable.

## Commit & Pull Request Guidelines
- Commits: imperative present (“Add …”, “Fix …”). Keep concise; include scope when helpful. Reference issues/PRs (e.g., `(#123)`).
- Pre-push: run `ruff check . --fix && ruff format . && mypy nomos && pytest` or `pre-commit run -a`.
- PRs: include clear description, linked issues, screenshots or logs for user-visible changes, and notes on backwards compatibility/config impacts.

## Security & Configuration Tips
- Keep secrets in environment variables; `.env` files are git-ignored. Never commit keys.
- Optional provider extras: install with `pip install .[openai,anthropic,serve,...]` or `uv sync --extra <name>` per `pyproject.toml`.
