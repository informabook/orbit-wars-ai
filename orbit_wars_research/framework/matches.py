"""Strict, seeded match execution shared by tournament and validation."""

import math
import os
import random
import time
from dataclasses import asdict, dataclass
from numbers import Real

from .agents import bind


@dataclass(frozen=True)
class Match:
    match_id: str
    agents: tuple
    seed: int
    episode_steps: int
    candidate_slot: int | None = None

    def __post_init__(self):
        if len(self.agents) not in (2, 4):
            raise ValueError("Only 2P and 4P lineups are supported")
        if type(self.seed) is not int or not 0 <= self.seed < 2**31:
            raise ValueError("Seed must be an integer in [0, 2**31)")
        if type(self.episode_steps) is not int or not 4 <= self.episode_steps <= 500:
            raise ValueError("episode_steps must be between 4 and 500")
        if self.candidate_slot is not None and not 0 <= self.candidate_slot < len(self.agents):
            raise ValueError("Invalid candidate slot")


def terminal(states, players):
    """Preserve engine statuses and report whether a score can be used."""
    statuses = [state.get("status") for state in states]
    rewards = [state.get("reward") for state in states]
    if len(states) != players:
        return statuses, None, "unexpected_player_count"
    if any(status != "DONE" for status in statuses):
        return statuses, None, "invalid_terminal_status"
    if any(isinstance(r, bool) or not isinstance(r, Real) or not math.isfinite(r) or r not in (-1, 1)
           for r in rewards):
        return statuses, None, "invalid_reward"
    return statuses, [float(r) for r in rewards], None


def make_game(**kwargs):
    os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    from kaggle_environments import make
    return make("orbit_wars", **kwargs)


def run_match(task, registry=None, make=make_game, *, bind_policy=bind):
    """Run one match. A missing/mismatched simulator seed is a failed attempt."""
    result = asdict(task)
    result.update(mode=f"{len(task.agents)}P", status="ERROR", terminal_statuses=[],
                  rewards=None, applied_seed=None, turns=None, reason=None)
    start = time.perf_counter()
    rng_state = random.getstate()
    try:
        random.seed(task.seed)
        env = make(configuration={"seed": task.seed, "episodeSteps": task.episode_steps,
                                  "actTimeout": 1, "runTimeout": 15}, debug=False)
        env.reset(len(task.agents))
        result["applied_seed"] = env.info.get("seed")
        if result["applied_seed"] != task.seed:
            result["reason"] = "seed_not_applied"
            return result

        def adapter(policy):
            def agent(observation, configuration):
                return policy(observation, configuration)
            return agent

        env.run([adapter(bind_policy(ref, len(task.agents), registry or {})) for ref in task.agents])
        result["applied_seed"] = env.info.get("seed")
        result["turns"] = len(env.steps) - 1
        statuses, rewards, reason = terminal(env.steps[-1], len(task.agents))
        result["terminal_statuses"] = statuses
        if result["applied_seed"] != task.seed:
            result["reason"] = "seed_changed_during_run"
        elif reason:
            result["reason"] = reason
        else:
            result.update(status="OK", rewards=rewards)
    except Exception as exc:
        result["reason"] = f"exception:{type(exc).__name__}"
    finally:
        random.setstate(rng_state)
        result["duration_sec"] = round(time.perf_counter() - start, 6)
    return result

