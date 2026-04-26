# jk-mcp-nwsl

[![CI](https://github.com/jedi-knights/jk-mcp-nwsl/actions/workflows/ci.yml/badge.svg)](https://github.com/jedi-knights/jk-mcp-nwsl/actions/workflows/ci.yml)
[![Badge](https://github.com/jedi-knights/jk-mcp-nwsl/actions/workflows/badge.yml/badge.svg)](https://github.com/jedi-knights/jk-mcp-nwsl/actions/workflows/badge.yml)
[![Coverage](https://img.shields.io/badge/Coverage-93.4%25-brightgreen)](https://jedi-knights.github.io/jk-mcp-nwsl/)
[![Python](https://img.shields.io/badge/python-3.13-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

AI assistants like Claude are knowledgeable, but they have a hard cutoff date — they cannot tell you today's NWSL standings, last night's scores, or which teams are fighting for a playoff spot right now. This project fixes that.

It is an **MCP server** — a plugin that gives Claude a direct connection to live NWSL data from the ESPN public API. Once installed, you can ask Claude natural-language questions about the National Women's Soccer League and get accurate, up-to-date answers. No subscription, no API key, and no knowledge of programming required to use it.

---

## Contents

- [Tools](#tools)
- [Example Prompts](#example-prompts)
- [Production](#production)
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

## Example Prompts

Once the server is connected to Claude, try prompts like these.

### Standings

> Who is leading the NWSL standings right now?

> Which teams are currently in a playoff position?

> How does the bottom half of the NWSL table look?

> Show me the full standings with goal differential.

### Scores and results

> What NWSL matches are scheduled for today?

> What were the scores from this past weekend's NWSL games?

> Show me all the NWSL results from June 15th, 2025.

> Did the Portland Thorns win their most recent match?

### Teams

> List all the current NWSL teams.

> What city does the team with abbreviation "NCC" play in?

> Give me the ESPN ID for the Washington Spirit.

### Multi-step

> Which team is top of the table, and what was their last result?

> How are the Portland Thorns doing in the standings, and what were their recent scores?

> Which NWSL teams have the best goal differential, and who played on the most recent matchday?

---

## Production

A live instance of this server is already running at:

```
https://jk-mcp-nwsl.fly.dev/mcp
```

No installation, no Python, no cloning required. Connect your MCP client directly to the URL and you are done.

### Claude Code

```sh
claude mcp add --transport http nwsl https://jk-mcp-nwsl.fly.dev/mcp
```

Or add it manually to your project's `.claude/settings.json`:

```json
{
  "mcpServers": {
    "nwsl": {
      "type": "http",
      "url": "https://jk-mcp-nwsl.fly.dev/mcp"
    }
  }
}
```

### Claude Desktop

Add the following to your Claude Desktop configuration file.

**Location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "nwsl": {
      "type": "streamable-http",
      "url": "https://jk-mcp-nwsl.fly.dev/mcp"
    }
  }
}
```

Restart Claude Desktop after saving. The NWSL tools will appear in the tool picker.

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

Replace `/path/to/jk-mcp-nwsl` with the absolute path to your clone. See [Example Prompts](#example-prompts) for ideas on what to ask.

---

## Claude Desktop

### Install Claude Desktop

**With Homebrew (macOS):**

```sh
brew install --cask claude
```

**Without Homebrew:**

Download the installer for your platform from [claude.ai/download](https://claude.ai/download) and follow the on-screen instructions:

- macOS: open the downloaded `.dmg` and drag **Claude** into `/Applications`
- Windows: run the downloaded `.exe` installer

Launch Claude Desktop once and sign in before continuing — this creates the configuration directory referenced below.

### Configure Claude Desktop to use this MCP server

Pick the option that matches how you want to run the server: **hosted** (no install), **uv** (local clone), or **Docker** (containerized). Then follow the four steps below.

#### 1. Open the Claude Desktop config file

The fastest way is from inside Claude Desktop: **Settings → Developer → Edit Config**. This opens (and creates, if needed) the file in your default editor.

You can also open it directly:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

If the file does not exist yet, create it with `{}` as its contents.

#### 2. Add the `nwsl` server entry

Merge **one** of the following snippets into the top-level `mcpServers` object. If `mcpServers` does not exist, add the whole block as shown.

**Option A — Hosted (easiest, no install):**

```json
{
  "mcpServers": {
    "nwsl": {
      "type": "streamable-http",
      "url": "https://jk-mcp-nwsl.fly.dev/mcp"
    }
  }
}
```

**Option B — Local clone with `uv`:**

Replace `/path/to/jk-mcp-nwsl` with the absolute path to your clone. If `uv` is not on Claude Desktop's `PATH`, use the absolute path to the binary (`which uv` will show it — typically `/opt/homebrew/bin/uv` on Apple Silicon or `/usr/local/bin/uv` on Intel Macs).

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

**Option C — Docker:**

Build the image first (see [Docker](#docker)), then:

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

#### 3. Save and fully restart Claude Desktop

Quit Claude Desktop completely (**⌘Q** on macOS, or right-click the tray icon → **Quit** on Windows) and relaunch it. A simple window close is not enough — the MCP servers are only loaded on launch.

#### 4. Verify the connection

Open a new chat and click the tools / plug icon in the message bar. You should see **nwsl** listed with four tools: `get_teams`, `get_team`, `get_scoreboard`, `get_standings`. Try a prompt from [Example Prompts](#example-prompts) to confirm it works end-to-end.

If the server does not appear, check the Claude Desktop logs:

- **macOS:** `~/Library/Logs/Claude/mcp*.log`
- **Windows:** `%APPDATA%\Claude\logs\mcp*.log`

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
