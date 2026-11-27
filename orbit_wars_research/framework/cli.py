"""Installable command-line interface for local research."""

import argparse
import csv
import json
from pathlib import Path

from .agents import candidate_id, generate, read_registry, register
from .experiments import STAGES, evaluate, search, tournament, write_experiment
from .ranking import predict, train
from .replays import export_features


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, allow_nan=False)
        handle.write("\n")


def candidate(args):
    return load(args.spec) if args.spec is not None else args.agent


def parser():
    app = argparse.ArgumentParser(description="Orbit Wars Phase 3 local research")
    commands = app.add_subparsers(dest="operation", required=True)

    def command(name, help):
        return commands.add_parser(name, help=help)

    def with_candidate(cmd):
        group = cmd.add_mutually_exclusive_group(required=True)
        group.add_argument("--agent")
        group.add_argument("--spec", type=Path)

    item = command("import-agent", "register a trusted local Python file without copying its source")
    item.add_argument("source", type=Path)
    item.add_argument("--id", required=True)
    item.add_argument("--registry", required=True, type=Path)

    item = command("generate", "generate deterministic data-only variant specifications")
    with_candidate(item)
    item.add_argument("--seed", type=int, default=42)
    item.add_argument("--count", type=int, default=2)
    item.add_argument("--out", type=Path, required=True)

    item = command("hybridize", "compose separate agent policies for 2P and 4P")
    item.add_argument("--two", required=True)
    item.add_argument("--four", required=True)
    item.add_argument("--out", type=Path, required=True)

    for name in ("tournament", "validate", "search"):
        item = command(name, f"run a bounded {name} experiment")
        item.add_argument("--config", type=Path, required=True)
        item.add_argument("--registry", type=Path)
        item.add_argument("--out", type=Path, required=True)
        if name != "tournament":
            with_candidate(item)
        if name == "validate":
            item.add_argument("--stage", choices=("all",) + STAGES, default="all")
            item.add_argument("--evaluate-all", action="store_true", help="run later stages even after rejection")

    item = command("extract-replays", "extract V14 features from explicitly supplied local JSON replays")
    item.add_argument("files", type=Path, nargs="+")
    item.add_argument("--out", type=Path, required=True)
    item = command("train-ranker", "train a grouped linear ranker on feature CSV data")
    item.add_argument("features", type=Path)
    item.add_argument("--out", type=Path, required=True)
    item.add_argument("--seed", type=int, default=42)
    item.add_argument("--epochs", type=int, default=30)
    item.add_argument("--validation-fraction", type=float, default=0.25)
    item = command("predict", "score feature rows with a Phase 3 JSON ranker")
    item.add_argument("model", type=Path)
    item.add_argument("features", type=Path)
    item.add_argument("--out", type=Path, required=True)

    item = command("plot-history", "regenerate the Phase 2 figure from repository result tables")
    item.add_argument("--root", type=Path, default=Path.cwd(), help="repository or copy of its data and docs")
    return app


def main(argv=None):
    app = parser()
    args = app.parse_args(argv)
    try:
        if args.operation == "import-agent":
            register(args.registry, args.id, args.source)
        elif args.operation == "generate":
            variants = generate(candidate(args), args.seed, args.count)
            args.out.mkdir(parents=True, exist_ok=False)
            for variant in variants:
                write_json(args.out / f"{candidate_id(variant)}.json", variant)
        elif args.operation == "hybridize":
            write_json(args.out, {"kind": "router", "two": args.two, "four": args.four})
        elif args.operation in ("tournament", "validate", "search"):
            if args.out.exists():
                raise ValueError("Experiment output already exists")
            config = load(args.config)
            registry = read_registry(args.registry)
            if args.operation == "tournament":
                result = tournament(config, registry)
            else:
                config = {**config, "candidate": candidate(args)}
                if args.operation == "search":
                    result = search(config, config["candidate"], registry)
                else:
                    stages = STAGES if args.stage == "all" else (args.stage,)
                    config.update(selected_stages=stages, gated=not args.evaluate_all)
                    result = evaluate(config, config["candidate"], registry, stages, gated=config["gated"])
            write_experiment(args.out, args.operation, config, result, registry)
            print(f"Recorded {len(result['matches'])} attempted matches in {args.out}")
            if any(row["status"] != "OK" for row in result["matches"]):
                return 1
        elif args.operation == "extract-replays":
            count = export_features(args.files, args.out)
            print(f"Wrote {count} feature rows")
        elif args.operation == "train-ranker":
            write_json(args.out, train(args.features, args.seed, args.epochs, args.validation_fraction))
        elif args.operation == "predict":
            scores = predict(args.model, args.features)
            with args.out.open("x", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["row", "score"])
                writer.writerows(enumerate(scores))
        else:
            from .. import plot_results
            old_root = plot_results.ROOT
            try:
                plot_results.ROOT = args.root.resolve()
                plot_results.main()
            finally:
                plot_results.ROOT = old_root
    except (OSError, ValueError, KeyError, TypeError) as error:
        app.exit(2, f"orbit-research: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

