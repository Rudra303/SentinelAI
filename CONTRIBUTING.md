# Contributing to SentinelAI

First off, thank you for considering contributing to SentinelAI! It's people like you who make chaos engineering for AI agents a reality.

## 🎯 Mission

SentinelAI brings chaos engineering discipline to AI agents. Every contribution should advance this mission by:
- Improving reliability testing capabilities
- Supporting more agent frameworks
- Enhancing metrics and observability
- Making chaos testing more accessible

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Workflow](#development-workflow)
- [Code Style & Standards](#code-style--standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Guidelines](#documentation-guidelines)
- [Submitting Changes](#submitting-changes)
- [Community](#community)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- Familiarity with at least one agent framework (CrewAI, LangChain, or AutoGen)
- Understanding of chaos engineering principles (helpful but not required)

### Development Setup

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed setup instructions.

Quick start:

```bash
# Clone the repository
git clone https://github.com/Rudra303/SentinelAI.git
cd sentinel-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all extras
pip install -e ".[all-wrappers,dev]"

# Run tests to verify setup
pytest
```

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating a bug report:
- Check the [existing issues](https://github.com/Rudra303/SentinelAI/issues)
- Try the latest version from `main` branch
- Collect relevant information (version, Python version, agent framework)

When filing a bug report, use our [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml) and include:
- Clear title and description
- Steps to reproduce
- Minimal reproducible example
- Expected vs actual behavior
- Environment details

### 💡 Suggesting Features

Feature suggestions are welcome! Use our [feature request template](.github/ISSUE_TEMPLATE/feature_request.yml).

**Great feature requests include:**
- Clear problem statement (what pain point does this solve?)
- Proposed solution with example usage
- Consideration of alternatives
- Alignment with project mission

**Priority areas for new features:**
- New fault injectors (novel failure modes)
- Framework integrations (new agent frameworks)
- Enhanced metrics and observability
- Improved reporting and visualization
- Better developer experience

### 📖 Improving Documentation

Documentation improvements are highly valued! This includes:
- Fixing typos or clarifying existing docs
- Adding examples and tutorials
- Improving API documentation
- Writing guides for specific use cases

Use our [documentation issue template](.github/ISSUE_TEMPLATE/documentation.yml).

### 🔧 Contributing Code

#### Types of Contributions Welcome

1. **Bug Fixes** - Always welcome! Reference the issue number.

2. **New Injectors** - Adding new fault injection types:
   - Inherit from `BaseInjector`
   - Follow existing patterns (see `injectors/` directory)
   - Include comprehensive tests
   - Add example usage

3. **Framework Integrations** - Supporting new agent frameworks:
   - Inherit from `AgentWrapper`
   - Implement required abstract methods
   - Add integration tests
   - Write integration guide

4. **Metrics & Analysis** - New reliability metrics:
   - Follow SRE best practices
   - Provide clear interpretation guidelines
   - Add to reporting pipeline

5. **Tests** - Improving test coverage:
   - Unit tests for new functionality
   - Integration tests for framework wrappers
   - BDD tests for user-facing features

#### Good First Issues

Look for issues labeled [`good first issue`](https://github.com/Rudra303/SentinelAI/labels/good%20first%20issue) if you're new to the project.

## Development Workflow

### 1. Fork & Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/sentinel-ai.git
cd sentinel-ai
git remote add upstream https://github.com/Rudra303/SentinelAI.git
```

### 2. Create a Branch

```bash
git checkout -b feat/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

**Branch naming conventions:**
- `feat/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `test/` - Test improvements
- `refactor/` - Code refactoring
- `chore/` - Maintenance tasks

### 3. Make Changes

- Write clean, readable code
- Follow our [code style guidelines](#code-style--standards)
- Add/update tests
- Update documentation

### 4. Test Your Changes

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sentinelai --cov-report=html

# Run specific tests
pytest tests/test_engine.py

# Run linting
ruff check .
black --check .
mypy sentinelai
```

### 5. Commit Your Changes

```bash
git add .
git commit -m "feat: add new delay pattern for gradual degradation"
```

**Commit message format:**
```
<type>: <subject>

<body (optional)>

<footer (optional)>
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test changes
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `chore:` - Maintenance tasks

**Examples:**
```
feat: add PostgreSQL connection timeout injector

Adds a new injector for simulating database connection timeouts
specifically for PostgreSQL databases.

Closes #123
```

```
fix: correct MTTR calculation for concurrent failures

The MTTR calculator was not properly handling overlapping failures.
Updated the time window logic to account for concurrent failure scenarios.

Fixes #456
```

### 6. Push & Create PR

```bash
git push origin feat/your-feature-name
```

Then create a pull request on GitHub using our [PR template](.github/pull_request_template.md).

## Code Style & Standards

### Python Style

We follow PEP 8 with some adjustments:

- **Line length:** 100 characters (enforced by Black)
- **Formatting:** Use Black for automatic formatting
- **Linting:** Use Ruff for fast Python linting
- **Type hints:** Required for all public APIs and encouraged elsewhere
- **Docstrings:** Google style docstrings for all public functions/classes

### Running Code Quality Tools

```bash
# Format code
black sentinelai tests

# Lint code
ruff check sentinelai tests

# Type check
mypy sentinelai

# Run all checks
black . && ruff check . && mypy sentinelai && pytest
```

### Code Organization

```python
# Imports: stdlib, third-party, local
import sys
from typing import Optional

from crewai import Crew

from sentinelai.engine import ChaosEngine
from sentinelai.injectors.base import BaseInjector

# Type hints for public APIs
def inject_fault(
    operation: str,
    config: Optional[dict] = None,
) -> bool:
    """Inject a fault into the operation.

    Args:
        operation: The operation name to inject fault into
        config: Optional configuration for fault injection

    Returns:
        True if fault was injected, False otherwise

    Example:
        >>> inject_fault("search", {"probability": 0.5})
        True
    """
    pass
```

### Best Practices

1. **Keep it simple** - Prioritize readability over cleverness
2. **Write self-documenting code** - Use clear variable/function names
3. **Avoid premature optimization** - Get it working, then make it fast
4. **Fail fast** - Validate inputs early and explicitly
5. **Be explicit** - Avoid implicit behavior and magic
6. **Follow existing patterns** - Look at existing code for examples

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                   # Unit tests (fast, isolated)
├── integration/            # Integration tests (framework wrappers)
├── e2e/                    # End-to-end tests (full scenarios)
└── bdd/                    # BDD/Gherkin tests (user scenarios)
```

### Writing Tests

```python
import pytest
from sentinelai.injectors import ToolFailureInjector

class TestToolFailureInjector:
    """Test suite for tool failure injection."""

    def test_inject_timeout_failure(self):
        """Should inject timeout failure with correct probability."""
        # Arrange
        config = ToolFailureConfig(probability=1.0)
        injector = ToolFailureInjector(config)

        # Act
        result = injector.should_inject_fault()

        # Assert
        assert result is True
        assert injector.get_last_fault_type() == FailureMode.TIMEOUT

    @pytest.mark.parametrize("probability", [0.0, 0.25, 0.5, 1.0])
    def test_probability_levels(self, probability):
        """Should respect configured probability levels."""
        # Test implementation
        pass
```

### Test Coverage

- **Minimum coverage:** 80% overall
- **Critical paths:** 95%+ coverage required
- **New features:** Must include tests
- **Bug fixes:** Must include regression tests

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=sentinelai --cov-report=term-missing

# Specific test file
pytest tests/test_engine.py

# Specific test
pytest tests/test_engine.py::TestChaosEngine::test_inject_fault

# Mark-based tests
pytest -m "not slow"
pytest -m integration
```

## Documentation Guidelines

### Docstring Format (Google Style)

```python
def calculate_mttr(
    failures: list[FailureEvent],
    recoveries: list[RecoveryEvent],
) -> MTTRStats:
    """Calculate Mean Time To Recovery from failure events.

    Analyzes failure and recovery events to compute MTTR metrics
    following SRE best practices.

    Args:
        failures: List of failure events with timestamps
        recoveries: List of recovery events with timestamps

    Returns:
        MTTRStats object containing:
            - mttr_seconds: Mean recovery time in seconds
            - recovery_rate: Percentage of failures that recovered
            - fastest_recovery: Minimum recovery time observed
            - slowest_recovery: Maximum recovery time observed

    Raises:
        ValueError: If failures and recoveries lists don't align

    Example:
        >>> failures = [FailureEvent(time=0, tool="search")]
        >>> recoveries = [RecoveryEvent(time=1.5, tool="search")]
        >>> stats = calculate_mttr(failures, recoveries)
        >>> stats.mttr_seconds
        1.5

    Note:
        Unrecovered failures are excluded from MTTR calculation
        but included in recovery_rate calculation.
    """
    pass
```

### README Updates

When adding features, update the main [README.md](README.md):
- Add to Features section if it's a new capability
- Update Quick Start if it affects basic usage
- Add examples demonstrating the feature
- Update CLI documentation if adding commands

### Documentation Files

- **README.md** - Project overview, quick start, examples
- **DEVELOPMENT.md** - Development setup and workflows
- **CONTRIBUTING.md** - This file
- **Integration Guides** - Framework-specific guides (e.g., CREWAI_INTEGRATION_GUIDE.md)
- **API Documentation** - Generated from docstrings

## Submitting Changes

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Commits are clean and well-described
- [ ] Branch is up to date with `main`

### Pull Request Process

1. **Fill out the PR template** completely
2. **Link related issues** using keywords (Fixes #123, Closes #456)
3. **Request review** from maintainers
4. **Address feedback** promptly and respectfully
5. **Keep PR focused** - one feature/fix per PR
6. **Update branch** if main has moved forward

### PR Review Process

Maintainers will review your PR for:
- Code quality and style
- Test coverage
- Documentation completeness
- Architectural fit
- Performance implications
- Breaking changes

**Review timeline:**
- Initial review: Within 3 business days
- Follow-up reviews: Within 2 business days
- Urgent fixes: Within 24 hours

### After Merge

Once merged:
- Your contribution will be in the next release
- You'll be added to CONTRIBUTORS.md
- Consider joining as a regular contributor!

## Community

### Getting Help

- **GitHub Discussions** - Ask questions, share ideas: [Discussions](https://github.com/Rudra303/SentinelAI/discussions)
- **GitHub Issues** - Report bugs, request features: [Issues](https://github.com/Rudra303/SentinelAI/issues)

### Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project README (for significant contributions)

### Becoming a Maintainer

Active contributors who demonstrate:
- Consistent high-quality contributions
- Good judgment on technical decisions
- Helpful engagement with community
- Alignment with project values

May be invited to become maintainers.

## Questions?

Don't hesitate to ask! File an issue, start a discussion, or reach out to maintainers.

**Remember:** There are no "stupid questions," and everyone was new once. We're here to help!

---

**Thank you for contributing to SentinelAI!** 🎉

*"Hope is not a strategy. Test your agents."*
