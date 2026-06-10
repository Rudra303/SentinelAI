"""LangChain wrapper for chaos injection.

This module provides chaos engineering capabilities for LangChain agents and chains.
It wraps LangChain tools and enables fault injection during agent execution.

Example usage:
    from langchain.agents import AgentExecutor
    from sentinelai.wrappers.langchain import LangChainAgentWrapper

    # Create your agent executor
    agent_executor = AgentExecutor(agent=agent, tools=tools)

    # Wrap with chaos
    wrapper = LangChainAgentWrapper(agent_executor, chaos_level=0.5)
    wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

    # Run with chaos injection
    result = wrapper.invoke({"input": "Hello"})
"""

import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterator, Optional

from .base import BaseChaosProxy, BaseChaosWrapper
from ..metrics import MetricsCollector


@dataclass
class LangChainToolCall:
    """Record of a LangChain tool call."""

    tool_name: str
    args: tuple
    kwargs: dict
    start_time: float
    end_time: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    fault_injected: Optional[str] = None
    retries: int = 0

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class CallbackEvent:
    """Record of a callback event."""

    event_type: str
    timestamp: float
    data: dict


class LangChainToolProxy(BaseChaosProxy):
    """
    Proxy for LangChain tool objects that enables chaos injection.
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
        """Execute the tool with chaos injection."""
        call_record = LangChainToolCall(
            tool_name=self._tool_name,
            args=args,
            kwargs=kwargs,
            start_time=time.time(),
        )
        return self._execute_with_chaos(call_record, self._func, *args, **kwargs)


class ChaosCallbackHandler:
    """
    LangChain callback handler that records events and can inject chaos.
    """

    def __init__(self, chaos_level: float = 0.0):
        self.chaos_level = chaos_level
        self._events: list[CallbackEvent] = []
        self._tool_calls = 0
        self._llm_calls = 0
        self._chain_runs = 0

    def on_llm_start(self, serialized: dict, prompts: list, **kwargs):
        self._llm_calls += 1
        self._events.append(
            CallbackEvent(
                event_type="llm_start",
                timestamp=time.time(),
                data={"serialized": serialized, "prompts": prompts},
            )
        )

    def on_llm_end(self, response, **kwargs):
        self._events.append(
            CallbackEvent(
                event_type="llm_end",
                timestamp=time.time(),
                data={"response": str(response)},
            )
        )

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs):
        self._tool_calls += 1
        self._events.append(
            CallbackEvent(
                event_type="tool_start",
                timestamp=time.time(),
                data={"serialized": serialized, "input": input_str},
            )
        )

    def on_tool_end(self, output: str, **kwargs):
        self._events.append(
            CallbackEvent(
                event_type="tool_end",
                timestamp=time.time(),
                data={"output": output},
            )
        )

    def on_chain_start(self, serialized: dict, inputs: dict, **kwargs):
        self._chain_runs += 1
        self._events.append(
            CallbackEvent(
                event_type="chain_start",
                timestamp=time.time(),
                data={"serialized": serialized, "inputs": inputs},
            )
        )

    def on_chain_end(self, outputs: dict, **kwargs):
        self._events.append(
            CallbackEvent(
                event_type="chain_end",
                timestamp=time.time(),
                data={"outputs": outputs},
            )
        )

    def get_events(self) -> list[CallbackEvent]:
        return self._events.copy()

    def get_metrics(self) -> dict[str, Any]:
        return {
            "tool_calls": self._tool_calls,
            "llm_calls": self._llm_calls,
            "chain_runs": self._chain_runs,
            "total_events": len(self._events),
        }

    def reset(self):
        self._events.clear()
        self._tool_calls = 0
        self._llm_calls = 0
        self._chain_runs = 0


class LangChainAgentWrapper(BaseChaosWrapper):
    """
    Wrapper for LangChain AgentExecutor that enables chaos engineering.
    """

    def __init__(
        self,
        agent_executor: Any,
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
        self._agent_executor = agent_executor
        self._invoke_count = 0
        self._wrap_tools()

    @property
    def agent_executor(self) -> Any:
        return self._agent_executor

    def _wrap_tools(self):
        tools = getattr(self._agent_executor, "tools", [])

        for tool in tools:
            tool_name = getattr(tool, "name", str(tool))

            if tool_name not in self._tool_proxies:
                proxy = LangChainToolProxy(
                    tool,
                    chaos_level=self._chaos_level,
                    max_retries=self._max_retries,
                    retry_delay=self._retry_delay,
                    verbose=self.verbose,
                )
                self._tool_proxies[tool_name] = proxy

                if hasattr(tool, "func"):
                    tool.func = proxy

    def invoke(self, input_data: dict, config: Optional[dict] = None, **kwargs) -> Any:
        self._invoke_count += 1
        if config is not None:
            kwargs["config"] = config
        return self._agent_executor.invoke(input_data, **kwargs)

    async def ainvoke(self, input_data: dict, config: Optional[dict] = None, **kwargs) -> Any:
        self._invoke_count += 1
        if config is not None:
            kwargs["config"] = config
        return await self._agent_executor.ainvoke(input_data, **kwargs)

    def stream(self, input_data: dict, config: Optional[dict] = None, **kwargs) -> Iterator[Any]:
        self._invoke_count += 1
        if config is not None:
            kwargs["config"] = config
        yield from self._agent_executor.stream(input_data, **kwargs)

    async def astream(
        self, input_data: dict, config: Optional[dict] = None, **kwargs
    ) -> AsyncIterator[Any]:
        self._invoke_count += 1
        if config is not None:
            kwargs["config"] = config
        async for chunk in self._agent_executor.astream(input_data, **kwargs):
            yield chunk

    def batch(self, inputs: list[dict], config: Optional[dict] = None, **kwargs) -> list[Any]:
        self._invoke_count += len(inputs)
        if config is not None:
            kwargs["config"] = config
        from typing import cast
        return cast(list[Any], self._agent_executor.batch(inputs, **kwargs))

    async def abatch(
        self, inputs: list[dict], config: Optional[dict] = None, **kwargs
    ) -> list[Any]:
        self._invoke_count += len(inputs)
        if config is not None:
            kwargs["config"] = config
        from typing import cast
        return cast(list[Any], await self._agent_executor.abatch(inputs, **kwargs))

    def get_metrics(self) -> dict[str, Any]:
        metrics = super().get_metrics()
        metrics["invoke_count"] = self._invoke_count
        return metrics

    def reset(self):
        super().reset()
        self._invoke_count = 0


class LangChainChainWrapper:
    """
    Wrapper for LangChain chains (LCEL) that enables chaos engineering.
    """

    def __init__(
        self,
        chain: Any,
        chaos_level: float = 0.0,
    ):
        self._chain = chain
        self._chaos_level = chaos_level
        self._invoke_count = 0
        self._metrics = MetricsCollector()

    @property
    def chain(self) -> Any:
        return self._chain

    @property
    def chaos_level(self) -> float:
        return self._chaos_level

    def invoke(self, input_data: dict, **kwargs) -> Any:
        self._invoke_count += 1
        return self._chain.invoke(input_data, **kwargs)

    def stream(self, input_data: dict, **kwargs) -> Iterator[Any]:
        self._invoke_count += 1
        yield from self._chain.stream(input_data, **kwargs)

    def batch(self, inputs: list[dict], **kwargs) -> list[Any]:
        self._invoke_count += len(inputs)
        from typing import cast
        return cast(list[Any], self._chain.batch(inputs, **kwargs))

    def get_metrics(self) -> dict[str, Any]:
        return {
            "invoke_count": self._invoke_count,
            "aggregate": self._metrics.get_summary(),
        }

    def reset(self):
        self._invoke_count = 0
        self._metrics.reset()
