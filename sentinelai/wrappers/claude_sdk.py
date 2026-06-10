"""Claude Agent SDK wrapper for chaos injection.

This module provides chaos engineering capabilities for agents built with the
Claude Agent SDK.
"""

import time
from typing import Any, Callable, Optional

from .base import BaseChaosProxy, BaseChaosWrapper
from ..injectors.base import FaultType


class ClaudeAgentSDKToolProxy(BaseChaosProxy):
    """Proxy for a Claude Agent SDK ``@tool`` function with chaos injection."""

    def __init__(
        self,
        func: Callable,
        name: str,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ):
        super().__init__(
            tool_name=name,
            chaos_level=chaos_level,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        self._func = func

        for attr in ("__name__", "__doc__", "__module__", "__qualname__"):
            try:
                setattr(self, attr, getattr(func, attr))
            except AttributeError:
                pass

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        class DummyCall:
            def __init__(self):
                self.duration_ms = 0.0
                self.retries = 0

        call_record = DummyCall()
        context = {"tool_name": self._tool_name, "args": args, "kwargs": kwargs}

        retries = 0
        last_error: Optional[Exception] = None
        fault_injected: Optional[str] = None
        start_time = time.time()

        while retries <= self._max_retries:
            try:
                for injector in self._injectors:
                    if injector.should_inject(self._tool_name):
                        fault_type = injector.fault_type.value
                        fault_injected = fault_type
                        self._mttr.record_failure(self._tool_name, fault_type)

                        result, _details = injector.inject(self._tool_name, context)
                        if fault_type == FaultType.TOOL_FAILURE.value:
                            from ..injectors.tool_failure import ToolFailureException
                            raise ToolFailureException(
                                _details.get("error_message", "Injected fault"),
                                _details.get("failure_mode", fault_type),
                                self._tool_name,
                            )
                        if result is not None:
                            call_record.duration_ms = (time.time() - start_time) * 1000
                            self._metrics.record_operation(
                                self._tool_name,
                                call_record.duration_ms,
                                success=False,
                                fault_type=fault_type,
                            )
                            return result

                result = self._func(*args, **kwargs)

                call_record.duration_ms = (time.time() - start_time) * 1000
                if fault_injected:
                    self._mttr.record_recovery(
                        self._tool_name,
                        fault_injected,
                        recovery_method="retry",
                        retries=retries,
                        success=True,
                    )

                self._metrics.record_operation(
                    self._tool_name,
                    call_record.duration_ms,
                    success=True,
                    retries=retries,
                    fault_type=fault_injected,
                )
                return result

            except Exception as e:
                last_error = e
                retries += 1
                if retries <= self._max_retries:
                    time.sleep(self._retry_delay)
                else:
                    break

        call_record.duration_ms = (time.time() - start_time) * 1000
        self._metrics.record_operation(
            self._tool_name,
            call_record.duration_ms,
            success=False,
            retries=retries,
            fault_type=fault_injected,
        )
        if fault_injected:
            self._mttr.record_recovery(
                self._tool_name,
                fault_injected,
                recovery_method="retry",
                retries=retries,
                success=False,
            )

        assert last_error is not None
        raise last_error


class ClaudeAgentSDKWrapper(BaseChaosWrapper):
    """Chaos wrapper for Claude Agent SDK custom tools."""

    def __init__(
        self,
        tools: Optional[list[Any]] = None,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ):
        super().__init__(
            chaos_level=chaos_level,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        self._query_count = 0

        if tools:
            self._register_tools(tools)

    @property
    def query_count(self) -> int:
        return self._query_count

    def _register_tools(self, tools: list[Any]):
        for t in tools:
            if isinstance(t, dict):
                name = t.get("name", str(t))
                func = t.get("func", t)
            elif hasattr(t, "name") and hasattr(t, "func"):
                name = t.name
                func = t.func
            elif callable(t):
                name = getattr(t, "__name__", str(t))
                func = t
            else:
                continue

            proxy = ClaudeAgentSDKToolProxy(
                func,
                name=name,
                chaos_level=self._chaos_level,
                max_retries=self._max_retries,
                retry_delay=self._retry_delay,
            )
            self._tool_proxies[name] = proxy

    def add_tool(self, func: Callable, name: Optional[str] = None):
        tool_name = name or getattr(func, "__name__", str(func))
        self._register_tools([{"name": tool_name, "func": func}])

    def get_wrapped_tool_list(self) -> list[ClaudeAgentSDKToolProxy]:
        return list(self._tool_proxies.values())  # type: ignore

    def record_query(self):
        self._query_count += 1

    def get_metrics(self) -> dict[str, Any]:
        metrics = super().get_metrics()
        metrics["query_count"] = self._query_count
        return metrics

    def reset(self):
        super().reset()
        self._query_count = 0
