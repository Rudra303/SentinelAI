"""Adaptive Chaos Scheduling using ML to target fragile components."""

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class ComponentStats:
    """Statistics for a single component (tool/agent)."""
    invocations: int = 0
    failures: int = 0
    recovery_time_ms: float = 0.0

    @property
    def failure_rate(self) -> float:
        if self.invocations == 0:
            return 0.0
        return self.failures / self.invocations

class AdaptiveScheduler:
    """
    Uses Multi-Armed Bandit (UCB1) to learn component weaknesses
    and intelligently target fragile parts of the system.
    """
    def __init__(self, exploration_weight: float = 1.41):
        self.exploration_weight = exploration_weight
        self.stats: Dict[str, ComponentStats] = {}
        self.total_invocations = 0

    def record_result(self, component: str, success: bool, recovery_time_ms: float = 0.0):
        """Update the ML model with new execution data."""
        if component not in self.stats:
            self.stats[component] = ComponentStats()
            
        self.stats[component].invocations += 1
        if not success:
            self.stats[component].failures += 1
            self.stats[component].recovery_time_ms += recovery_time_ms
            
        self.total_invocations += 1

    def select_target(self, available_components: List[str]) -> Optional[str]:
        """
        Select the next component to inject chaos into.
        Prioritizes components that have a high failure rate but still
        explores untested components.
        """
        if not available_components:
            return None

        # Exploration phase: try components that haven't been tested yet
        untested = [c for c in available_components if c not in self.stats or self.stats[c].invocations == 0]
        if untested:
            return random.choice(untested)

        # UCB1 algorithm for Exploitation vs Exploration
        best_target = None
        max_score = -float('inf')

        for component in available_components:
            stat = self.stats[component]
            # Exploit: high failure rate = good target for chaos
            exploitation = stat.failure_rate
            # Explore: components we haven't tested much recently
            exploration = self.exploration_weight * math.sqrt(
                math.log(self.total_invocations) / stat.invocations
            )
            
            score = exploitation + exploration
            
            if score > max_score:
                max_score = score
                best_target = component

        return best_target
