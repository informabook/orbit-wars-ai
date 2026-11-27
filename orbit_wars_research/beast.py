"""Reviewed excerpt from historical Python source. See PROVENANCE.md for source and scope."""

import dataclasses
import hashlib
import importlib.util
import json
import random
import re
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

FAST_GATE = 0.010

FULL_GATE = 0.010

HOLDOUT_GATE = 0.006

MODE_FLOOR = -0.015

CI_LOW_GATE = -0.005

ANTI_MIRAGE_GATE = 0.030

ANTI_MIRAGE_MIN_COMBINED = -0.050

ANTI_MIRAGE_MAX_STD = 0.420

def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default

def verify_submission_dir(root: Path) -> Tuple[bool, str]:
    if not (root / "main.py").exists():
        return False, "main.py absent"
    if not (root / "orbit_lite").is_dir():
        return False, "orbit_lite absent"
    for bad in ["brains", "results", "tmp", "build", "prepared_agents", "generated_stream_learning"]:
        if (root / bad).exists():
            return False, f"dossier parasite à la racine: {bad}"
    try:
        for p in root.glob("*.py"):
            compile(p.read_text(encoding="utf-8", errors="replace"), str(p), "exec")
    except Exception as e:
        return False, f"compile error: {e}"
    return True, "ok"

def import_smoke(root: Path, tag: str) -> Tuple[bool, str]:
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(root))
        name = "ow_" + re.sub(r"[^A-Za-z0-9_]", "_", tag)[:28] + "_" + hashlib.md5(str(root).encode()).hexdigest()[:8]
        spec = importlib.util.spec_from_file_location(name, str(root / "main.py"))
        if spec is None or spec.loader is None:
            return False, "cannot create import spec"
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        if not hasattr(mod, "agent"):
            return False, "main.py has no agent"
        return True, "ok"
    except Exception as e:
        return False, repr(e)
    finally:
        sys.path[:] = old_path

GLOBAL_TYPES = {
    "horizon": "int",
    "max_sources_per_lane": "int",
    "max_offensive_targets": "int",
    "max_defensive_targets": "int",
    "max_waves_per_turn": "int",
    "roi_threshold": "float",
    "min_ships_to_launch": "float",
    "reinforce_size_beta": "float",
}

GLOBAL_RANGES = {
    "horizon": [16, 18, 20, 22],
    "max_sources_per_lane": [8, 10, 12],
    "max_offensive_targets": [10, 12, 14],
    "max_defensive_targets": [3, 4, 5],
    "max_waves_per_turn": [5, 6, 7],
    "roi_threshold": [1.20, 1.35, 1.50, 1.65, 1.80],
    "min_ships_to_launch": [3.0, 4.0, 5.0],
    "reinforce_size_beta": [2.0, 2.2, 2.5, 2.8],
}

FOURP_RANGES = {
    "horizon": [11, 12, 13, 14, 15],
    "max_sources_per_lane": [5, 6, 7, 8],
    "max_offensive_targets": [8, 10, 12],
    "max_defensive_targets": [2, 3, 4],
    "max_waves_per_turn": [3, 4, 5],
    "roi_threshold": [1.35, 1.50, 1.75, 2.0],
    "min_ships_to_launch": [3.0, 4.0, 5.0],
    "max_regroup_time": [5.0, 6.0, 7.0],
}

@dataclasses.dataclass
class VariantSpec:
    name: str
    family: str
    generation: int
    parent: str
    global_params: Dict[str, Any]
    fourp_params: Dict[str, Any]

def random_spec(rng: random.Random, idx: int, generation: int, family: str) -> VariantSpec:
    gp: Dict[str, Any] = {}
    fp: Dict[str, Any] = {}

    if family in ("global", "mixed"):
        for k, vals in GLOBAL_RANGES.items():
            if rng.random() < 0.40:
                gp[k] = rng.choice(vals)

    if family in ("fourp", "mixed"):
        for k, vals in FOURP_RANGES.items():
            if rng.random() < 0.48:
                fp[k] = rng.choice(vals)

    if not gp and not fp:
        fp["horizon"] = rng.choice(FOURP_RANGES["horizon"])

    sig = hashlib.md5(json.dumps([gp, fp], sort_keys=True).encode()).hexdigest()[:8]
    return VariantSpec(f"g{generation:02d}_{family}_{idx:04d}_{sig}", family, generation, "", gp, fp)

