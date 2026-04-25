# jk-mcp-nwsl

[![CI](https://github.com/jedi-knights/jk-mcp-nwsl/actions/workflows/ci.yml/badge.svg)](https://github.com/jedi-knights/jk-mcp-nwsl/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://jedi-knights.github.io/jk-mcp-nwsl/)
[![Python](https://img.shields.io/badge/python-3.13-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

An MCP server that exposes NWSL (National Women's Soccer League) data through the ESPN public API. No API key required.

---

## Contents

- [Tools](#tools)
- [Requirements](#requirements)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Claude Code](#claude-code)
- [Claude Desktop](#claude-desktop)
- [Docker](#docker)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

## Tools

| Tool | Description |
|---|---|
| `get_teams` | List all active NWSL teams with IDs and abbreviations |
| `get_team` | Get details for a specific team by ESPN team ID |
| `get_scoreboard` | Get match scores, optionally filtered by date (`YYYYMMDD`) |
| `get_standings` | Get current league standings ordered by points |

All tools are read-only, idempotent, and call the ESPN public API with automatic retry and in-process caching.

---

## Requirements

- [Python 3.13+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

---

## Quickstart

```sh
git clone https://github.com/jedi-knights/jk-mcp-nwsl.git
cd jk-mcp-nwsl
uv sync
```

Run the server in stdio mode (the default — used by Claude Code and Claude Desktop):

```sh
uv run python -m nwsl.server
```

Run in HTTP mode (for networked or deployed access):

```sh
MCP_TRANSPORT=streamable-http uv run python -m nwsl.server
```

---

## Configuration

All configuration is via environment variables. None are required for local use.

| Variable | Default | Description |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | Transport mode: `stdio` or `streamable-http` |
| `HOST` | `0.0.0.0` | Bind address (HTTP transport only) |
| `PORT` | `8000` | TCP port (HTTP transport only) |
| `API_HOST` | `https://site.api.espn.com` | ESPN API base URL |
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Claude Code

Add the server to Claude Code from the repository root:

```sh
claude mcp add nwsl -- uv run --directory /path/to/jk-mcp-nwsl python -m nwsl.server
```

Or add it manually to your project's `.claude/settings.json`:

```json
{
  "mcpServers": {
    "nwsl": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/jk-mcp-nwsl", "python", "-m", "nwsl.server"]
    }
  }
}
```

Replace `/path/to/jk-mcp-nwsl` with the absolute path to your clone.

Once connected, you can ask Claude things like:

- *"What are the current NWSL standings?"*
- *"What was the score of the Portland Thorns match on June 1st?"*
- *"List all NWSL teams and their IDs."*

---

## Claude Desktop

Add the following to your Claude Desktop configuration file.

**Location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**Using uv (recommended if you have the repo cloned):**

```json
{
  "mcpServers": {
    "nwsl": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/jk-mcp-nwsl",
        "python", "-m", "nwsl.server"
      ]
    }
  }
}
```

**Using Docker:**

```json
{
  "mcpServers": {
    "nwsl": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "jk-mcp-nwsl:latest"]
    }
  }
}
```

Restart Claude Desktop after saving the config. The NWSL tools will appear in the tool picker.

---

## Docker

Build the image:

```sh
docker build -t jk-mcp-nwsl:latest .
```

Run in stdio mode (for MCP clients that spawn a subprocess):

```sh
docker run -i --rm jk-mcp-nwsl:latest
```

Run in HTTP mode:

```sh
docker run --rm -p 8000:8000 \
  -e MCP_TRANSPORT=streamable-http \
  jk-mcp-nwsl:latest
```

---

## Development

### Install dependencies

```sh
uv sync
```

### Invoke tasks

All common development workflows are available as `invoke` tasks. Run `uv run inv --list` to see all tasks.

| Task | Alias | Description |
|---|---|---|
| `uv run inv install` | `inv i` | Install project dependencies |
| `uv run inv lint` | `inv l` | Run ruff linter and format check |
| `uv run inv lint --fix` | `inv l --fix` | Auto-fix lint violations and reformat |
| `uv run inv test` | `inv t` | Run the full test suite |
| `uv run inv test -k <expr>` | `inv t -k <expr>` | Run tests matching an expression |
| `uv run inv test -x` | `inv t -x` | Stop after the first failure |
| `uv run inv coverage` | `inv v` | Run tests with coverage report (threshold: 90%) |
| `uv run inv coverage --report html` | | Generate an HTML coverage report in `htmlcov/` |
| `uv run inv check-complexity` | `inv cc` | Check cyclomatic complexity (max 7) |
| `uv run inv build` | `inv b` | Build wheel and sdist into `dist/` |
| `uv run inv build-image` | `inv bi` | Build the Docker image |
| `uv run inv dry-run` | `inv dr` | Preview the next release version |
| `uv run inv clean` | `inv c` | Remove build and coverage artifacts |

### Workflow

```sh
# Make changes, then verify everything passes before committing
uv run inv lint
uv run inv check-complexity
uv run inv coverage
```

### Project structure

```
src/nwsl/
├── server.py                  # entry point, transport selection, logging setup
├── adapters/
│   ├── inbound/
│   │   └── mcp_adapter.py     # FastMCP tools, request formatting
│   └── outbound/
│       ├── espn_adapter.py    # ESPN HTTP client
│       ├── retry_adapter.py   # retry decorator for transient failures
│       └── caching_adapter.py # in-process response cache
├── application/
│   └── service.py             # use cases, orchestration
├── domain/
│   ├── models.py              # Team, Match, Standing, etc.
│   └── exceptions.py         # NWSLNotFoundError, UpstreamAPIError
└── ports/
    └── outbound.py            # Protocol interfaces for driven adapters
```

The dependency direction flows inward: adapters → ports → domain. Nothing in `domain/` imports from adapters or the framework.

---

## Contributing

1. Fork the repository and clone your fork
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes following the existing patterns (hexagonal architecture, TDD, conventional commits)
4. Verify the full check suite passes: `uv run inv lint && uv run inv check-complexity && uv run inv coverage`
5. Open a pull request against `main`

All CI checks (lint, complexity, tests, coverage ≥ 90%) must pass before merge.

---

## License

MIT — see [LICENSE](LICENSE).
