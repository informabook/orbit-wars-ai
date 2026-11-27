"""Parallel, checkpointed execution for explicit local match schedules."""

from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from ..framework.matches import run_match, terminal
from .policies import bind_candidate


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=False).encode()).hexdigest()


def save_json(path, data):
    # Write on the same volume, so an interrupted write never creates a half-valid record.
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            json.dump(data, handle, indent=2, allow_nan=False)
            handle.write("\n")
        except BaseException:
            handle.close()
            temporary.unlink()
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def start_checkpoint(root, configuration):
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / "checkpoint.json"
    key = digest(configuration)
    if manifest.exists() and json.loads(manifest.read_text(encoding="utf-8")).get("key") != key:
        raise ValueError("Checkpoint settings changed; use a fresh output directory")
    if not manifest.exists():
        save_json(manifest, {"key": key, "configuration": configuration})
    records = root / "match-records"
    records.mkdir(exist_ok=True)
    return records


def registry_hashes(registry):
    hashes = {}
    for name, entry in registry.items():
        digest_value = hashlib.sha256(Path(entry["path"]).read_bytes()).hexdigest()
        if digest_value != entry["sha256"]:
            raise ValueError(f"Registered source changed: {name}")
        hashes[name] = digest_value
    return hashes


def run_one(task, registry, candidates):
    binder = partial(bind_candidate, candidates=candidates)
    return run_match(task, registry, bind_policy=binder)


def execute(tasks, records, registry, candidates, executor=None):
    """Record each attempt once. Return rows in schedule order even when jobs finish out of order."""
    work = {}
    rows = {}
    futures = {}
    for task in tasks:
        key = digest([task.match_id, list(task.agents), task.seed, task.episode_steps,
                      task.candidate_slot, candidates])
        path = records / f"{key}.json"
        if path.exists():
            row = json.loads(path.read_text(encoding="utf-8"))
            if (row["match_id"] != task.match_id or row["agents"] != list(task.agents)
                    or row["seed"] != task.seed or row["episode_steps"] != task.episode_steps
                    or row["candidate_slot"] != task.candidate_slot or row["status"] not in {"OK", "ERROR"}):
                raise ValueError("Checkpoint contains inconsistent match records")
            if row["status"] == "OK":
                states = [{"status": s, "reward": r} for s, r in zip(row["terminal_statuses"], row["rewards"], strict=True)]
                if row["applied_seed"] != task.seed or terminal(states, len(task.agents))[2]:
                    raise ValueError("Checkpoint contains invalid terminal evidence")
            rows[task.match_id] = row
        elif executor is None:
            row = run_one(task, registry, candidates)
            save_json(path, row)
            rows[task.match_id] = row
        else:
            work[task.match_id] = path
            futures[executor.submit(run_one, task, registry, candidates)] = task.match_id
    for future in as_completed(futures):
        identifier = futures[future]
        row = future.result()
        save_json(work[identifier], row)
        rows[identifier] = row
    return [rows[task.match_id] for task in tasks]


def pool(workers):
    if workers not in (1, 2, 3, 4):
        raise ValueError("Workers must be between one and four")
    return ProcessPoolExecutor(max_workers=workers)

