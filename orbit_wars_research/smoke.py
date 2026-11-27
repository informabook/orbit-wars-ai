"""Bounded Phase 2 smoke run using controlled, generated-in-place fixtures."""

import argparse
import ast
import json
import os
import random
import tempfile
from collections import Counter
from importlib.metadata import version
from pathlib import Path

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("MPLBACKEND", "Agg")

from . import beast, evolution, orbitlab, ranker_v14

# Known local test fixtures. Neither file is a historical agent.
PASSIVE = "def agent(obs, configuration=None):\n    return []\n"
LAUNCH = """
def agent(obs, configuration=None):
    if obs.get("step", 0) % 20:
        return []
    for p in obs.get("planets", []):
        if p[1] == obs.get("player") and p[5] >= 5:
            return [[p[0], 0.25, 2]]
    return []
"""
ROOT = Path(__file__).resolve().parents[1]


def emit(check, **facts):
    print(json.dumps({"check": check, **facts}, sort_keys=True), flush=True)


def fixtures(root):
    for name, code in (("passive", PASSIVE), ("launch", LAUNCH)):
        path = root / name
        path.mkdir()
        (path / "main.py").write_text(code, encoding="utf-8")
    return root / "passive", root / "launch"


def terminal(env, player_count):
    statuses = [state.status for state in env.steps[-1]]
    assert statuses == ["DONE"] * player_count, statuses
    return statuses


def simulator(make):
    for count in (2, 4):
        env = make("orbit_wars", configuration={"seed": 42, "episodeSteps": 32})
        assert env.name == "orbit_wars"
        env.run(["random"] * count)
        statuses = terminal(env, count)
        assert len(env.steps) > 1
        emit("simulator", players=count, seed=42, steps=len(env.steps), statuses=statuses)


def tournament(root, passive, launch):
    agents = [{"agent": p.name, "path": str(p / "main.py")} for p in (passive, launch)]
    args = argparse.Namespace(seed=77, snapshot_step=25, modes=["2p"],
                              repeats_2p=1, swap_positions=True)
    tasks = orbitlab.construire_taches(agents, args)
    assert len(tasks) == 2 and {tuple(t["agents"]) for t in tasks} == {
        ("passive", "launch"), ("launch", "passive")
    }
    results = []
    for task in tasks:
        output = root / (task["match_id"] + ".json")
        orbitlab.worker_match(task, str(output))
        result = json.loads(output.read_text(encoding="utf-8"))
        assert result["status"] == "OK", result["error"]
        assert result["agent_statuses"] == ["DONE", "DONE"], result["agent_statuses"]
        assert result["snapshots"] and result["actions"]
        summary = orbitlab.resume_match_depuis_resultat(result)
        results.append({"order": task["agents"], "seed": task["seed"],
                        "reward": json.loads(summary["rewards_json"]),
                        "snapshots": len(result["snapshots"])})
    emit("orbitlab_tournament", matches=results)


