"""Render the Phase 2 figure solely from bundled historical CSV values."""

import csv
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

ROOT = Path(__file__).resolve().parents[1]


def read_csv(name):
    with (ROOT / "results" / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    counts = Counter(row["status"] for row in read_csv("evolution_matches.csv"))
    full = read_csv("beast_full.csv")
    colors = ["#186a76", "#a16920", "#a14941"]

    fig, (left, right) = plt.subplots(1, 2, figsize=(10, 4.45))
    fig.set_facecolor("#f8f8f5")
    fig.subplots_adjust(left=0.12, right=0.96, top=0.72, bottom=0.22, wspace=0.55)
    fig.text(0.055, 0.925, "Orbit Wars  |  Historical evaluation", fontsize=20, weight="bold", color="#18232f")
    fig.text(0.055, 0.853, "Local tournament records and Full-stage candidate scores", fontsize=11, color="#465769")

    for ax in (left, right):
        ax.set_facecolor("#f8f8f5")
        ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
        ax.tick_params(length=0, pad=6, labelcolor="#465769")
        ax.grid(axis="x", color="#dfe4e7", linewidth=0.8)
        ax.set_axisbelow(True)

    statuses = ["OK", "TIMEOUT", "BAD_OUTPUT"]
    bars = left.barh(["Completed", "Timeout", "Bad output"], [counts[s] for s in statuses], color=colors, height=0.48)
    left.bar_label(bars, padding=4, fontsize=10, color="#18232f")
    left.set_xlim(0, 270)
    left.invert_yaxis()
    left.set_title("Evolution lab  |  253 matches", loc="left", fontsize=12, weight="bold", pad=14)
    left.set_xticks([0, 50, 100, 150, 200, 250])

    labels = ["Midgame lead", "Ship deficit", "Midgame child", "2P / 4P hybrid"]
    values = [float(row["full_combined"]) for row in full]
    bars = right.barh(labels, values, color="#a14941", height=0.48)
    right.bar_label(bars, labels=[f"{value:.3f}" for value in values], padding=4, fontsize=9, color="#18232f")
    right.set_xlim(-0.415, 0.015)
    right.set_xticks([-0.4, -0.3, -0.2, -0.1, 0])
    right.axvline(0, color="#6f7f8b", linewidth=0.8)
    right.invert_yaxis()
    right.set_title("Beast Lab  |  Full stage", loc="left", fontsize=12, weight="bold", pad=14)
    fig.text(0.055, 0.075, "Source: historical CSVs. Full scores are combined deltas. The run recorded zero validated exports.",
             fontsize=9, color="#465769")
    target = ROOT / "docs/figures/historical-results.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("Wrote docs/figures/historical-results.png")


if __name__ == "__main__":
    main()
