# CLI Reference

SentinelAI provides a CLI for running experiments without writing code.

## Installation

```bash
pip install sentinel-ai
sentinelai --version
```

## Commands

### `sentinelai demo`

Run a quick demo experiment to see SentinelAI in action.

```bash
sentinelai demo --chaos-level 0.5
sentinelai demo --chaos-level 0.75 --verbose
```

| Option | Description | Default |
|--------|-------------|---------|
| `-c, --chaos-level` | Chaos intensity (0.0–2.0) | 0.5 |
| `-v, --verbose` | Verbose output | off |

### `sentinelai init`

Scaffold a new chaos test project.

```bash
sentinelai init my-chaos-tests
```

Creates:

- `scenarios/sample.json` — sample scenario
- `agent.py` — sample agent with tools
- `sentinelai.json` — configuration file

### `sentinelai run`

Run a chaos experiment from a scenario file.

```bash
sentinelai run scenarios/search.json --chaos-level 0.75
sentinelai run scenarios/critical.json -f html -o report.html
```

| Option | Description | Default |
|--------|-------------|---------|
| `-a, --agent` | Agent module path (`module:class`) | — |
| `-c, --chaos-level` | Chaos intensity (0.0–2.0) | 1.0 |
| `-n, --iterations` | Number of iterations | 1 |
| `-o, --output` | Output file path | — |
| `-f, --format` | Report format: `json`, `markdown`, `html`, `terminal` | terminal |
| `-v, --verbose` | Verbose output | off |

### `sentinelai stress`

Run stress tests across multiple chaos levels.

```bash
sentinelai stress scenarios/critical.json --levels 0.1 0.5 1.0 --iterations 50
```

| Option | Description | Default |
|--------|-------------|---------|
| `-a, --agent` | Agent module path | — |
| `-n, --iterations` | Iterations per chaos level | 100 |
| `-l, --levels` | Chaos levels to test | 0.1 0.25 0.5 0.75 1.0 |
| `-o, --output` | Output file path | — |
| `-v, --verbose` | Verbose output | off |
