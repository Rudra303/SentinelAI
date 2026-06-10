"""Shared pytest fixtures for SentinelAI tests."""

import pytest

from sentinelai import ChaosEngine
from sentinelai.metrics import MetricsCollector
from sentinelai.testing import MockAgent


@pytest.fixture
def mock_agent():
    """Return a fresh instance of MockAgent for testing."""
    return MockAgent()


@pytest.fixture
def chaos_engine():
    """Return a fresh ChaosEngine with chaos level 0.0."""
    return ChaosEngine(chaos_level=0.0)


@pytest.fixture
def metrics_collector():
    """Return a fresh MetricsCollector."""
    return MetricsCollector()
