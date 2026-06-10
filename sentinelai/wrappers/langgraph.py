"""LangGraph wrapper for chaos injection.

This module provides chaos engineering capabilities for LangGraph state graphs.
It wraps LangGraph compiled graphs and their tools/nodes to enable fault injection
during graph execution.

Example usage:
    from langgraph.graph import StateGraph
    from sentinelai.wrappers.langgraph import LangGraphWrapper

    # Build and compile your graph
    graph = StateGraph(AgentState)
    # ... add nodes and edges ...
    compiled = graph.compile()

    # Wrap with chaos
    wrapper = LangGraphWrapper(compiled, chaos_level=0.5)
    wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

    # Run with chaos injection
    result = wrapper.invoke({"messages": [HumanMessage(content="Hello")]})
"""

import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Iterator, Optional

from .base import BaseChaosProxy, BaseChaosWrapper
from ..injectors import BaseInjector
from ..injectors.base import FaultType
from ..metrics import MetricsCollector
from ..verbose import get_logger


@dataclass
class LangGraphToolCall:
    """Record of a LangGraph tool call."""

    tool_name: str
    args: tuple
    kwargs: dict
    start_time: float
    end_time: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    fault_injected: Optional[str] = None
    retries: int = 0
    node_name: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class LangGraphNodeEvent:
    """Record of a LangGraph node execution."""

    node_name: str
    start_time: float
    end_time: Optional[float] = None
    error: Optional[str] = None
    fault_injected: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    @property
    def success(self) -> bool:
        return self.error is None


