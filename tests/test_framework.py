import csv
import json
from pathlib import Path

import numpy as np
import pytest

from orbit_wars_research.framework import agents, experiments, matches, ranking, replays
from orbit_wars_research.framework.cli import main
from orbit_wars_research.ranker_v14 import FEATURES

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("status", ["TIMEOUT", "INVALID", "ERROR", "INACTIVE", None])
def test_terminal_status_rejected_even_with_valid_looking_rewards(status):
    states = [{"status": status, "reward": 1}, {"status": "DONE", "reward": -1}]
    assert matches.terminal(states, 2) == ([status, "DONE"], None, "invalid_terminal_status")


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), True, "1", 0])
def test_bad_terminal_rewards(value):
    states = [{"status": "DONE", "reward": value}, {"status": "DONE", "reward": -1}]
    assert matches.terminal(states, 2)[2] == "invalid_reward"


def test_missing_seed_rejected_before_agent_call():
    calls = []

    class Fake:
        info = {}
        def reset(self, players):
            calls.append(players)

    def make(**kwargs):
        calls.append(kwargs["configuration"]["seed"])
        return Fake()

    row = matches.run_match(matches.Match("missing", ("hold", "hold"), 23, 12), {}, make)
    assert row["reason"] == "seed_not_applied" and row["applied_seed"] is None
    assert calls == [23, 2]


def test_no_unseeded_retry_on_engine_type_error():
    calls = []

    def make(**kwargs):
        calls.append(kwargs)
        raise TypeError("old engine")

    assert matches.run_match(matches.Match("old", ("hold", "hold"), 1, 12), {}, make)["status"] == "ERROR"
    assert len(calls) == 1 and calls[0]["configuration"]["seed"] == 1


def test_staged_seed_sets_do_not_overlap():
    cfg = json.loads((ROOT / "configs/quickstart.json").read_text(encoding="utf-8"))
    plan = experiments.evaluation_plan(cfg, "nearest", experiments.STAGES)
    seeds = [match.seed for stage in plan.values() for _, match in stage]
    assert len(seeds) == len(set(seeds)) == 10
    cfg["stages"]["full"]["seed"] = cfg["stages"]["fast"]["seed"]
    with pytest.raises(ValueError, match="Seed reused"):
        experiments.evaluation_plan(cfg, "nearest", ("fast",))


def test_bad_stage_skips_later_stages_and_keeps_attempts():
    cfg = json.loads((ROOT / "configs/quickstart.json").read_text(encoding="utf-8"))

    def runner(match, _):
        return {"match_id": match.match_id, "mode": f"{len(match.agents)}P", "status": "OK",
                "seed": match.seed, "applied_seed": match.seed, "candidate_slot": match.candidate_slot,
                "terminal_statuses": ["TIMEOUT"] + ["DONE"] * (len(match.agents) - 1),
                "rewards": [1] + [-1] * (len(match.agents) - 1)}

    result = experiments.evaluate(cfg, "nearest", {}, runner=runner)
    assert [row["decision"] for row in result["stages"]] == ["REJECT", "SKIPPED", "SKIPPED", "SKIPPED"]
    assert result["stages"][0]["reason"] == "match_failed"
    assert len(result["matches"]) == 2


def test_variant_identity_reproducible_and_clamps_cumulative_ships():
    assert agents.generate("nearest", 22, 4) == agents.generate("nearest", 22, 4)
    assert len({agents.candidate_id(v) for v in agents.generate("nearest", 22, 4)}) == 4
    observation = {"player": 0, "planets": [[4, 0, 0, 0, 0, 12, 1], [3, 1, 1, 0, 0, 11, 1]]}
    spec = {"kind": "mutation", "parent": "nearest", "ship_scale": 2, "angle_shift": 0.25}
    assert agents.bind(spec, 2, {})(observation, None) == [[4, pytest.approx(0.25), 12]]
    router = {"kind": "router", "two": "hold", "four": "nearest"}
    assert agents.bind(router, 2, {})(observation, None) == []
    assert agents.bind(router, 4, {})(observation, None)[0][0] == 4


