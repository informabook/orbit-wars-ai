"""Original Beast Lab and V6 workflows with bounded, explicit local inputs."""

from contextlib import nullcontext
from dataclasses import asdict
import ast
import gzip
import hashlib
import io
import random
import re
import tarfile
from types import SimpleNamespace

from .. import beast, orbitlab
from ..framework.agents import bind, read_registry, register
from ..framework.experiments import STAGES, budget, evaluate, write_experiment
from ..framework.matches import Match
from ..framework.replays import load_replay
from . import beast_v18, bracket_v6
from .checkpoint import execute, pool, registry_hashes, save_json, start_checkpoint
from .policies import COMBINATIONS, MUTATIONS


def guided(paths, base, config, output, count, seed, candidate_index, evaluate_all, charts=False, opponents=None):
    if not 1 <= len(paths) <= 20 or not 2 <= count <= 16 or not 0 <= candidate_index <= count:
        raise ValueError("Use 1–20 replays, 2–16 population members and a valid candidate index (including the child)")
    source = base.read_bytes()
    compile(source, base.name, "exec")
    output.mkdir(parents=True, exist_ok=False)
    tables = output / "tables"
    beast_v18.run_failure_situation_analysis(paths, tables, output / "charts" if charts else None)
    stats = []
    for name, replay in beast_v18.load_replay_objects(paths):
        row = beast_v18.analyse_one_replay(name, replay)
        if row is None:
            raise ValueError(f"Missing Beast Lab replay summary for {name}")
        stats.append(row)
    beast_v18.write_csv(tables / "replay_statistics.csv", stats)
    profile = beast_v18.load_failure_profile(tables)
    rng = random.Random(seed)
    population = beast_v18.build_guided_population(profile, rng, count, 0)
    population.append(beast_v18.mutate_spec_guided(population[0], profile, rng, 0, 1))
    save_json(output / "population.json", [asdict(member) for member in population])
    selected = population[candidate_index]
    private = output / "private-agents"
    private.mkdir()
    registered = private / "agents.json"
    baseline = private / "main.py"
    baseline.write_bytes(source)
    if baseline not in beast_v18.discover_patch_targets(private):
        raise ValueError("No compatible typed V18 patch targets in the single-file baseline")
    text = source.decode("utf-8-sig").replace("\r\n", "\n")
    patched = beast.patch_config4p(beast.patch_global(text, selected.global_params), selected.fourp_params)
    if patched == text:
        raise ValueError("Selected candidate made no effective source patch")
    variant = private / "variant.py"
    variant.write_text(patched, encoding="utf-8", newline="\n")
    register(registered, "guided-base", baseline)
    register(registered, "guided-candidate", variant)
    if {"guided-base", "guided-candidate"} & set(opponents or {}):
        raise ValueError("guided-base and guided-candidate are reserved IDs")
    registry = {**(opponents or {}), **read_registry(registered)}
    for name in ("guided-base", "guided-candidate"):
        bind(name, 2, registry)
    validation = {"opponents": ["guided-base"], **config}
    result = evaluate(validation, "guided-candidate", registry, STAGES, gated=not evaluate_all)
    recipe = {"validation": validation, "seed": seed, "population_size": count,
              "selected": asdict(selected), "baseline_sha256": hashlib.sha256(source).hexdigest(),
              "gate_bypass": evaluate_all, "replay_seats": "seat zero"}
    write_experiment(output / "validation", "beast-guided", recipe, result, registry)
    return result["matches"]


def check_agents(names, registry, minimum, maximum):
    if not minimum <= len(names) <= maximum or len(set(names)) != len(names):
        raise ValueError(f"Provide {minimum}–{maximum} distinct agent IDs")
    for name in names:
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,47}", name) or name not in {"hold", "nearest", *registry}:
            raise ValueError(f"Unknown or invalid agent ID: {name}")