def generation(root):
    rng = random.Random(17)
    parent = beast.random_spec(rng, 1, 0, "mixed")
    child = beast.mutate_spec(parent, rng, 2, 1)
    assert child.parent == parent.name and child.generation == 1
    assert beast.patch_global("horizon: int = 12", {"horizon": 14}) == "horizon: int = 14"
    setting = "CONFIG_4P = dataclasses.replace(\n    BASE,\n    horizon=12,\n)\n"
    assert "horizon=14," in beast.patch_config4p(setting, {"horizon": 14})
    gen = root / "generated"
    gen.mkdir()
    for mode in ("expand", "combo_situation", "combo_vote_merge"):
        if mode == "expand":
            evolution.write_intelligent_variant_main(gen, "fixture_a", mode, 1, "left", "fixture_a")
        else:
            evolution.write_combo_variant_main(gen, ["fixture_a", "fixture_b"], mode, 2,
                                               ["fixture_a", "fixture_b"])
        source = (gen / "main.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert any(isinstance(node, ast.FunctionDef) and node.name == "agent" for node in tree.body)
        compile(tree, f"{mode}.py", "exec")
    rows = [
        {"name": "duel", "full_mean2p": 0.2, "full_mean4p": -0.1,
         "global_params": '{"horizon": 14}'},
        {"name": "ffa", "full_mean2p": -0.1, "full_mean4p": 0.2,
         "fourp_params": '{"horizon": 18}'},
    ]
    duel = beast.choose_best_mode_row(rows, [], "2P")
    ffa = beast.choose_best_mode_row(rows, [], "4P")
    hybrid = beast.build_hybrid_spec(duel, ffa)
    assert hybrid.parent == "2P:duel|GT2:ffa"
    assert hybrid.global_params["horizon"] == 14 and hybrid.fourp_params["horizon"] == 18
    emit("generation", templates=3, generated_code_executed=False, parent=parent.name,
         child=child.name, context_selection=hybrid.parent)


def validation(passive, launch):
    ok, message = beast.import_smoke(passive, "controlled_fixture")
    assert ok, message
    assert beast.verify_submission_dir(passive) == (False, "orbit_lite absent")

    for stage, seed in (("fast", 90), ("full", 100), ("holdout", 110)):
        outcome = beast.eval_variant("orbit_wars", passive, launch, 1, 1, 1, seed, [])
        assert outcome["ok"] and outcome["errors"] == 0
        assert (outcome["n2p"], outcome["n4p"]) == (1, 1)
        passes_gate = getattr(beast, f"pass_{stage}")(outcome)
        assert type(passes_gate) is bool
        assert not getattr(beast, f"pass_{stage}")({**outcome, "ok": False})
        emit("validation_fixture", stage=stage, seed=seed, passed_gate=passes_gate,
             matches=outcome["n2p"]+outcome["n4p"], combined=outcome["combined"])

    outcome = beast.eval_variant_anti_mirage("orbit_wars", passive, launch, 6, 2, 1, 120, [])
    assert outcome["ok"] and outcome["errors"] == 0 and outcome["good_rounds"] == 2
    assert (outcome["n2p"], outcome["n4p"]) == (6, 6)
    emit("validation_fixture", stage="anti_mirage", seed=120, rounds=2, matches=12,
         passed_gate=beast.pass_anti_mirage(outcome))
    assert not beast.pass_anti_mirage(beast.aggregate_eval_rounds([]))


def ranker():
    import numpy as np

    rng = np.random.default_rng(7)
    features = rng.normal(size=(128, len(ranker_v14.FEATURES)))
    labels = (features[:, 0] > 0).astype(float)
    ranker_v14.MAX_EPOCHS = 2
    result = ranker_v14.entrainer_ranker_numpy_lineaire(features, labels, np.ones(len(labels)))
    assert len(result["weights"]) == len(ranker_v14.FEATURES)
    assert all(np.isfinite(result["weights"]))
    assert 0 <= result["metrics"]["best_val_auc"] <= 1
    emit("ranker_fixture", samples=len(labels), epoch_budget=2,
         features=len(ranker_v14.FEATURES), finite_weights=True)


def historical_tables():
    import csv
    def load(name):
        with (ROOT / "results" / name).open(encoding="utf-8", newline="") as data:
            return list(csv.DictReader(data))
    statuses = Counter(row["status"] for row in load("evolution_matches.csv"))
    assert statuses == {"OK": 231, "TIMEOUT": 8, "BAD_OUTPUT": 14}
    assert len(load("evolution_candidates.csv")) == 52
    assert len(load("beast_fast.csv")) == 16 and len(load("beast_full.csv")) == 4
    assert sum(int(row["games"]) for row in load("beast_replays_by_mode.csv")) == 312
    summary = json.loads((ROOT / "results/ranker_v14_summary.json").read_text(encoding="utf-8"))
    assert summary["n"] == 134051 and round(summary["best_val_auc"], 6) == 0.886154
    assert summary["export_coefficient"] == 0
    emit("historical_tables", cases=52, match_statuses=statuses, replays=312)


def main():
    from kaggle_environments import make

    emit("imports", environment=version("kaggle-environments"), numpy=version("numpy"))
    simulator(make)
    with tempfile.TemporaryDirectory(prefix="orbit-wars-smoke-") as tmp:
        root = Path(tmp)
        passive, launch = fixtures(root)
        tournament(root, passive, launch)
        generation(root)
        validation(passive, launch)
    ranker()
    historical_tables()
    emit("complete", fixture_games=22)


if __name__ == "__main__":
    main()
