"""AutoGen wrapper for chaos injection.

This module provides chaos engineering capabilities for Microsoft AutoGen agents.
It wraps AutoGen function_map functions and enables fault injection during agent
conversations.

Example usage:
    from autogen import AssistantAgent, UserProxyAgent
    from sentinelai.wrappers.autogen import AutoGenWrapper

    # Create your agents
    assistant = AssistantAgent("assistant", llm_config=config)
    user_proxy = UserProxyAgent("user_proxy")

    # Wrap with chaos
    wrapper = AutoGenWrapper(assistant, user_proxy=user_proxy, chaos_level=0.5)
    wrapper.configure_chaos(enable_tool_failures=True, enable_delays=True)

    # Run with chaos injection
    result = wrapper.initiate_chat("Hello, agent!")
"""

import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .base import BaseChaosProxy, BaseChaosWrapper
from ..metrics import MetricsCollector


@dataclass
class AutoGenFunctionCall:
    """Record of an AutoGen function call."""

    function_name: str
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


class AutoGenFunctionProxy(BaseChaosProxy):
    """
    Proxy for AutoGen function_map functions that enables chaos injection.
    """

    def __init__(
        self,
        func: Callable,
        name: str,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        verbose: bool = False,
    ):
        super().__init__(
            tool_name=name,
            chaos_level=chaos_level,
            max_retries=max_retries,
            retry_delay=retry_delay,
            verbose=verbose,
        )
        self._func = func

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the function with chaos injection via the base proxy loop."""
        call_record = AutoGenFunctionCall(
            function_name=self._tool_name,
            args=args,
            kwargs=kwargs,
            start_time=time.time(),
        )
        return self._execute_with_chaos(call_record, self._func, *args, **kwargs)


class AutoGenWrapper(BaseChaosWrapper):
    """
    Wrapper for AutoGen agents that enables chaos engineering.
    """

    def __init__(
        self,
        agent: Any,
        user_proxy: Optional[Any] = None,
        group_chat: Optional[Any] = None,
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
        self._agent = agent
        self._user_proxy = user_proxy
        self._group_chat = group_chat
        self._reply_count = 0
        self._wrap_functions()

    @property
    def agent(self) -> Any:
        return self._agent

    @property
    def user_proxy(self) -> Optional[Any]:
        return self._user_proxy

    @property
    def group_chat(self) -> Optional[Any]:
        return self._group_chat

    def _wrap_functions(self):
        function_map = getattr(self._agent, "function_map", {})

        if isinstance(function_map, dict):
            for name, func in function_map.items():
                proxy = AutoGenFunctionProxy(
                    func,
                    name=name,
                    chaos_level=self._chaos_level,
                    max_retries=self._max_retries,
                    retry_delay=self._retry_delay,
                    verbose=self.verbose,
                )
                self._tool_proxies[name] = proxy
                function_map[name] = proxy

    def get_wrapped_functions(self) -> dict[str, AutoGenFunctionProxy]:
        return self.get_wrapped_tools()  # type: ignore

    def initiate_chat(
        self,
        message: str,
        max_turns: Optional[int] = None,
        clear_history: bool = False,
        **kwargs,
    ) -> Any:
        if self._user_proxy is None:
            raise ValueError("user_proxy is required for initiate_chat")

        chat_kwargs = {"recipient": self._agent, "message": message, **kwargs}

        if max_turns is not None:
            chat_kwargs["max_turns"] = max_turns
        if clear_history:
            chat_kwargs["clear_history"] = clear_history

        return self._user_proxy.initiate_chat(**chat_kwargs)

    def generate_reply(
        self,
        messages: list[dict[str, Any]],
        sender: Optional[Any] = None,
        **kwargs,
    ) -> Any:
        self._reply_count += 1
        reply_kwargs = {"messages": messages, **kwargs}
        if sender is not None:
            reply_kwargs["sender"] = sender

        return self._agent.generate_reply(**reply_kwargs)

    def get_metrics(self) -> dict[str, Any]:
        metrics = super().get_metrics()
        metrics["reply_count"] = self._reply_count
        return metrics

    def reset(self):
        super().reset()
        self._reply_count = 0


class AutoGenMultiAgentWrapper:
    """
    Wrapper for multiple AutoGen agents in a conversation.
    """

    def __init__(
        self,
        agents: list[Any],
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ):
        self._agents = agents
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        self._agent_wrappers: dict[str, AutoGenWrapper] = {}
        self._metrics = MetricsCollector()

        self._wrap_agents()

    @property
    def agents(self) -> list[Any]:
        return self._agents

    @property
    def chaos_level(self) -> float:
        return self._chaos_level

    def _wrap_agents(self):
        for agent in self._agents:
            agent_name = getattr(agent, "name", str(agent))
            wrapper = AutoGenWrapper(
                agent,
                chaos_level=self._chaos_level,
                max_retries=self._max_retries,
                retry_delay=self._retry_delay,
            )
            self._agent_wrappers[agent_name] = wrapper

    def configure_chaos(
        self,
        chaos_level: float = 1.0,
        enable_tool_failures: bool = True,
        enable_delays: bool = True,
        enable_hallucinations: bool = True,
        enable_context_corruption: bool = True,
        enable_budget_exhaustion: bool = True,
    ):
        self._chaos_level = chaos_level

        for wrapper in self._agent_wrappers.values():
            wrapper.configure_chaos(
                chaos_level=chaos_level,
                enable_tool_failures=enable_tool_failures,
                enable_delays=enable_delays,
                enable_hallucinations=enable_hallucinations,
                enable_context_corruption=enable_context_corruption,
                enable_budget_exhaustion=enable_budget_exhaustion,
            )

    def get_agent_wrappers(self) -> list[AutoGenWrapper]:
        return list(self._agent_wrappers.values())

    def get_agent_wrapper(self, name: str) -> Optional[AutoGenWrapper]:
        return self._agent_wrappers.get(name)

    def get_aggregate_metrics(self) -> dict[str, Any]:
        total_replies = 0
        agent_metrics = {}

        for name, wrapper in self._agent_wrappers.items():
            metrics = wrapper.get_metrics()
            total_replies += metrics.get("reply_count", 0)
            agent_metrics[name] = metrics

        return {
            "total_replies": total_replies,
            "agents": agent_metrics,
            "aggregate": self._metrics.get_summary(),
        }

    def reset(self):
        for wrapper in self._agent_wrappers.values():
            wrapper.reset()
        self._metrics.reset()
