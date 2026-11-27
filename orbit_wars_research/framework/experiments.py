"""Bounded schedules, explicit stage decisions and experiment records."""

import csv
import json
import statistics
from collections import Counter
from importlib.metadata import PackageNotFoundError, version

from .. import beast
from .agents import candidate_id, generate
from .matches import Match, run_match, terminal

STAGES = ("fast", "anti-mirage", "full", "holdout")
GATES = dict(zip(STAGES, (beast.pass_fast, beast.pass_anti_mirage, beast.pass_full, beast.pass_holdout)))
MAX_GAMES = 256


def budget(config, games):
    limit = config.get("max_games", 24)
    if type(limit) is not int or not 1 <= games <= limit <= MAX_GAMES:
        raise ValueError(f"Planned {games} games. Require 1 <= games <= max_games <= {MAX_GAMES}.")


def tournament(config, registry, runner=run_match):
    lineups = config["lineups"]
    repeats = config.get("repeats", 1)
    if type(repeats) is not int or repeats < 1:
        raise ValueError("repeats must be a positive integer")
    budget(config, len(lineups) * repeats)
    tasks = []
    for lineup in lineups:
        for repeat in range(repeats):
            ordinal = len(tasks)
            rotation = repeat % len(lineup)
            tasks.append(Match(f"t{ordinal:04d}", tuple(lineup[rotation:] + lineup[:rotation]),
                               config["seed"] + ordinal, config["episode_steps"]))
    return {"matches": [runner(task, registry) for task in tasks]}


def evaluation_plan(config, candidate, stage_names):
    """Build all stage tasks before play and reject seed reuse across stages."""
    if set(config["stages"]) != set(STAGES):
        raise ValueError(f"Specify each stage in the configuration: {', '.join(STAGES)}.")
    plans = {}
    seen_seeds = set()
    for stage in STAGES:
        settings = config["stages"][stage]
        rounds = settings.get("rounds", 1)
        if type(rounds) is not int or not 1 <= rounds <= 16:
            raise ValueError("rounds must be between one and sixteen")
        if stage == "anti-mirage" and rounds < 2:
            raise ValueError("Anti-Mirage needs at least two independently seeded rounds")
        tasks = []
        for round_index in range(rounds):
            for players in (2, 4):
                games = settings[f"games{players}"]
                if type(games) is not int or not 1 <= games <= 64:
                    raise ValueError("Each mode needs between one and sixty-four games")
                pool = settings.get("opponents", config["opponents"])
                if not isinstance(pool, list) or not pool:
                    raise ValueError("Evaluation requires an opponent pool.")
                for game in range(games):
                    seed = settings["seed"] + len(tasks)
                    if seed in seen_seeds:
                        raise ValueError(f"Seed reused across stages: {seed}")
                    seen_seeds.add(seed)
                    slot = game % players
                    lineup = [pool[(game * (players - 1) + k) % len(pool)] for k in range(players - 1)]
                    lineup.insert(slot, candidate)
                    task = Match(f"{stage}-{round_index:02d}-{players}p-{game:03d}", tuple(lineup),
                                 seed, config["episode_steps"], slot)
                    tasks.append((round_index, task))
        plans[stage] = tasks
    return {stage: plans[stage] for stage in stage_names}


def metrics(rows):
    usable = []
    for row in rows:
        if row["status"] != "OK":
            continue
        statuses = row.get("terminal_statuses") or []
        rewards = row.get("rewards") or []
        players = {"2P": 2, "4P": 4}[row["mode"]]
        packed = [{"status": s, "reward": r} for s, r in zip(statuses, rewards)]
        _, _, problem = terminal(packed, players)
        if (problem or len(statuses) != players or len(rewards) != players
                or row.get("applied_seed") != row.get("seed") or row.get("seed") is None):
            row.update(status="ERROR", rewards=None, reason=problem or "bad_match_evidence")
        else:
            usable.append(row)
    samples = {mode: [beast.delta_from_rewards(r["rewards"], r["candidate_slot"])
                      for r in usable if r["mode"] == mode] for mode in ("2P", "4P")}
    errors = len(rows) - len(usable)
    if not all(samples.values()):
        return {"ok": False, "errors": errors, "n2p": len(samples["2P"]), "n4p": len(samples["4P"])}
    d2, d4 = samples["2P"], samples["4P"]
    mean2p, mean4p = statistics.mean(d2), statistics.mean(d4)
    low, high = beast.bootstrap_ci(d2 + d4)
    return {"ok": not errors, "errors": errors, "n2p": len(d2), "n4p": len(d4),
            "mean2p": mean2p, "mean4p": mean4p, "combined": 0.45 * mean2p + 0.55 * mean4p,
            "ci_all_low": low, "ci_all_high": high}