def mutate_spec(parent: VariantSpec, rng: random.Random, idx: int, generation: int) -> VariantSpec:
    gp = dict(parent.global_params)
    fp = dict(parent.fourp_params)

    if rng.random() < 0.55:
        k = rng.choice(list(GLOBAL_RANGES))
        gp[k] = rng.choice(GLOBAL_RANGES[k])
    if rng.random() < 0.75:
        k = rng.choice(list(FOURP_RANGES))
        fp[k] = rng.choice(FOURP_RANGES[k])
    if rng.random() < 0.15 and gp:
        gp.pop(rng.choice(list(gp)), None)
    if rng.random() < 0.15 and fp:
        fp.pop(rng.choice(list(fp)), None)

    sig = hashlib.md5(json.dumps([gp, fp], sort_keys=True).encode()).hexdigest()[:8]
    return VariantSpec(f"g{generation:02d}_child_{idx:04d}_{sig}", "child", generation, parent.name, gp, fp)

def patch_global(text: str, params: Dict[str, Any]) -> str:
    """
    Patch souple des paramètres typés.
    Ancienne version : cherchait exactement `horizon: int = 20` dans trois fichiers fixes.
    V18 : accepte espaces variables, ints/floats signés, et remplace toutes les occurrences pertinentes.
    """
    for key, val in params.items():
        typ = GLOBAL_TYPES.get(key)
        if not typ:
            continue
        pattern = rf"({re.escape(key)}\s*:\s*{re.escape(typ)}\s*=\s*)[-+]?[0-9]+(?:\.[0-9]+)?"
        text = re.sub(pattern, rf"\g<1>{val}", text)
    return text

def patch_config4p(text: str, params: Dict[str, Any]) -> str:
    if not params:
        return text
    marker = "CONFIG_4P = dataclasses.replace("
    start = text.find(marker)
    if start < 0:
        return text
    end = text.find(")\n", start)
    if end < 0:
        end = text.find(")", start)
    if end < 0:
        return text
    block = text[start:end+2]
    new = block
    for key, val in params.items():
        line_re = rf"(\n\s*){re.escape(key)}\s*=\s*[^,\n]+,"
        if re.search(line_re, new):
            new = re.sub(line_re, rf"\g<1>{key}={val},", new)
        else:
            close = new.rfind("\n)")
            if close >= 0:
                new = new[:close] + f"    {key}={val},\n" + new[close:]
    return text[:start] + new + text[end+2:]

def run_match_worker(env_name: str, agent_dirs: List[str], seed: int) -> Dict[str, Any]:
    try:
        from kaggle_environments import make
        agent_files = [str(Path(d) / "main.py") for d in agent_dirs]
        try:
            env = make(env_name, configuration={"seed": int(seed)}, debug=False)
        except TypeError:
            env = make(env_name, debug=False)
        env.run(agent_files)
        last = env.steps[-1]
        rewards = [float(x.get("reward", 0.0) or 0.0) for x in last]
        statuses = [str(x.get("status", "")) for x in last]
        return {"ok": True, "rewards": rewards, "statuses": statuses}
    except Exception as e:
        return {"ok": False, "error": repr(e)}

def build_tasks(base: Path, var: Path, games2: int, games4: int, seed: int, opponents: List[Path]) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    tasks = []

    for i in range(games2):
        opp = rng.choice(opponents) if opponents else base
        if i % 2 == 0:
            dirs = [var, opp]
            slot = 0
        else:
            dirs = [opp, var]
            slot = 1
        tasks.append({"mode": "2P", "slot": slot, "dirs": [str(x) for x in dirs], "seed": seed + i})

    for i in range(games4):
        pool = [rng.choice(opponents) if opponents else base for _ in range(3)]
        slot = i % 4
        dirs = []
        k = 0
        for j in range(4):
            if j == slot:
                dirs.append(var)
            else:
                dirs.append(pool[k])
                k += 1
        tasks.append({"mode": "4P", "slot": slot, "dirs": [str(x) for x in dirs], "seed": seed + 100000 + i})

    return tasks

def delta_from_rewards(rewards: List[float], slot: int) -> Optional[float]:
    if not isinstance(rewards, list) or slot >= len(rewards):
        return None
    cand = float(rewards[slot])
    others = [float(x) for i, x in enumerate(rewards) if i != slot]
    if not others:
        return None
    return cand - statistics.mean(others)

def bootstrap_ci(xs: List[float], boots: int = 400) -> Tuple[float, float]:
    xs = [float(x) for x in xs]
    if not xs:
        return -999.0, -999.0
    if len(xs) == 1:
        return xs[0], xs[0]
    rng = random.Random(1234 + len(xs))
    vals = []
    for _ in range(boots):
        sample = [xs[rng.randrange(len(xs))] for _ in xs]
        vals.append(statistics.mean(sample))
    vals.sort()
    return vals[int(0.05 * (len(vals)-1))], vals[int(0.95 * (len(vals)-1))]