def test_local_import_does_not_execute_or_copy_at_registration(tmp_path):
    source = tmp_path / "agent.py"
    registry = tmp_path / "registry.json"
    source.write_text("raise AssertionError('must not run during registration')\n", encoding="utf-8")
    agents.register(registry, "local", source)
    entry = agents.read_registry(registry)
    assert set(tmp_path.iterdir()) == {source, registry}
    source.write_text("def agent(obs): return []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="source changed"):
        agents.bind("local", 2, entry)
    agents.register(registry, "test-agent", source)
    assert agents.bind("test-agent", 2, agents.read_registry(registry))({}, {}) == []


def test_auc_counts_ties_and_is_invariant_to_row_order():
    labels, scores = [0, 1, 0, 1], [0.1, 0.3, 0.3, 0.6]
    assert ranking.auc(labels, scores) == 0.875
    assert ranking.auc(labels[::-1], scores[::-1]) == 0.875
    assert ranking.auc([0, 1], [0.5, 0.5]) == 0.5
    with pytest.raises(ValueError):
        ranking.auc([1, 1], [0.1, 0.2])


def test_group_split_is_disjoint_deterministic_and_contains_both_classes():
    groups = np.repeat(["g0", "g1", "g2", "g3"], 4)
    labels = np.tile([0, 1], 8)
    train, validation = ranking.grouped_split(groups, labels, 7)
    assert not (set(groups[train]) & set(groups[validation]))
    assert set(labels[train]) == set(labels[validation]) == {0, 1}
    assert (validation == ranking.grouped_split(groups, labels, 7)[1]).all()


def test_ranker_cli_training_and_inference(tmp_path):
    model, scored = tmp_path / "model.json", tmp_path / "scores.csv"
    data = ROOT / "configs/ranker_fixture.csv"
    assert main(["train-ranker", str(data), "--epochs", "3", "--out", str(model)]) == 0
    assert main(["predict", str(model), str(data), "--out", str(scored)]) == 0
    doc = json.loads(model.read_text(encoding="utf-8"))
    assert doc["run"]["train_replays"] == 3 and doc["run"]["validation_replays"] == 1
    with scored.open(newline="") as handle:
        values = [float(row["score"]) for row in csv.DictReader(handle)]
    assert len(values) == 8 and all(values[i] < values[i+1] for i in range(0, 8, 2))


def test_historical_replay_features_are_grouped_by_playable_content(tmp_path):
    planets = [[0, 0, 5, 5, 2, 47, 2], [1, 1, 20, 5, 2, 10, 2], [2, -1, 12, 13, 2, 9, 3]]
    observation = {"player": 0, "planets": planets, "initial_planets": planets, "fleets": []}
    initial = [{"observation": observation}, {"observation": {"player": 1}}]
    ending = [{"action": [[0, 0, 22]], "status": "DONE", "reward": 1},
              {"status": "DONE", "reward": -1}]
    data = {"name": "orbit_wars", "steps": [initial, ending], "rewards": [1, -1]}
    files = [tmp_path / n for n in ("one.json", "duplicate.json")]
    for i, path in enumerate(files):
        path.write_text(json.dumps({**data, "id": i}), encoding="utf-8")
    output = tmp_path / "features.csv"
    assert replays.export_features(files, output) == 2
    with output.open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames[3:] == FEATURES
        rows = list(reader)
    assert len({row["replay_id"] for row in rows}) == 1
    assert {float(row["label"]) for row in rows} == {0.0, 1.0}
    ending[0]["status"] = "TIMEOUT"
    files[0].write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="terminal"):
        replays.load_replay(files[0])


@pytest.mark.simulator
def test_real_game_modes_and_seed_invariants():
    pytest.importorskip("kaggle_environments", reason="install the simulator extra")
    configs = [matches.Match("two", ("hold", "nearest"), 103, 16),
               matches.Match("four", ("hold", "nearest", "hold", "nearest"), 104, 16)]
    for task in configs:
        outcome = matches.run_match(task)
        assert outcome["status"] == "OK", outcome
        assert outcome["applied_seed"] == task.seed
        assert outcome["terminal_statuses"] == ["DONE"] * len(task.agents)
        assert 1 <= outcome["turns"] < task.episode_steps
        assert matches.run_match(task)["rewards"] == outcome["rewards"]

    def planets(seed):
        env = matches.make_game(configuration={"seed": seed, "episodeSteps": 16})
        env.reset(4)
        rows = env.steps[0][0]["observation"]["planets"]
        assert {p[1] for p in rows if p[1] >= 0} == {0, 1, 2, 3}
        assert all(0 < p[2] < 100 and 0 < p[3] < 100 and p[5] >= 0 for p in rows)
        return rows

    assert planets(14) == planets(14)
    assert planets(14) != planets(15)

