"""Base classes for SentinelAI framework wrappers.

Provides base Proxy and Wrapper implementations to reduce code duplication
across different AI agent framework integrations.
"""

import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional

from ..experiment import Experiment, ExperimentConfig, ExperimentResult
from ..injectors import BaseInjector
from ..injectors.budget import BudgetExhaustionConfig, BudgetExhaustionInjector
from ..injectors.context import ContextCorruptionConfig, ContextCorruptionInjector
from ..injectors.delay import DelayConfig, DelayInjector
from ..injectors.hallucination import HallucinationConfig, HallucinationInjector
from ..injectors.tool_failure import ToolFailureConfig, ToolFailureInjector
from ..metrics import MetricsCollector, MTTRCalculator
from ..verbose import get_logger


class BaseChaosProxy:
    """Base class for proxying tool calls with chaos injection."""

    def __init__(
        self,
        tool_name: str,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        verbose: bool = False,
    ):
        self._tool_name = tool_name
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self.verbose = verbose
        self._logger = get_logger()

        self._injectors: List[BaseInjector] = []
        self._call_history: List[Any] = []
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()

    @property
    def tool_name(self) -> str:
        return self._tool_name

    def add_injector(self, injector: BaseInjector):
        self._injectors.append(injector)

    def remove_injector(self, injector: BaseInjector):
        if injector in self._injectors:
            self._injectors.remove(injector)

    def clear_injectors(self):
        self._injectors.clear()

    def _execute_with_chaos(self, call_record: Any, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Core retry loop and chaos injection logic.
        
        Args:
            call_record: A mutable data object to track timing and results (framework specific).
            func: The actual tool function to execute.
            *args, **kwargs: Arguments to the tool function.
        """
        context = {
            "tool_name": self._tool_name,
            "args": args,
            "kwargs": kwargs,
        }

        if self.verbose:
            self._logger.tool_call(self._tool_name, args, kwargs)

        retries = 0
        last_error = None
        fault_injected = None

        while retries <= self._max_retries:
            try:
                # Check injectors before call
                for injector in self._injectors:
                    if injector.should_inject(self._tool_name):
                        fault_type = injector.fault_type.value
                        fault_injected = fault_type
                        self._mttr.record_failure(self._tool_name, fault_type)

                        result, details = injector.inject(self._tool_name, context)
                        if result is not None:
                            call_record.end_time = time.time()
                            call_record.fault_injected = fault_type
                            call_record.result = result
                            self._call_history.append(call_record)
                            self._metrics.record_operation(
                                self._tool_name,
                                call_record.duration_ms,
                                success=False,
                                fault_type=fault_type,
                            )
                            return result

                # Execute the actual tool function
                result = func(*args, **kwargs)

                call_record.end_time = time.time()
                call_record.result = result
                call_record.retries = retries

                if fault_injected:
                    self._mttr.record_recovery(
                        self._tool_name,
                        fault_injected,
                        recovery_method="retry",
                        retries=retries,
                        success=True,
                    )
                    if self.verbose:
                        self._logger.recovery(self._tool_name, retries, True)

                if self.verbose:
                    self._logger.tool_result(result, call_record.duration_ms)

                self._call_history.append(call_record)
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
                call_record.retries = retries

                if retries <= self._max_retries:
                    if self.verbose:
                        self._logger.retry(retries, self._max_retries, self._retry_delay)
                    time.sleep(self._retry_delay)
                else:
                    break

        call_record.end_time = time.time()
        call_record.error = str(last_error)
        self._call_history.append(call_record)

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
            if self.verbose:
                self._logger.recovery(self._tool_name, retries, False)

        if self.verbose and last_error is not None:
            self._logger.tool_error(last_error, call_record.duration_ms)

        assert last_error is not None
        raise last_error

    def get_call_history(self) -> List[Any]:
        return self._call_history.copy()

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.get_summary()

    def reset(self):
        self._call_history.clear()
        self._metrics.reset()
        self._mttr.reset()
        for injector in self._injectors:
            injector.reset()


class BaseChaosWrapper:
    """Base class for wrapping AI agent frameworks."""

    def __init__(
        self,
        chaos_level: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        verbose: bool = False,
    ):
        self._chaos_level = chaos_level
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self.verbose = verbose
        self._logger = get_logger()

        self._tool_proxies: Dict[str, BaseChaosProxy] = {}
        self._injectors: List[BaseInjector] = []
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()
        self._kickoff_count = 0

        self._experiments: List[Experiment] = []
        self._experiment_results: List[ExperimentResult] = []
        self._current_experiment: Optional[Experiment] = None

    @property
    def chaos_level(self) -> float:
        return self._chaos_level

    def configure_chaos(
        self,
        chaos_level: float = 1.0,
        enable_tool_failures: bool = True,
        enable_delays: bool = True,
        enable_hallucinations: bool = True,
        enable_context_corruption: bool = True,
        enable_budget_exhaustion: bool = True,
    ):
        """Configure chaos injection for all tools."""
        self._chaos_level = chaos_level
        self._injectors.clear()
        base_prob = 0.1 * chaos_level

        if enable_tool_failures:
            self._injectors.append(ToolFailureInjector(ToolFailureConfig(probability=base_prob)))

        if enable_delays:
            self._injectors.append(DelayInjector(DelayConfig(probability=base_prob * 2)))

        if enable_hallucinations:
            self._injectors.append(
                HallucinationInjector(HallucinationConfig(probability=base_prob * 0.5))
            )

        if enable_context_corruption:
            self._injectors.append(
                ContextCorruptionInjector(ContextCorruptionConfig(probability=base_prob * 0.3))
            )

        if enable_budget_exhaustion:
            self._injectors.append(
                BudgetExhaustionInjector(BudgetExhaustionConfig(probability=1.0))
            )

        # Apply injectors to all tool proxies
        for proxy in self._tool_proxies.values():
            proxy.clear_injectors()
            for injector in self._injectors:
                proxy.add_injector(injector)

    def add_injector(self, injector: BaseInjector, tools: Optional[List[str]] = None):
        targets = tools or list(self._tool_proxies.keys())
        for name in targets:
            if name in self._tool_proxies:
                self._tool_proxies[name].add_injector(injector)

    def get_wrapped_tools(self) -> Dict[str, BaseChaosProxy]:
        return self._tool_proxies.copy()

    def get_metrics(self) -> Dict[str, Any]:
        tool_metrics = {}
        for name, proxy in self._tool_proxies.items():
            tool_metrics[name] = proxy.get_metrics()

        return {
            "kickoff_count": self._kickoff_count,
            "tools": tool_metrics,
            "aggregate": self._metrics.get_summary(),
        }

    def get_mttr_stats(self) -> Dict[str, Any]:
        tool_stats = {}
        for name, proxy in self._tool_proxies.items():
            tool_stats[name] = proxy._mttr.get_recovery_stats()

        return {
            "tools": tool_stats,
            "aggregate": self._mttr.get_recovery_stats(),
        }

    def reset(self):
        self._kickoff_count = 0
        for proxy in self._tool_proxies.values():
            proxy.reset()
        self._metrics.reset()
        self._mttr.reset()

    @contextmanager
    def experiment(self, name: str, **config_kwargs):
        """Context manager for running chaos experiments."""
        config = ExperimentConfig(name=name, **config_kwargs)
        exp = Experiment(config)

        self._experiments.append(exp)
        self._current_experiment = exp

        try:
            exp.start()
            yield exp
        except Exception as e:
            exp.abort(str(e))
            raise
        finally:
            if exp.status.value == "running":
                result = exp.complete()
                self._experiment_results.append(result)
            self._current_experiment = None

    def get_experiment_results(self) -> List[ExperimentResult]:
        return self._experiment_results.copy()