def evaluate(config, candidate, registry, stage_names=STAGES, gated=True, runner=run_match):
    plans = evaluation_plan(config, candidate, stage_names)
    budget(config, sum(len(tasks) for tasks in plans.values()))
    results = {"matches": [], "stages": []}
    halted = False
    for stage, tasks in plans.items():
        if halted:
            results["stages"].append({"stage": stage, "decision": "SKIPPED", "reason": "previous_stage_rejected"})
            continue
        matches = []
        for round_index, task in tasks:
            matches.append({**runner(task, registry), "stage": stage, "round": round_index})
        results["matches"].extend(matches)
        summary = metrics(matches)
        if stage == "anti-mirage":
            rounds = [metrics([r for r in matches if r["round"] == n]) for n in sorted({r["round"] for r in matches})]
            if all(r["ok"] for r in rounds):
                summary.update(beast.aggregate_eval_rounds(rounds))
            else:
                summary["ok"] = False
        passed = summary["ok"] and GATES[stage](summary)
        reason = "thresholds_met" if passed else "match_failed" if summary["errors"] else "thresholds_not_met"
        results["stages"].append({"stage": stage, "decision": "PASS" if passed else "REJECT",
                                  "reason": reason, "metrics": summary})
        halted = gated and not passed
    results["holdout_pool_shared"] = bool(
        {candidate_id(opponent) for opponent in config["stages"]["holdout"].get("opponents", config["opponents"])}
        & {candidate_id(opponent) for stage in STAGES[:-1]
           for opponent in config["stages"][stage].get("opponents", config["opponents"])}
    )
    return results


def search(config, candidate, registry, runner=run_match):
    generations, variants = config["generations"], config["variants"]
    if type(generations) is not int or not 1 <= generations <= 8:
        raise ValueError("generations must be between one and eight")
    if type(variants) is not int or not 1 <= variants <= 4:
        raise ValueError("variants must be between one and four")
    plan = evaluation_plan(config, candidate, ("fast",))
    budget(config, generations * variants * len(plan["fast"]))
    results = {"candidates": [], "matches": [], "generation_winners": []}
    parent = candidate
    for generation in range(1, generations + 1):
        eligible = []
        for variant in generate(parent, config["seed"] + generation, variants):
            key = candidate_id(variant)
            outcome = evaluate(config, variant, registry, ("fast",), runner=runner)
            judgment = outcome["stages"][0]
            row = {"candidate_id": key, "parent_id": candidate_id(parent), "generation": generation,
                   "definition": variant, **judgment}
            results["candidates"].append(row)
            results["matches"].extend({**r, "match_id": f"{generation}-{key}-{r['match_id']}",
                                       "generation": generation, "candidate_id": key} for r in outcome["matches"])
            if judgment["metrics"]["ok"]:
                eligible.append(row)
        if not eligible:
            break
        winner = max(eligible, key=lambda r: (r["metrics"]["combined"], r["candidate_id"]))
        results["generation_winners"].append(winner["candidate_id"])
        parent = winner["definition"]
    return results


def write_experiment(output, operation, config, result, registry=None):
    """Keep the recipe, all attempt records and scores in an explicit output directory."""
    output.mkdir(parents=True, exist_ok=False)
    try:
        engine = version("kaggle-environments")
    except PackageNotFoundError:
        engine = None
    statuses = Counter(row["status"] for row in result.get("matches", []))
    sources = {name: entry["sha256"] for name, entry in (registry or {}).items()}
    manifest = {"schema_version": 1, "operation": operation, "engine": engine,
                "statuses": dict(statuses), "config": config, "registered_source_hashes": sources}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    matches = result.get("matches", [])
    if matches:
        columns = list(dict.fromkeys(key for row in matches for key in row))
        with (output / "matches.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            for row in matches:
                writer.writerow({key: json.dumps(value, separators=(",", ":")) if isinstance(value, (tuple, list, dict))
                                 else value for key, value in row.items()})