class LangGraphToolProxy(BaseChaosProxy):
    """
    Proxy for LangGraph tool objects that enables chaos injection.
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
        call_record = LangGraphToolCall(
            tool_name=self._tool_name,
            args=args,
            kwargs=kwargs,
            start_time=time.time(),
        )
        return self._execute_with_chaos(call_record, self._func, *args, **kwargs)


class LangGraphNodeProxy:
    """
    Proxy for a LangGraph node function that enables chaos injection.
    """

    def __init__(
        self,
        func: Callable,
        node_name: str,
        chaos_level: float = 0.0,
        verbose: bool = False,
    ):
        self._func = func
        self._node_name = node_name
        self._chaos_level = chaos_level
        self.verbose = verbose
        self._logger = get_logger()

        self._injectors: list[BaseInjector] = []
        self._event_history: list[LangGraphNodeEvent] = []
        self._metrics = MetricsCollector()

    @property
    def node_name(self) -> str:
        return self._node_name

    def add_injector(self, injector: BaseInjector):
        self._injectors.append(injector)

    def remove_injector(self, injector: BaseInjector):
        self._injectors.remove(injector)

    def clear_injectors(self):
        self._injectors.clear()

    def __call__(self, state: Any) -> Any:
        event = LangGraphNodeEvent(
            node_name=self._node_name,
            start_time=time.time(),
        )

        for injector in self._injectors:
            if injector.should_inject(self._node_name):
                fault_type = injector.fault_type.value
                event.fault_injected = fault_type

                if self.verbose:
                    self._logger.info(
                        f"[LangGraph] Injecting {fault_type} on node '{self._node_name}'"
                    )

                result, details = injector.inject(
                    self._node_name,
                    {"node_name": self._node_name, "state": state},
                )

                if injector.fault_type == FaultType.DELAY:
                    continue

                if result is not None:
                    event.end_time = time.time()
                    event.error = f"Fault injected: {fault_type}"
                    self._event_history.append(event)
                    self._metrics.record_operation(
                        self._node_name,
                        event.duration_ms,
                        success=False,
                        fault_type=fault_type,
                    )
                    raise RuntimeError(
                        f"Chaos fault injected on node '{self._node_name}': {fault_type}"
                    )

        try:
            result = self._func(state)
            event.end_time = time.time()
            self._event_history.append(event)
            self._metrics.record_operation(
                self._node_name,
                event.duration_ms,
                success=True,
            )
            return result
        except Exception as e:
            event.end_time = time.time()
            event.error = str(e)
            self._event_history.append(event)
            self._metrics.record_operation(
                self._node_name,
                event.duration_ms,
                success=False,
            )
            raise

    def get_event_history(self) -> list[LangGraphNodeEvent]:
        return self._event_history.copy()

    def get_metrics(self) -> dict[str, Any]:
        return self._metrics.get_summary()

    def reset(self):
        self._event_history.clear()
        self._metrics.reset()


class LangGraphWrapper(BaseChaosWrapper):
    """
    Wrapper for LangGraph CompiledGraph that enables chaos engineering.
    """

    def __init__(
        self,
        compiled_graph: Any,
        tools: Optional[list[Any]] = None,
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
        self._compiled_graph = compiled_graph
        self._explicit_tools = tools
        self._node_proxies: dict[str, LangGraphNodeProxy] = {}
        self._invoke_count = 0

        self._wrap_tools()

    @property
    def compiled_graph(self) -> Any:
        return self._compiled_graph

    def _wrap_tools(self):
        tools_to_wrap: list[Any] = []

        if self._explicit_tools:
            tools_to_wrap.extend(self._explicit_tools)

        nodes = getattr(self._compiled_graph, "nodes", {})
        for node_name, node_func in nodes.items():
            node_tools = getattr(node_func, "tools", None)
            if node_tools and isinstance(node_tools, (list, tuple)):
                tools_to_wrap.extend(node_tools)
            tools_by_name = getattr(node_func, "tools_by_name", None)
            if tools_by_name and isinstance(tools_by_name, dict):
                tools_to_wrap.extend(tools_by_name.values())

        graph_tools = getattr(self._compiled_graph, "tools", None)
        if graph_tools and isinstance(graph_tools, (list, tuple)):
            tools_to_wrap.extend(graph_tools)

        for tool in tools_to_wrap:
            tool_name = getattr(tool, "name", str(tool))

            if tool_name not in self._tool_proxies:
                proxy = LangGraphToolProxy(
                    tool,
                    chaos_level=self._chaos_level,
                    max_retries=self._max_retries,
                    retry_delay=self._retry_delay,
                    verbose=self.verbose,
                )
                self._tool_proxies[tool_name] = proxy

                if hasattr(tool, "func"):
                    tool.func = proxy

    def wrap_node(
        self,
        node_name: str,
        injectors: Optional[list[BaseInjector]] = None,
    ) -> Optional[LangGraphNodeProxy]:
        nodes = getattr(self._compiled_graph, "nodes", {})
        if node_name not in nodes:
            return None

        original_func = nodes[node_name]
        proxy = LangGraphNodeProxy(
            func=original_func,
            node_name=node_name,
            chaos_level=self._chaos_level,
            verbose=self.verbose,
        )
        if injectors:
            for inj in injectors:
                proxy.add_injector(inj)

        self._node_proxies[node_name] = proxy
        nodes[node_name] = proxy
        return proxy

    def add_injector(
        self,
        injector: BaseInjector,
        tools: Optional[list[str]] = None,
        nodes: Optional[list[str]] = None,
    ):
        super().add_injector(injector, tools)
        if nodes:
            for name in nodes:
                if name in self._node_proxies:
                    self._node_proxies[name].add_injector(injector)

    def get_wrapped_nodes(self) -> dict[str, LangGraphNodeProxy]:
        return self._node_proxies.copy()

    def invoke(self, input_data: dict, config: Optional[dict] = None, **kwargs) -> Any:
        self._invoke_count += 1
        if config is not None:
            kwargs["config"] = config
        return self._compiled_graph.invoke(input_data, **kwargs)

    async def ainvoke(self, input_data: dict, config: Optional[dict] = None, **kwargs) -> Any:
        self._invoke_count += 1
        if config is not None:
            kwargs["config"] = config
        return await self._compiled_graph.ainvoke(input_data, **kwargs)

    def stream(
        self, input_data: dict, config: Optional[dict] = None, **kwargs
    ) -> Iterator[Any]:
        self._invoke_count += 1
        if config is not None:
            kwargs["config"] = config
        yield from self._compiled_graph.stream(input_data, **kwargs)

    async def astream(
        self, input_data: dict, config: Optional[dict] = None, **kwargs
    ) -> AsyncIterator[Any]:
        self._invoke_count += 1
        if config is not None:
            kwargs["config"] = config
        async for chunk in self._compiled_graph.astream(input_data, **kwargs):
            yield chunk

    def batch(self, inputs: list[dict], config: Optional[dict] = None, **kwargs) -> list[Any]:
        self._invoke_count += len(inputs)
        if config is not None:
            kwargs["config"] = config
        from typing import cast
        return cast(list[Any], self._compiled_graph.batch(inputs, **kwargs))

    async def abatch(
        self, inputs: list[dict], config: Optional[dict] = None, **kwargs
    ) -> list[Any]:
        self._invoke_count += len(inputs)
        if config is not None:
            kwargs["config"] = config
        from typing import cast
        return cast(list[Any], await self._compiled_graph.abatch(inputs, **kwargs))

    def get_state(self, config: Optional[dict] = None) -> Any:
        return self._compiled_graph.get_state(config or {})

    def update_state(self, config: dict, values: dict, **kwargs) -> Any:
        return self._compiled_graph.update_state(config, values, **kwargs)

    def get_metrics(self) -> dict[str, Any]:
        metrics = super().get_metrics()
        node_metrics = {}
        for name, proxy in self._node_proxies.items():
            node_metrics[name] = proxy.get_metrics()

        return {
            "invoke_count": self._invoke_count,
            "tools": metrics["tools"],
            "nodes": node_metrics,
            "aggregate": metrics["aggregate"],
        }

    def reset(self):
        super().reset()
        self._invoke_count = 0
        for proxy in self._node_proxies.values():
            proxy.reset()