def evolve(names, registry, output, seed, generations, variants, best_of, workers, max_games, steps):
    check_agents(names, registry, 2, 8)
    if not 1 <= generations <= 4 or not 1 <= best_of <= 4:
        raise ValueError("Use 1–4 generations and 1–4 games per duel")
    if not variants or len(variants) != len(set(variants)) or not set(variants) <= set(MUTATIONS):
        raise ValueError("Choose distinct V6 mutation strategies")
    second_size = 4 + 2 * len(variants)
    expected = (len(names) - 2 + generations * (second_size - 2) + len(names) + 2) * best_of
    budget({"max_games": max_games}, expected)
    identity = {"workflow": "intelligent-v6", "version": 1, "agents": list(names),
                "sha256": registry_hashes(registry), "seed": seed, "generations": generations,
                "strategies": list(variants), "best_of": best_of, "steps": steps, "max_games": max_games}
    records = start_checkpoint(output, identity)
    definitions = {}
    history = []
    originals = [bracket_v6.Candidate(name) for name in names]
    current = originals

    def create(strategy, generation, side, parents):
        parent_names = [parent.name for parent in parents]
        name = f"v6-g{generation}-{side}-{strategy}"
        if name in names:
            raise ValueError("Agent ID collides with a generated V6 candidate")
        definitions[name] = {"strategy": strategy, "generation": generation,
                             "side": side, "parents": parent_names}
        return bracket_v6.Candidate(name, strategy, generation, parent_names)

    with pool(workers) if workers != 1 else nullcontext() as executor:
        def play(round_tasks):
            tasks = [Match(f"{t['match_id']}-{index}", (t["a_name"], t["b_name"]), t["seed"], steps)
                     for index, t in enumerate(round_tasks)]
            rows = execute(tasks, records, registry, definitions, executor)
            if any(row["status"] != "OK" for row in rows):
                raise ValueError("A bracket round has failed matches. See the saved attempt records.")
            round_rows = []
            for task, row in zip(round_tasks, rows, strict=True):
                a, b = row["agents"]
                left, right = row["rewards"]
                winner = a if left > right else b if right > left else ""
                round_rows.append({**row, "phase": task["phase"], "round": task["round"],
                                   "a": a, "b": b, "winner": winner, "reward_a": left, "reward_b": right})
            history.extend(round_rows)
            return round_rows

        top4 = []
        for generation in range(1, generations + 1):
            left, right = bracket_v6.initial_left_right_finalists(
                current, f"step{generation}_initial", best_of, seed + generation * 1000, play)
            challengers = [left, right]
            for side, finalist in (("left", left), ("right", right)):
                challengers.extend(create(strategy, generation, side, [finalist]) for strategy in variants)
            challengers.extend(create(strategy, generation, "combo", [left, right]) for strategy in COMBINATIONS)
            phase = f"step{generation}_second8"
            current = bracket_v6.initial_left_right_finalists(
                challengers, phase, best_of, seed + generation * 1000 + 777, play)
            top4 = bracket_v6.bracket_rank(challengers, history, phase)[:4]

        final_pool = list({entry.name: entry for entry in originals + top4}.values())
        phase = "final_originals_plus_top4"
        bracket_v6.initial_left_right_finalists(final_pool, phase, best_of, seed + 999999, play)
        ranked = bracket_v6.bracket_rank(final_pool, history, phase)
    generated = next((entry.name for entry in ranked if entry.generation), None)
    outcome = {"best": ranked[0].name, "best_generated": generated,
               "ranked_finalists": [entry.name for entry in ranked],
               "lineage": definitions, "matches": history}
    save_json(output / "results.json", outcome)
    return history


def orbitlab_tournament(names, registry, output, seed, repeats, modes, workers, max_games, steps):
    check_agents(names, registry, 4 if "4p" in modes else 2, 8)
    if not 1 <= repeats <= 4 or not modes or not set(modes) <= {"2p", "4p"}:
        raise ValueError("Use 1–4 repetitions and modes 2p or 4p")
    args = SimpleNamespace(seed=seed, modes=modes, snapshot_step=20, repeats_2p=repeats,
                           swap_positions=True, repeats_4p=repeats, max_4p=max_games)
    schedule = orbitlab.construire_taches([{"agent": name, "path": name} for name in names], args)
    budget({"max_games": max_games}, len(schedule))
    tasks = [Match(row["match_id"], tuple(row["agents"]), row["seed"], steps) for row in schedule]
    identity = {"workflow": "orbitlab", "version": 1, "agents": list(names), "modes": list(modes),
                "sha256": registry_hashes(registry), "seed": seed, "repeats": repeats,
                "steps": steps, "max_games": max_games}
    records = start_checkpoint(output, identity)
    with pool(workers) if workers != 1 else nullcontext() as executor:
        rows = execute(tasks, records, registry, {}, executor)

    totals = {}
    for row in rows:
        for index, name in enumerate(row["agents"]):
            info = totals.setdefault((row["mode"], name), {"mode": row["mode"], "agent": name,
                                     "completed": 0, "errors": 0, "reward_sum": 0,
                                     "top1": 0, "shared_top1": 0})
            if row["status"] != "OK":
                info["errors"] += 1
                continue
            info["completed"] += 1
            rewards = row["rewards"]
            info["reward_sum"] += rewards[index]
            if rewards[index] == max(rewards):
                info["top1"] += rewards.count(rewards[index]) == 1
                info["shared_top1"] += rewards.count(rewards[index]) > 1
    for info in totals.values():
        count = info["completed"]
        info["mean_reward"] = info["reward_sum"] / count if count else None
    save_json(output / "results.json", {"matches": rows, "leaderboard": list(totals.values())})
    return rows


def orbitlab_diagnose(source, output, every):
    if not 1 <= every <= 500:
        raise ValueError("Snapshot interval must be 1–500")
    fingerprint, replay = load_replay(source)
    players = len(replay["rewards"])
    aliases = [f"seat-{index}" for index in range(players)]
    snapshots, actions = orbitlab.snapshots_depuis_env_steps(
        "local-replay", f"{players}p", aliases, replay["steps"], every)
    if not snapshots:
        raise ValueError("No OrbitLab snapshots could be extracted")
    output.mkdir(parents=True, exist_ok=False)
    beast_v18.write_csv(output / "snapshots.csv", snapshots)
    beast_v18.write_csv(output / "actions.csv", actions)
    save_json(output / "manifest.json", {"replay_content_sha256": fingerprint,
                                       "snapshot_rows": len(snapshots), "action_rows": len(actions)})
    return len(snapshots)


def packaging(source, output):
    """Write a deterministic, local TAR from one explicitly supplied Python entry point."""
    if source.is_symlink() or source.suffix.lower() != ".py" or source.stat().st_size > 1024 * 1024:
        raise ValueError("Provide a regular Python agent file no larger than 1 MiB")
    data = source.read_bytes()
    tree = ast.parse(data, filename=source.name)
    if not any(isinstance(node, ast.FunctionDef) and node.name == "agent" for node in tree.body):
        raise ValueError("Provide a module defining a top-level agent function")
    with output.open("xb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
        with tarfile.open(mode="w", fileobj=stream) as archive:
            metadata = tarfile.TarInfo("main.py")
            metadata.size = len(data)
            metadata.mode = 0o644
            archive.addfile(metadata, io.BytesIO(data))
