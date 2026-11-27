"""Command-line interface for the recovered historical workflows."""

import argparse
import multiprocessing
from pathlib import Path

from ..framework.cli import load
from ..framework.agents import read_registry
from .workflows import evolve, guided, orbitlab_diagnose, orbitlab_tournament, packaging


def parser():
    app = argparse.ArgumentParser(description=__doc__)
    commands = app.add_subparsers(dest="operation", required=True)
    item = commands.add_parser("beast-guided")
    item.add_argument("replays", nargs="+", type=Path)
    item.add_argument("--base", type=Path, required=True)
    item.add_argument("--registry", type=Path)
    item.add_argument("--config", type=Path, required=True)
    item.add_argument("--out", type=Path, required=True)
    item.add_argument("--population", type=int, default=4)
    item.add_argument("--candidate-index", type=int, default=0)
    item.add_argument("--seed", type=int, default=42)
    item.add_argument("--evaluate-all", action="store_true")
    item.add_argument("--charts", action="store_true")

    for name in ("intelligent-v6", "orbitlab"):
        item = commands.add_parser(name)
        item.add_argument("agents", nargs="+")
        item.add_argument("--registry", type=Path)
        item.add_argument("--out", type=Path, required=True)
        item.add_argument("--seed", type=int, default=42)
        item.add_argument("--workers", type=int, choices=range(1, 5), default=1)
        item.add_argument("--max-games", type=int, default=16)
        item.add_argument("--steps", type=int, default=24)
        if name == "intelligent-v6":
            item.add_argument("--generations", type=int, default=1)
            item.add_argument("--best-of", type=int, default=1)
            item.add_argument("--variants", nargs="+", default=["expand"])
        else:
            item.add_argument("--repeats", type=int, default=1)
            item.add_argument("--modes", nargs="+", choices=("2p", "4p"), default=["2p"])
    item = commands.add_parser("orbitlab-diagnose")
    item.add_argument("replay", type=Path)
    item.add_argument("--every", type=int, default=20)
    item.add_argument("--out", type=Path, required=True)
    item = commands.add_parser("package-agent")
    item.add_argument("agent", type=Path)
    item.add_argument("--out", type=Path, required=True)
    return app


def main(argv=None):
    multiprocessing.freeze_support()
    app = parser()
    args = app.parse_args(argv)
    try:
        if args.operation == "orbitlab-diagnose":
            count = orbitlab_diagnose(args.replay, args.out, args.every)
            print(f"Recorded {count} OrbitLab snapshot rows in {args.out}")
            return 0
        if args.operation == "package-agent":
            packaging(args.agent, args.out)
            return 0
        if args.operation == "beast-guided":
            rows = guided(args.replays, args.base, load(args.config), args.out, args.population,
                          args.seed, args.candidate_index, args.evaluate_all, args.charts, read_registry(args.registry))
        else:
            registry = read_registry(args.registry)
            if args.operation == "intelligent-v6":
                rows = evolve(args.agents, registry, args.out, args.seed, args.generations,
                              args.variants, args.best_of, args.workers, args.max_games, args.steps)
            else:
                rows = orbitlab_tournament(args.agents, registry, args.out, args.seed, args.repeats,
                                           args.modes, args.workers, args.max_games, args.steps)
    except (OSError, ValueError, SyntaxError, KeyError, TypeError) as exc:
        app.exit(2, f"orbit-history: {exc}\n")
    print(f"Recorded {len(rows)} attempted matches in {args.out}")
    return int(any(row["status"] != "OK" for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
