"""CrewAI wrapper for chaos injection.

This module provides chaos engineering capabilities for CrewAI agents and crews.
It wraps CrewAI tools and enables fault injection during crew execution.

Example usage:
    from crewai import Agent, Task, Crew
    from sentinelai.wrappers.crewai import CrewAIWrapper

    # Create your crew
    crew = Crew(agents=[agent1, agent2], tasks=[task1, task2])

    # Wrap with chaos
    wrapper = CrewAIWrapper(crew, chaos_level=0.5)
    wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

    # Run with chaos injection
    result = wrapper.kickoff()
"""

import time
from dataclasses import dataclass
from typing import Any, Optional

from .base import BaseChaosProxy, BaseChaosWrapper


@dataclass
class CrewAIToolCall:
    """Record of a CrewAI tool call."""

    tool_name: str
    args: tuple
    kwargs: dict
    start_time: float
    end_time: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    fault_injected: Optional[str] = None
    retries: int = 0
    agent_name: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    @property
    def success(self) -> bool:
        return self.error is None


class CrewAIToolProxy(BaseChaosProxy):
    """
    Proxy for CrewAI tool objects that enables chaos injection.
    """

    def __init__(
        self,
        tool: Any,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        verbose: bool = False,
    ):
        tool_name = getattr(tool, "name", str(tool))
        super().__init__(
            tool_name=tool_name,
            chaos_level=chaos_level,
            max_retries=max_retries,
            retry_delay=retry_delay,
            verbose=verbose,
        )
        self._tool = tool
        self._func = getattr(tool, "func", tool)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the tool with chaos injection via the base proxy loop."""
        call_record = CrewAIToolCall(
            tool_name=self._tool_name,
            args=args,
            kwargs=kwargs,
            start_time=time.time(),
        )
        return self._execute_with_chaos(call_record, self._func, *args, **kwargs)


class CrewAIWrapper(BaseChaosWrapper):
    """
    Wrapper for CrewAI Crew objects that enables chaos engineering.
    """

    def __init__(
        self,
        crew: Any,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        verbose: bool = False,
    ):
        super().__init__(
            chaos_level=chaos_level,
            max_retries=max_retries,
            retry_delay=retry_delay,
            verbose=verbose,
        )
        self._crew = crew
        self._wrap_tools()

    @property
    def crew(self) -> Any:
        """Get the wrapped crew."""
        return self._crew

    def _wrap_tools(self):
        """Wrap all tools from all agents in the crew."""
        agents = getattr(self._crew, "agents", [])

        for agent in agents:
            agent_tools = getattr(agent, "tools", [])

            for tool in agent_tools:
                tool_name = getattr(tool, "name", str(tool))

                if tool_name not in self._tool_proxies:
                    proxy = CrewAIToolProxy(
                        tool,
                        chaos_level=self._chaos_level,
                        max_retries=self._max_retries,
                        retry_delay=self._retry_delay,
                        verbose=self.verbose,
                    )
                    self._tool_proxies[tool_name] = proxy

                    # Replace the tool's func with our proxy
                    if hasattr(tool, "func"):
                        tool.func = proxy

    def kickoff(self, inputs: Optional[dict[str, Any]] = None) -> Any:
        """
        Execute the crew with chaos injection.
        """
        self._kickoff_count += 1

        if inputs is not None:
            return self._crew.kickoff(inputs=inputs)
        return self._crew.kickoff()
