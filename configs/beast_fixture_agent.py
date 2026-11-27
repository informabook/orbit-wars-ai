"""Synthetic patchable baseline for the Beast Lab API example."""

import dataclasses
import math


@dataclasses.dataclass
class PlannerConfig:
    horizon: int = 18
    max_offensive_targets: int = 6
    roi_threshold: float = 1.65
    min_ships_to_launch: float = 6.0
    max_sources_per_lane: int = 4
    max_waves_per_turn: int = 2
    max_defensive_targets: int = 2
    reinforce_size_beta: float = 1.8
    max_regroup_time: float = 6.0


CONFIG = PlannerConfig()
CONFIG_4P = dataclasses.replace(
    CONFIG,
    horizon=12,
    max_offensive_targets=5,
    roi_threshold=1.85,
    min_ships_to_launch=7.0,
)


def agent(observation, configuration=None):
    del configuration
    player = observation["player"]
    planets = observation["planets"]
    active = {p[1] for p in planets if p[1] >= 0}
    policy = CONFIG_4P if len(active) > 2 else CONFIG
    owned = [p for p in planets if p[1] == player and p[5] >= 2 * policy.min_ships_to_launch]
    targets = [p for p in planets if p[1] != player]
    if not owned or not targets:
        return []
    source = max(owned, key=lambda p: p[5])
    targets.sort(key=lambda p: math.hypot(p[2] - source[2], p[3] - source[3]))
    target = max(targets[:policy.max_offensive_targets], key=lambda p: p[6] / max(1, p[5]))
    cost = math.hypot(target[2] - source[2], target[3] - source[3])
    if cost > policy.horizon * policy.roi_threshold:
        return []
    return [[source[0], math.atan2(target[3] - source[3], target[2] - source[2]), int(source[5]) // 2]]
