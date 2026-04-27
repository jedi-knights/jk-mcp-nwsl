# jk-mcp-nwsl

[![CI](https://github.com/jedi-knights/jk-mcp-nwsl/actions/workflows/ci.yml/badge.svg)](https://github.com/jedi-knights/jk-mcp-nwsl/actions/workflows/ci.yml)
[![Badge](https://github.com/jedi-knights/jk-mcp-nwsl/actions/workflows/badge.yml/badge.svg)](https://github.com/jedi-knights/jk-mcp-nwsl/actions/workflows/badge.yml)
[![Coverage](https://img.shields.io/badge/Coverage-91.1%25-brightgreen)](https://jedi-knights.github.io/jk-mcp-nwsl/)
[![Python](https://img.shields.io/badge/python-3.13-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

AI assistants like Claude are knowledgeable, but they have a hard cutoff date — they cannot tell you today's NWSL standings, last night's scores, or which teams are fighting for a playoff spot right now. This project fixes that.

It is an **MCP server** — a plugin that gives Claude direct access to live NWSL data: scores, standings, rosters, player and team stats, historical seasons, awards, and more. Once installed, you can ask Claude natural-language questions about the National Women's Soccer League and get accurate, up-to-date answers. No subscription, no API key, and no knowledge of programming required to use it.

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
| `get_team` | Get details for a specific team |
| `get_roster` | Get a team's active roster — jersey numbers, positions, ages, citizenships |
| `get_scoreboard` | Get match scores for a single day, a date range, or the current matchweek |
| `get_team_schedule` | Get every match for a team in the current season — past results and upcoming fixtures |
| `get_match_details` | Get one match's full details — score, venue, attendance, goals, substitutions, cards |
| `get_standings` | Get current NWSL league standings |
| `get_historical_standings` | Get final standings for any prior season (2016 onward) |
| `get_challenge_cup_standings` | Get NWSL Challenge Cup standings for any year (2020 onward) |
| `get_player_leaderboards` | Get top players ranked by any stat — goals, assists, saves, xG, etc. |
| `get_team_season_stats` | Get team season aggregates ranked by any stat — points, goals, possession, etc. |
| `get_news` | Get recent NWSL news articles |
| `get_award_articles` | Get recent award announcements — Best XI, Player of the Month, Rookie of the Month |
| `get_strength_of_schedule` | Get a team's average opponent points-per-game across matches already played |
| `get_results_by_opponent_tier` | Split a team's W-L-T by current top, middle, and bottom standings tiers |
| `get_adjusted_points_per_game` | Get a team's raw PPG alongside an opponent-quality-adjusted PPG |

All tools are read-only and idempotent. Backed by three sources: the **ESPN public API** (teams, schedule, scores, league standings, news), the unofficial **SDP/Opta feed** that powers nwslsoccer.com (player stats, team aggregates, historical standings, Challenge Cup), and the **official NWSL CMS** (award articles). Endpoints and IDs were reverse-engineered from the public site's widget bundles — no auth required, but the SDP and CMS contracts are not officially documented; if a tool stops working the upstream format likely changed.

The last three tools (`get_strength_of_schedule`, `get_results_by_opponent_tier`, `get_adjusted_points_per_game`) are **derived analytics** — pure functions over the live ESPN standings + team schedule that surface schedule-strength context the raw table doesn't show. They're inspired by NCAA RPI's idea of weighting results by opponent quality but adapted to the realities of a 16-team pro league (no non-conference adjustments, no opponent-of-opponent recursion, current standings used to define tiers).

---

## Example Prompts

Once the server is connected to Claude, try prompts like these.

### Standings

> Who is leading the NWSL standings right now?

> Which teams are currently in a playoff position?

> Show me the full standings with goal differential.

> Who won the 2018 NWSL Regular Season?

> What were the final 2017 standings?

> Show me the 2022 NWSL Challenge Cup standings.

### Scores and results

> What NWSL matches are scheduled for today?

> What were the scores from this past weekend's NWSL games?

> Show me all the NWSL results from June 15th, 2025.

> Did the Portland Thorns win their most recent match?

> When does Bay FC play next?

### Match details

> Who scored in the most recent Portland-Carolina match?

> What was the attendance at Denver's home opener?

> Show me all the goals, cards, and substitutions from the most recent Gotham match.

> Who got the assists on Angel City's goals last weekend?

### Teams and rosters

> List all the current NWSL teams.

> Who's on the Portland Thorns roster?

> Which Angel City players are international?

> Show me Kansas City Current's goalkeepers.

> Give me the ESPN ID for the Washington Spirit.

### Player and team statistics

> Who is the top scorer in the NWSL right now?

> Which player has the most assists this season?

> Show me the top 10 NWSL players by minutes played.

> Who leads the league in saves?

> Which NWSL team has the best passing accuracy this season?

> Compare Portland and Kansas City by points and goals scored this season.

### News and awards

> What's the latest NWSL news?

> Who won March Player of the Month?

> Show me the most recent Best XI of the Month.

> Who was named NWSL Rookie of the Month?

### Schedule strength and opponent quality

> Which team has played the toughest schedule so far this season?

> What's Portland's strength of schedule? List the opponents they've faced.

> How does Bay FC stack up — have they played weak opponents or strong ones?

> Show me Gotham's record against the current top 5 teams in the standings.

> How has Kansas City Current done against the bottom of the table compared to the top?

> Split Angel City's results into top, middle, and bottom standings tiers (use a tier size of 4).

> Group Portland's opponents into top 3, middle, and bottom 3 — how do they stack up against the league extremes?

> Compare San Diego and Seattle on adjusted points-per-game — who has earned their points the hard way?

> Is Houston's record more impressive than the standings suggest, given who they've played?

> What's the league average PPG and how does Washington's adjusted PPG compare?

### Multi-step

> Who is the top scorer in the NWSL right now, and what was their team's last match result?

> How are the Portland Thorns doing in the standings, and who scored their last goal?

> Compare the 2024 NWSL champion to the 2018 NWSL champion — same franchise, or different?

> Which team currently leads the league, and what's their roster's average age?

---

## Production

A live instance of this server is already running at:

```
https://jk-mcp-nwsl.fly.dev/mcp
```

No installation, no Python, no cloning required. Connect your MCP client directly to the URL and you are done.

### Claude Code

Install globally (recommended) so the server is available in every project:

```sh
claude mcp add --transport http --scope user nwsl https://jk-mcp-nwsl.fly.dev/mcp
```

Verify it's registered and healthy:

```sh
claude mcp list
```

You should see `nwsl: https://jk-mcp-nwsl.fly.dev/mcp (HTTP) - ✓ Connected`. Restart Claude Code if you had it open.

**Other scopes:**

- Drop `--scope user` to register only for the current project (`cwd` must match when you run `claude`).
- Or commit a `.mcp.json` to the repo root to share with collaborators:

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

> Prefer the hosted server? See [Production → Claude Code](#claude-code) above — it's a single command and requires no clone.

To run the server from your local clone instead, install it globally:

```sh
claude mcp add --scope user nwsl -- uv run --directory /path/to/jk-mcp-nwsl python -m nwsl.server
```

Replace `/path/to/jk-mcp-nwsl` with the absolute path to your clone. Verify with `claude mcp list`.

**Other scopes:**

- Drop `--scope user` to register only for the current project.
- Or commit a `.mcp.json` to the repo root for collaborators:

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

See [Example Prompts](#example-prompts) for ideas on what to ask.

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
