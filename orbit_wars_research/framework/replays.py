"""Local JSON-only replay ingestion with stable replay grouping."""

import csv
import hashlib
import json

from .. import ranker_v14, replay_features_v14
from .matches import terminal

MAX_BYTES = 64 * 1024 * 1024


def load_replay(path):
    if path.suffix.lower() != ".json" or path.stat().st_size > MAX_BYTES:
        raise ValueError("Supply unpacked replay JSON of at most 64 MiB per file")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("name") != "orbit_wars":
        raise ValueError("Input is not a Kaggle Orbit Wars replay")
    steps = data.get("steps")
    if not isinstance(steps, list) or len(steps) < 2 or not isinstance(steps[0], list):
        raise ValueError("Replay lacks a complete step sequence")
    players = len(steps[0])
    if players not in (2, 4) or any(
        not isinstance(step, list) or len(step) != players or any(not isinstance(agent, dict) for agent in step)
        for step in steps
    ):
        raise ValueError("Replay step records must have consistent 2P or 4P seats")
    _, rewards, error = terminal(steps[-1], players)
    if error or rewards != data.get("rewards"):
        raise ValueError("Replay requires valid terminal statuses and consistent rewards")
    # Exclude metadata, IDs and unrelated fields when hashing playable content.
    payload = {"steps": [[{key: state.get(key) for key in ("action", "observation")}
                          for state in step] for step in steps], "rewards": rewards}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode()).hexdigest(), data


def export_features(paths, output):
    if output.exists():
        raise FileExistsError("Feature output already exists")
    if not paths:
        raise ValueError("Supply replay files")
    seen = set()
    rows = []
    for path in paths:
        group, data = load_replay(path)
        if group in seen:
            continue
        seen.add(group)
        x, y, weights, _ = replay_features_v14.traiter_un_replay((group, data))
        rows.extend((group, label, weight, *values) for values, label, weight in zip(x, y, weights, strict=True))
    if not rows:
        raise ValueError("No feature rows extracted. V14 requires a unique winner with identifiable launches.")
    features = ranker_v14.FEATURES
    if any(len(row) != len(features) + 3 for row in rows):
        raise ValueError("Recovered extractor feature order does not align with V14")
    with output.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["replay_id", "label", "weight", *features])
        writer.writerows(rows)
    return len(rows)

