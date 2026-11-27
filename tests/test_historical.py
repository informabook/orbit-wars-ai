import hashlib
import json
import random
import tarfile
from pathlib import Path

import pytest

from orbit_wars_research.framework.matches import Match
from orbit_wars_research.historical import beast_v18, checkpoint, workflows
from orbit_wars_research.historical.policies import bind_candidate

CONFIGS = Path(__file__).resolve().parents[1] / "configs"


def test_beast_replay_guides_population_and_preserves_parent(monkeypatch, tmp_path):
    def evaluate(config, identifier, registry, stages, gated):
        assert identifier == "guided-candidate"
        assert config["opponents"] == ["guided-base"]
        assert registry["guided-base"]["sha256"] != registry[identifier]["sha256"]
        assert not gated and stages == ("fast", "anti-mirage", "full", "holdout")
        return {"matches": [], "stages": []}

    monkeypatch.setattr(workflows, "evaluate", evaluate)
    replay = CONFIGS / "beast_replay_fixture.json"
    config = json.loads((CONFIGS / "beast_validation_fixture.json").read_text(encoding="utf-8"))
    out = tmp_path / "guidance"
    workflows.guided([replay, replay], CONFIGS / "beast_fixture_agent.py",
                     config, out, 4, 42, 0, True)
    profile = json.loads((out / "tables/failure_guidance_plan.json").read_text(encoding="utf-8"))
    assert profile["counts"]["expansion_stall_big_neutrals"] == 1
    assert profile["counts"]["passive_low_actions"] == 1
    assert not (profile["counts"].keys() & {"analysis_error"})
    raw = (out / "tables/replay_statistics.csv").read_text(encoding="utf-8")
    assert raw.count("replay-0001") == 1
    assert "replay-0002" not in raw
    population = json.loads((out / "population.json").read_text(encoding="utf-8"))
    assert len(population) == 5
    assert population[-1]["parent"] == population[0]["name"]
    deterministic = [item.name for item in beast_v18.build_guided_population(profile, random.Random(42), 4, 0)]
    assert deterministic == [row["name"] for row in population[:4]]


def fake_match(task, registry, candidates):
    assert not registry
    return {"match_id": task.match_id, "agents": list(task.agents), "seed": task.seed,
            "episode_steps": task.episode_steps, "candidate_slot": task.candidate_slot,
            "mode": f"{len(task.agents)}P", "status": "OK", "applied_seed": task.seed,
            "terminal_statuses": ["DONE"] * len(task.agents),
            "rewards": [1.0] + [-1.0] * (len(task.agents) - 1)}


def test_orbitlab_resumes_same_plan_and_rejects_changed_seed(monkeypatch, tmp_path):
    monkeypatch.setattr(checkpoint, "run_one", fake_match)
    options = (["hold", "nearest"], {}, tmp_path, 42, 1, ["2p"], 1, 16, 24)
    rows = workflows.orbitlab_tournament(*options)
    assert {tuple(row["agents"]) for row in rows} == {("hold", "nearest"), ("nearest", "hold")}
    summary = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert all(row["completed"] == 2 and row["mean_reward"] == 0 for row in summary["leaderboard"])

    def unexpected(*args):
        pytest.fail("Already-recorded match was rerun")

    monkeypatch.setattr(checkpoint, "run_one", unexpected)
    assert workflows.orbitlab_tournament(*options) == rows
    with pytest.raises(ValueError, match="settings changed"):
        workflows.orbitlab_tournament(*options[:3], 43, *options[4:])


def test_checkpoint_rejects_invalid_terminal_record(monkeypatch, tmp_path):
    monkeypatch.setattr(checkpoint, "run_one", fake_match)
    task = Match("single", ("hold", "nearest"), 42, 24)
    checkpoint.execute([task], tmp_path, {}, {})
    path, = tmp_path.glob("*.json")
    record = json.loads(path.read_text(encoding="utf-8"))
    record["applied_seed"] = 143
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid terminal evidence"):
        checkpoint.execute([task], tmp_path, {}, {})


def test_v6_builds_real_strategy_graph_and_bracket(monkeypatch, tmp_path):
    monkeypatch.setattr(checkpoint, "run_one", fake_match)
    attempts = workflows.evolve(["hold", "nearest"], {}, tmp_path, 42, 2, ["expand"], 1, 1, 16, 24)
    strategy = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert len(attempts) <= 12 and {row["phase"] for row in attempts} == {
        "step1_second8", "step2_second8", "final_originals_plus_top4"
    }
    graph = strategy["lineage"]
    assert len(graph) == 8
    combo_entries = {item["strategy"] for item in graph.values() if len(item["parents"]) == 2}
    assert combo_entries == {"combo_situation", "combo_vote_merge"}
    observation = {"step": 4, "player": 0, "planets": [[0, 0, 5, 5, 2, 20, 1],
                   [1, 1, 19, 5, 2, 12, 2]], "fleets": []}
    for name in graph:
        assert isinstance(bind_candidate(name, 2, {}, candidates=graph)(observation, {}), list)


def test_local_packaging_is_repeatable_and_does_not_execute(tmp_path):
    agent = tmp_path / "policy.py"
    agent.write_text("raise RuntimeError('must not execute')\n\ndef agent(obs):\n    return []\n", encoding="utf-8")
    first, second = tmp_path / "first.tar.gz", tmp_path / "second.tar.gz"
    workflows.packaging(agent, first)
    workflows.packaging(agent, second)
    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()
    with tarfile.open(first, "r:gz") as bundle:
        assert bundle.getnames() == ["main.py"]
        assert bundle.extractfile("main.py").read() == agent.read_bytes()
    with pytest.raises(FileExistsError):
        workflows.packaging(agent, first)



def test_orbitlab_extracts_local_snapshots(tmp_path):
    out = tmp_path / "diagnostics"
    count = workflows.orbitlab_diagnose(CONFIGS / "beast_replay_fixture.json", out, 20)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["snapshot_rows"] == count > 0
    assert "seat-0" in (out / "snapshots.csv").read_text(encoding="utf-8")