def eval_variant(env_name: str, base: Path, var: Path, games2: int, games4: int, workers: int, seed: int, opponents: List[Path]) -> Dict[str, Any]:
    tasks = build_tasks(base, var, games2, games4, seed, opponents)
    rows = []

    if workers <= 1:
        for t in tasks:
            res = run_match_worker(env_name, t["dirs"], t["seed"])
            row = dict(t)
            row.update(res)
            rows.append(row)
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(run_match_worker, env_name, t["dirs"], t["seed"]): t for t in tasks}
            for fut in as_completed(futs):
                t = futs[fut]
                try:
                    res = fut.result()
                except Exception as e:
                    res = {"ok": False, "error": repr(e)}
                row = dict(t)
                row.update(res)
                rows.append(row)

    d2, d4 = [], []
    errors = 0
    for r in rows:
        if not r.get("ok"):
            errors += 1
            continue
        d = delta_from_rewards(r.get("rewards", []), r["slot"])
        if d is None:
            errors += 1
            continue
        if r["mode"] == "2P":
            d2.append(d)
        else:
            d4.append(d)

    def mean(xs: List[float]) -> float:
        return statistics.mean(xs) if xs else -999.0

    ci2 = bootstrap_ci(d2)
    ci4 = bootstrap_ci(d4)
    ciall = bootstrap_ci(d2 + d4)
    combined = 0.45 * mean(d2) + 0.55 * mean(d4)
    return {
        "ok": bool(d2 and d4),
        "errors": errors,
        "n2p": len(d2),
        "n4p": len(d4),
        "mean2p": mean(d2),
        "mean4p": mean(d4),
        "combined": combined,
        "ci2_low": ci2[0],
        "ci2_high": ci2[1],
        "ci4_low": ci4[0],
        "ci4_high": ci4[1],
        "ci_all_low": ciall[0],
        "ci_all_high": ciall[1],
    }

def aggregate_eval_rounds(rounds: List[Dict[str, Any]]) -> Dict[str, Any]:
    good = [r for r in rounds if r.get("ok")]
    if not good:
        return {
            "ok": False,
            "rounds": len(rounds),
            "good_rounds": 0,
            "combined": -999.0,
            "mean2p": -999.0,
            "mean4p": -999.0,
            "min_combined": -999.0,
            "std_combined": 999.0,
            "ci_all_low": -999.0,
        }

    combs = [safe_float(r.get("combined"), -999.0) for r in good]
    m2 = [safe_float(r.get("mean2p"), -999.0) for r in good]
    m4 = [safe_float(r.get("mean4p"), -999.0) for r in good]
    lows = [safe_float(r.get("ci_all_low"), -999.0) for r in good]

    return {
        "ok": len(good) == len(rounds),
        "rounds": len(rounds),
        "good_rounds": len(good),
        "n2p": sum(int(r.get("n2p", 0) or 0) for r in good),
        "n4p": sum(int(r.get("n4p", 0) or 0) for r in good),
        "errors": sum(int(r.get("errors", 0) or 0) for r in rounds),
        "mean2p": statistics.mean(m2) if m2 else -999.0,
        "mean4p": statistics.mean(m4) if m4 else -999.0,
        "combined": statistics.mean(combs) if combs else -999.0,
        "min_combined": min(combs) if combs else -999.0,
        "max_combined": max(combs) if combs else -999.0,
        "std_combined": statistics.pstdev(combs) if len(combs) > 1 else 0.0,
        "ci_all_low": min(lows) if lows else -999.0,
    }

