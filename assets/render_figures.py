"""Render the release's original architecture and data-driven V14 plots."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

INK = "#12253a"
MUTED = "#43566b"
TEAL = "#176d75"
BLUE = "#324e85"
AMBER = "#94531c"
PAPER = "#f7f9fb"
ROOT = Path(__file__).resolve().parents[1]


def save(fig, path, formats, description):
    for suffix in formats:
        meta = {"Description": description}
        if suffix == "svg":
            meta["Date"] = None
        destination = path.with_suffix("." + suffix)
        fig.savefig(destination, dpi=160, metadata=meta, facecolor=PAPER)
        if suffix == "svg":
            lines = destination.read_text(encoding="utf-8").splitlines()
            destination.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8", newline="\n")
    plt.close(fig)


def architecture(output):
    fig = plt.figure(figsize=(15, 8.4), facecolor=PAPER)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, 1600), ylim=(0, 900))
    ax.axis("off")

    def label(x, y, value, *, size=12, color=INK, weight="normal", align="left"):
        ax.text(x, y, value, fontsize=size, color=color, weight=weight,
                ha=align, va="center", linespacing=1.25)

    def card(x, y, name, detail, *, width=245, edge=TEAL, face="#ffffff", dashed=False):
        ax.add_patch(FancyBboxPatch((x - width/2, y - 39), width, 78,
                                   boxstyle="round,pad=1,rounding_size=11",
                                   edgecolor=edge, facecolor=face, linewidth=1.35,
                                   linestyle="--" if dashed else "-"))
        label(x, y + 11, name, size=12.3, color=edge, weight="bold", align="center")
        label(x, y - 13, detail, size=9.7, color=MUTED, align="center")

    def arrow(start, end, color=TEAL, dashed=False):
        ax.add_patch(FancyArrowPatch(start, end, mutation_scale=13, arrowstyle="-|>",
                                    color=color, linewidth=1.45,
                                    linestyle="--" if dashed else "-", shrinkA=0, shrinkB=0))

    label(65, 838, "Orbit Wars research workflow", size=29, weight="bold")
    label(65, 790, "Historical experiment paths and the boundary of the release evidence", size=14, color=MUTED)
    label(65, 730, "STRATEGY SEARCH", size=10.5, weight="bold", color=TEAL)
    xs = (183, 491, 799, 1107, 1415)
    top_cards = (
        ("Baseline agents", "Public and historical policies"),
        ("Strategic heuristics", "Tune allocation and tactics"),
        ("Generate candidates", "Mutation and hybridization"),
        ("Contextual policies", "2P and 4P routing"),
        ("Local tournaments", "Compare seeded matches"),
    )
    for x, (name, detail) in zip(xs, top_cards):
        card(x, 662, name, detail)
    for a, b in zip(xs, xs[1:]):
        arrow((a + 126, 662), (b - 126, 662))

    label(65, 567, "REPLAY LEARNING", size=10.5, weight="bold", color=BLUE)
    replay_cards = (
        ("Recorded replays", "Selected competition episodes"),
        ("Feature extraction", "Parse state, moves and labels"),
        ("Action ranker", "Train and evaluate on events"),
        ("Experimental overlay", "Archived V14 export weight: 0"),
    )
    for x, (name, detail) in zip(xs, replay_cards):
        card(x, 500, name, detail, edge=BLUE, face="#f2f5fc")
    for a, b in zip(xs[:4], xs[1:4]):
        arrow((a + 126, 500), (b - 126, 500), BLUE)
    arrow((xs[3], 541), (xs[3], 617), BLUE, dashed=True)

    label(65, 413, "MULTI-STAGE VALIDATION", size=10.5, weight="bold", color=TEAL)
    stages = (
        ("Smoke", "Agent and simulator"),
        ("Fast", "Screen candidates"),
        ("Anti-Mirage", "Repeat across seeds"),
        ("Full", "Broader evaluation"),
        ("Holdout", "Historical score missing"),
        ("Selection", "Gate or fallback"),
    )
    stage_x = (171, 422, 673, 924, 1175, 1426)
    for i, (x, (name, detail)) in enumerate(zip(stage_x, stages)):
        card(x, 323, name, detail, width=216, edge=AMBER if i == 4 else TEAL,
             face="#fff7ec" if i == 4 else "#ffffff", dashed=i == 4)
    for a, b in zip(stage_x, stage_x[1:]):
        arrow((a + 112, 323), (b - 112, 323))
    ax.plot([xs[-1], xs[-1], stage_x[0]], [618, 390, 390], color=TEAL, linewidth=1.45)
    arrow((stage_x[0], 390), (stage_x[0], 366))

    ax.add_patch(FancyBboxPatch((65, 78), 1470, 124, boxstyle="round,pad=1,rounding_size=12",
                                linewidth=1.35, edgecolor="#8a9aac", facecolor="#eef3f8"))
    arrow((stage_x[-1], 281), (stage_x[-1], 208), color=MUTED, dashed=True)
    label(93, 166, "KAGGLE DEPLOYMENT AND EVIDENCE", size=10.5, color=MUTED, weight="bold")
    label(93, 132, "611 / 4,729 teams reported in V5", size=18, weight="bold")
    label(93, 98, "Submission name documented. Exact uploaded binary and feature lineage are unresolved.",
          size=10.8, color=MUTED)
    label(65, 36, "Conceptual diagram. Dashed paths indicate an experimental connection or an evidence gap.",
          size=10.8, color=MUTED)
    save(fig, output / "research-architecture", ("png", "svg"),
         "Conceptual Orbit Wars workflow, from baseline and replay inputs to validation and submission evidence.")


def ranker_curve(root, output):
    with (root / "results/phase3/v14_training_curve.csv").open(encoding="utf-8", newline="") as handle:
        results = list(csv.DictReader(handle))
    summary = json.loads((root / "results/ranker_v14_summary.json").read_text(encoding="utf-8"))
    epochs = [int(row["epoch"]) for row in results]
    fig, (auc, loss) = plt.subplots(1, 2, figsize=(12, 4.5), facecolor=PAPER)
    fig.subplots_adjust(left=0.085, right=0.965, wspace=0.32, top=0.73, bottom=0.23)
    fig.text(0.07, 0.91, "V14 ranker | archived training checkpoints", fontsize=21, color=INK, weight="bold")
    fig.text(0.07, 0.84, f"{len(results)} checkpoints · {summary['n']:,} historical examples", fontsize=12, color=MUTED)
    for ax, fields, ylabel in ((auc, ("train_auc", "val_auc"), "Approximate ROC AUC"),
                               (loss, ("train_loss", "val_loss"), "Recorded weighted loss")):
        ax.set_facecolor(PAPER)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set(xlabel="Epoch", ylabel=ylabel)
        ax.grid(axis="y", color="#dce4ee")
        ax.set_axisbelow(True)
        for field, color, name in zip(fields, (TEAL, AMBER), ("Training", "Validation")):
            ax.plot(epochs, [float(row[field]) for row in results], color=color, label=name, linewidth=1.8)
        ax.legend(frameon=False)
    fig.text(0.07, 0.065, "Historical example-level split. The exported action ranker coefficient was zero.",
             fontsize=10.5, color=MUTED)
    save(fig, output / "v14-training-curve", ("png",),
         "Historical V14 values read from v14_training_curve.csv without recomputing metrics.")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--root", type=Path, default=ROOT)
    cli.add_argument("--out", type=Path)
    args = cli.parse_args()
    output = args.out or (args.root / "assets")
    output.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"svg.fonttype": "none", "svg.hashsalt": "orbit-wars-v0.3.0"}):
        architecture(output)
        ranker_curve(args.root, output)


if __name__ == "__main__":
    main()
