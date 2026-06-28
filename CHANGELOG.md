# Changelog

## 0.8.0 (2026-06-28)

### Features

- **tools:** extended annotations — sensitivity, cost_class, rate_limit_class (P1) (d008135)

## 0.7.0 (2026-06-28)

### Features

- **authorization:** inbound port + adapter consulted on every tool dispatch (P1) (e19965f)

### Bug Fixes

- **authorization:** split helpers to satisfy cyclomatic-complexity cap (81f2255)

## 0.6.0 (2026-06-28)

### Features

- **security:** bearer token auth on streamable-http transport (P1) (fa391c4)

### Bug Fixes

- **security:** apply ruff format (1cf386e)

## 0.5.0 (2026-06-27)

### Features

- **observability:** wire OpenTelemetry tracing for MCP server (b39f4b4)

## 0.4.0 (2026-06-21)

### Features

- **server:** serve MCP at /mcp/nwsl (env MCP_PATH) (#20) (a41a3e3)

## 0.3.4 (2026-06-21)

### Bug Fixes

- **fly:** make app private behind the api-gateway (#18) (a004da7)

## 0.3.3 (2026-04-27)

### Bug Fixes

- **espn-adapter:** include upcoming fixtures in team schedule (#17) (f852174)

## 0.3.2 (2026-04-26)

### Bug Fixes

- use ESPN status state, expose match IDs, drop draft tool (#16) (c1f9633)

## 0.3.1 (2026-04-26)

### Bug Fixes

- team-schedule score parsing + release-workflow 404 annotation (#15) (2b271ae)