def eval_variant_anti_mirage(
    env_name: str,
    base: Path,
    var: Path,
    games_per_round: int,
    rounds: int,
    workers: int,
    seed: int,
    opponents: List[Path],
) -> Dict[str, Any]:
    evals = []
    for r in range(max(1, rounds)):
        ev = eval_variant(
            env_name,
            base,
            var,
            games2=max(3, games_per_round // 2),
            games4=max(3, games_per_round // 2),
            workers=workers,
            seed=seed + r * 1000003,
            opponents=opponents,
        )
        evals.append(ev)
    out = aggregate_eval_rounds(evals)
    out["round_details"] = json.dumps([
        {
            "combined": e.get("combined"),
            "mean2p": e.get("mean2p"),
            "mean4p": e.get("mean4p"),
            "ok": e.get("ok"),
            "n2p": e.get("n2p"),
            "n4p": e.get("n4p"),
        }
        for e in evals
    ], sort_keys=True)
    return out

def pass_anti_mirage(ev: Dict[str, Any]) -> bool:
    return (
        bool(ev.get("ok"))
        and safe_float(ev.get("combined"), -999.0) >= ANTI_MIRAGE_GATE
        and safe_float(ev.get("min_combined"), -999.0) >= ANTI_MIRAGE_MIN_COMBINED
        and safe_float(ev.get("mean2p"), -999.0) >= MODE_FLOOR
        and safe_float(ev.get("mean4p"), -999.0) >= MODE_FLOOR
        and safe_float(ev.get("std_combined"), 999.0) <= ANTI_MIRAGE_MAX_STD
    )

def pass_fast(ev: Dict[str, Any]) -> bool:
    return bool(ev.get("ok")) and ev["combined"] >= FAST_GATE and ev["mean2p"] >= MODE_FLOOR and ev["mean4p"] >= MODE_FLOOR

def pass_full(ev: Dict[str, Any]) -> bool:
    return bool(ev.get("ok")) and ev["combined"] >= FULL_GATE and ev["mean2p"] >= MODE_FLOOR and ev["mean4p"] >= MODE_FLOOR and ev["ci_all_low"] >= CI_LOW_GATE

def pass_holdout(ev: Dict[str, Any]) -> bool:
    return bool(ev.get("ok")) and ev["combined"] >= HOLDOUT_GATE and ev["mean2p"] >= MODE_FLOOR and ev["mean4p"] >= MODE_FLOOR and ev["ci_all_low"] >= CI_LOW_GATE

def parse_json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    try:
        obj = json.loads(str(value or "{}"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}

def row_metric(row: Dict[str, Any], metric_names: List[str], default: float = -999.0) -> float:
    for name in metric_names:
        if name in row and row.get(name) not in [None, ""]:
            return safe_float(row.get(name), default)
    return default

def choose_best_mode_row(full_rows: List[Dict[str, Any]], fast_rows: List[Dict[str, Any]], mode: str) -> Optional[Dict[str, Any]]:
    """
    Choisit le meilleur candidat pour 2P ou 4P.
    Priorité holdout > full > fast.
    """
    rows: List[Dict[str, Any]] = []

    for r in full_rows:
        if mode == "2P":
            score = row_metric(r, ["holdout_mean2p", "full_mean2p", "fast_mean2p"])
        else:
            score = row_metric(r, ["holdout_mean4p", "full_mean4p", "fast_mean4p"])
        rr = dict(r)
        rr["_mode_score"] = score
        rr["_source_stage"] = "full_holdout"
        rows.append(rr)

    if not rows:
        for r in fast_rows:
            if not r.get("build_ok"):
                continue
            if mode == "2P":
                score = row_metric(r, ["fast_mean2p"])
            else:
                score = row_metric(r, ["fast_mean4p"])
            rr = dict(r)
            rr["_mode_score"] = score
            rr["_source_stage"] = "fast"
            rows.append(rr)

    rows = [r for r in rows if safe_float(r.get("_mode_score"), -999.0) > -998.0]
    if not rows:
        return None

    rows.sort(key=lambda r: (
        safe_float(r.get("_mode_score"), -999.0),
        safe_float(r.get("holdout_combined"), safe_float(r.get("full_combined"), safe_float(r.get("fast_combined"), -999.0))),
    ), reverse=True)
    return rows[0]

def build_hybrid_spec(best2: Dict[str, Any], best4: Dict[str, Any], generation: int = 99) -> VariantSpec:
    """
    Le routeur logique est :
    - == 2 joueurs : global_params issus du meilleur 2P
    - > 2 joueurs : CONFIG_4P issu du meilleur 4P

    Pas de trou : tout ce qui n'est pas exactement 2 tombe dans >2.
    """
    gp = parse_json_dict(best2.get("global_params"))
    fp = parse_json_dict(best4.get("fourp_params"))

    # Si le meilleur 4P n'a pas assez de fourp_params, on récupère aussi des paramètres globaux utiles.
    # Mais on garde la séparation : 2P = global, >2P = CONFIG_4P.
    if not fp:
        fp = parse_json_dict(best4.get("global_params"))

    sig = hashlib.md5(json.dumps([gp, fp, best2.get("name"), best4.get("name")], sort_keys=True).encode()).hexdigest()[:8]
    return VariantSpec(
        name=f"final_hybrid_eq2_gt2_{sig}",
        family="final_hybrid_eq2_gt2",
        generation=generation,
        parent=f"2P:{best2.get('name')}|GT2:{best4.get('name')}",
        global_params=gp,
        fourp_params=fp,
    )
