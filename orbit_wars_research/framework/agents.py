"""Explicit local agent registration, demo policies and data-only variants."""

import hashlib
import importlib.util
import inspect
import json
import math
import random
import re
import sys
from pathlib import Path

DEMO_IDS = ("hold", "nearest")
MUTATIONS = ((0.70, 0.0), (0.85, 0.06), (1.10, -0.06), (1.25, 0.0))


def hold(observation, configuration=None):
    """New demonstration baseline. Keep all ships in place."""
    return []


def nearest(observation, configuration=None):
    """New demonstration policy. Aim at the nearest non-owned planet."""
    player = observation["player"]
    planets = observation["planets"]
    sources = [p for p in planets if p[1] == player and p[5] >= 12]
    targets = [p for p in planets if p[1] != player]
    if not sources or not targets:
        return []
    source = min(sources, key=lambda p: (-p[5], p[0]))
    target = min(targets, key=lambda p: ((p[2] - source[2]) ** 2 + (p[3] - source[3]) ** 2, p[0]))
    return [[source[0], math.atan2(target[3] - source[3], target[2] - source[2]), int(source[5]) // 2]]


def read_registry(path):
    return json.loads(path.read_text(encoding="utf-8")) if path and path.exists() else {}


def register(registry, identifier, source):
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,47}", identifier) or identifier in DEMO_IDS:
        raise ValueError("Choose a new identifier using lowercase letters, digits, '_' or '-'.")
    if source.suffix != ".py" or not source.is_file():
        raise ValueError("Provide a local Python module.")
    data = source.read_bytes()
    compile(data, source.name, "exec")
    entries = read_registry(registry)
    if identifier in entries:
        raise ValueError("Agent identifier already registered.")
    entries[identifier] = {
        "path": str(source.resolve()),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


def bind(reference, players, registry):
    """Construct a fresh policy for one seat in one match."""
    if reference == "hold":
        return hold
    if reference == "nearest":
        return nearest
    if isinstance(reference, str):
        entry = registry.get(reference)
        if entry is None:
            raise ValueError(f"Unknown agent: {reference}")
        path = Path(entry["path"])
        source = path.read_bytes()
        if hashlib.sha256(source).hexdigest() != entry["sha256"]:
            raise ValueError(f"Registered source changed: {reference}")
        name = "_orbit_local_" + entry["sha256"][:24]
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None:
            raise ValueError("Cannot construct a module spec")
        module = importlib.util.module_from_spec(spec)
        previous = sys.modules.get(name)
        sys.modules[name] = module
        try:
            exec(compile(source, path.name, "exec"), module.__dict__)
        finally:
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
        policy = module.agent
        signature = inspect.signature(policy)
        try:
            signature.bind({}, {})
        except TypeError:
            signature.bind({})
            return lambda observation, configuration: policy(observation)
        return lambda observation, configuration: policy(observation, configuration)

    if reference["kind"] == "router":
        return bind(reference["two"] if players == 2 else reference["four"], players, registry)
    if reference["kind"] != "mutation":
        raise ValueError("Unknown variant kind")
    scale, angle = float(reference["ship_scale"]), float(reference["angle_shift"])
    if not math.isfinite(scale) or not 0 < scale <= 2 or not math.isfinite(angle) or abs(angle) > math.pi:
        raise ValueError("Invalid mutation parameters")
    parent = bind(reference["parent"], players, registry)

    def mutate(observation, configuration):
        output = parent(observation, configuration)
        if not isinstance(output, list):
            raise ValueError("Agent actions must be a list")
        available = {p[0]: int(p[5]) for p in observation["planets"] if p[1] == observation["player"]}
        moves = []
        for planet, heading, count in output:
            if planet not in available or count < 1 or not math.isfinite(float(heading)):
                raise ValueError("Parent returned an invalid move")
            use = min(available[planet], max(1, round(count * scale)))
            if use:
                available[planet] -= use
                moves.append([planet, (float(heading) + angle + math.pi) % math.tau - math.pi, use])
        return moves
    return mutate


def candidate_id(reference):
    if isinstance(reference, str):
        return reference
    return hashlib.sha256(json.dumps(reference, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def generate(parent, seed, count):
    """Sample distinct parameter changes in seeded order, with explicit lineage."""
    if not 1 <= count <= len(MUTATIONS):
        raise ValueError("Variant count must be between one and four")
    return [
        {"kind": "mutation", "parent": parent, "ship_scale": scale, "angle_shift": angle}
        for scale, angle in random.Random(seed).sample(MUTATIONS, count)
    ]

