# Roadmap

## Completed (v0.5.0) :white_check_mark:

- :white_check_mark: Core chaos engine with fault injection
- :white_check_mark: 5 fault injectors — tool failure, delay, hallucination, context corruption, budget exhaustion
- :white_check_mark: Framework wrappers — CrewAI, AutoGen, LangChain, LangGraph, Claude Agent SDK
- :white_check_mark: MTTR, reliability scoring, recovery quality metrics
- :white_check_mark: Multi-format reporting (terminal, JSON, Markdown, HTML)
- :white_check_mark: CLI with `demo`, `run`, `stress`, `init` commands
- :white_check_mark: Comprehensive test suite (unit, integration, BDD, E2E)
- :white_check_mark: LangGraph node-level chaos injection
- :white_check_mark: Advanced metrics (latency percentiles, error budgets, SLO tracking)
- :white_check_mark: ML-powered Adaptive Chaos Scheduling (Multi-Armed Bandit)
- :white_check_mark: Thread-safe metrics collectors and injectors
- :white_check_mark: Pre-commit hooks and expanded CI matrix (Python 3.10–3.12)

## In Progress (v0.6.x) :arrows_counterclockwise:

- :arrows_counterclockwise: Async chaos engine and experiment runner
- :arrows_counterclockwise: Entry-point based plugin system for custom injectors
- :arrows_counterclockwise: Interactive HTML dashboard with Chart.js
- :arrows_counterclockwise: OpenTelemetry metrics export
- :arrows_counterclockwise: CLI upgrade with `typer` + `rich`

## Future (v0.7.x+) :clipboard:

- :clipboard: Distributed chaos experiments
- :clipboard: ML-powered failure prediction module
- :clipboard: Pydantic v2 config with TOML/YAML file loading
- :clipboard: Production chaos mode (with safeguards)
- :clipboard: Cost impact analysis
- :clipboard: Docker image and GitHub Action for CI chaos testing

---

Have an idea? [Open a discussion](https://github.com/arielshad/sentinel-ai/discussions).
