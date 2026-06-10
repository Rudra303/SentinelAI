# FAQ

## General

### What is SentinelAI?

SentinelAI is a chaos engineering framework for AI agents. It injects controlled failures (tool errors, latency, hallucinations, context corruption, budget exhaustion) into your agent's tool calls, then measures recovery time (MTTR) and reliability.

### Is this for production use?

No. SentinelAI is designed for **development and CI testing**. You run chaos experiments against your agents in dev/staging to find failure modes before they hit production.

### Does it cost money?

SentinelAI is free and open source (Apache 2.0). If your agent calls paid APIs (like LLMs), those API costs still apply during chaos experiments, but SentinelAI itself is free.

### What does "SentinelAI" mean?

"Sentinel" means a guard or watchkeeper. SentinelAI acts as a sentinel for your AI agents — proactively watching for weaknesses through controlled chaos testing before they cause real failures in production.

## Technical

### Which agent frameworks are supported?

- **CrewAI** — full wrapper + integration guide
- **Microsoft AutoGen** — full wrapper
- **LangChain** — full wrapper
- **Claude Agent SDK** — full wrapper + hooks
- **Custom agents** — wrap any Python class

### How do I add a custom injector?

Subclass `BaseInjector` from `sentinelai.injectors.base`:

```python
from sentinelai.injectors.base import BaseInjector, InjectorConfig

class MyInjector(BaseInjector):
    def inject(self, tool_name, args, kwargs):
        # Your fault injection logic
        ...
```

See the [Contributing Guide](https://github.com/Rudra303/SentinelAI/blob/main/CONTRIBUTING.md) for full details.

### What metrics does it collect?

- **MTTR** — Mean Time To Recovery (seconds)
- **Recovery quality** — did the agent recover correctly or just fail gracefully?
- **Reliability score** — SRE-grade (five nines to one nine)
- **Error budget tracking** — know when to freeze changes
- **Success rate, failure distributions, latency analysis**

### Can I use it in CI/CD?

Yes. Use the CLI to run experiments and assert on results:

```bash
sentinelai run scenarios/critical.json --format json -o results.json
# Then parse results.json in your CI pipeline
```

### What Python versions are supported?

Python 3.10, 3.11, and 3.12.

## Troubleshooting

### `sentinelai: command not found`

Make sure you installed with pip and the install location is on your PATH:

```bash
pip install sentinel-ai
python -m sentinelai --version
```

### Import errors with framework wrappers

Install the optional dependencies for your framework:

```bash
pip install sentinel-ai[crewai]
pip install sentinel-ai[langchain]
pip install sentinel-ai[autogen]
pip install sentinel-ai[claude-agent-sdk]
```
