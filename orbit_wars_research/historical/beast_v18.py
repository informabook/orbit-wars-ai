"""Reviewed excerpts from orbit_wars_beast_lab_v18_base_adaptive.py. See HISTORICAL_COVERAGE.md."""





import csv
import hashlib
import json
import random
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..beast import FOURP_RANGES, GLOBAL_RANGES, VariantSpec, mutate_spec, random_spec, safe_float
from ..framework.replays import load_replay


def mkdir(path):
    path.mkdir(parents=True, exist_ok=True)


def log(message):
    print(message)


def load_replay_objects(paths):
    # v0.3.1 uses explicit validated JSON, with deduplication and local-only labels.
    seen = set()
    for path in paths:
        digest, replay = load_replay(path)
        if digest in seen:
            continue
        seen.add(digest)
        yield f"replay-{len(seen):04d}", replay


# Source lines 158–168.
def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    mkdir(path.parent)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = sorted(set().union(*(r.keys() for r in rows)))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# Source lines 1159–1163.
def owner(p: Any) -> int:
    try:
        return int(p.get("owner", -1) if isinstance(p, dict) else p[1])
    except Exception:
        return -1


# Source lines 1166–1170.
def pships(p: Any) -> float:
    try:
        return float(p.get("ships", 0) if isinstance(p, dict) else p[5])
    except Exception:
        return 0.0


# Source lines 1173–1177.
def pprod(p: Any) -> float:
    try:
        return float(p.get("production", 0) if isinstance(p, dict) else p[6])
    except Exception:
        return 0.0


# Source lines 1180–1184.
def fowner(f: Any) -> int:
    try:
        return int(f.get("owner", -1) if isinstance(f, dict) else f[1])
    except Exception:
        return -1


# Source lines 1187–1191.
def fships(f: Any) -> float:
    try:
        return float(f.get("ships", 0) if isinstance(f, dict) else f[6])
    except Exception:
        return 0.0


# Source lines 1194–1198.
def obs_at(rep: Dict[str, Any], t: int) -> Optional[Dict[str, Any]]:
    try:
        return rep["steps"][t][0]["observation"]
    except Exception:
        return None


# Source lines 1201–1227.
def snapshot(rep: Dict[str, Any], t: int, players: int) -> Optional[Dict[str, Any]]:
    obs = obs_at(rep, t)
    if not obs:
        return None
    prod = [0.0] * players
    ships = [0.0] * players
    planets = [0.0] * players
    neutral_prod = 0.0
    neutral_big = 0

    for p in obs.get("planets", []) or []:
        o = owner(p)
        if 0 <= o < players:
            prod[o] += pprod(p)
            ships[o] += pships(p)
            planets[o] += 1
        else:
            neutral_prod += pprod(p)
            if pprod(p) >= 3.5 and pships(p) >= 25:
                neutral_big += 1

    for f in obs.get("fleets", []) or []:
        o = fowner(f)
        if 0 <= o < players:
            ships[o] += fships(f)

    return {"prod": prod, "ships": ships, "planets": planets, "neutral_prod": neutral_prod, "neutral_big": neutral_big}


# Source lines 1230–1245.
def analyse_actions(rep: Dict[str, Any], players: int) -> Dict[str, List[float]]:
    turns = [0] * players
    moves = [0] * players
    ships_sent = [0.0] * players
    for step in rep.get("steps", []):
        for i in range(min(players, len(step))):
            acts = step[i].get("action", [])
            if isinstance(acts, list) and acts:
                turns[i] += 1
                moves[i] += len(acts)
                for m in acts:
                    try:
                        ships_sent[i] += float(m[2])
                    except Exception:
                        pass
    return {"action_turns": turns, "moves": moves, "ships_sent": ships_sent}


# Source lines 1248–1322.
def analyse_one_replay(name: str, rep: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        steps = rep.get("steps", [])
        if not steps:
            return None
        players = len(steps[0])
        rewards = [float(x) for x in rep.get("rewards", [0.0] * players)]
        maxr = max(rewards) if rewards else 0.0
        winners = [i for i, r in enumerate(rewards) if abs(r - maxr) < 1e-9]

        checkpoints = sorted(set([0, 20, 40, 60, 80, 100, 140, 200, len(steps)-1]))
        checkpoints = [t for t in checkpoints if 0 <= t < len(steps)]
        snaps = {t: snapshot(rep, t, players) for t in checkpoints}
        snaps = {t: s for t, s in snaps.items() if s}

        if not snaps:
            return None

        sym = []
        for t in [20, 40, 60, 80]:
            if t in snaps:
                for key in ["prod", "ships"]:
                    vals = snaps[t][key]
                    mean = statistics.mean(vals) if vals else 0
                    if mean <= 0:
                        sym.append(1.0)
                    else:
                        sym.append(max(0.0, 1.0 - statistics.pstdev(vals) / max(1.0, mean)))
        symmetry = statistics.mean(sym) if sym else 0.0

        lead_loss_step = ""
        lead_reason = ""
        for t in checkpoints:
            if t < 60 or t not in snaps:
                continue
            prod = snaps[t]["prod"]
            ships = snaps[t]["ships"]
            prod_rank = sorted(range(players), key=lambda i: prod[i], reverse=True).index(0) + 1
            ship_rank = sorted(range(players), key=lambda i: ships[i], reverse=True).index(0) + 1
            if prod_rank > 1 or ship_rank > 2:
                lead_loss_step = str(t)
                lead_reason = f"prod_rank={prod_rank};ship_rank={ship_rank}"
                break

        t80 = max([t for t in snaps if t <= 80], default=min(snaps))
        tf = max(snaps)
        s80 = snaps[t80]
        sf = snaps[tf]
        act = analyse_actions(rep, players)

        return {
            "name": name,
            "mode": f"{players}P",
            "steps": len(steps),
            "rewards": json.dumps(rewards),
            "p0_strict_win": 1 if winners == [0] else 0,
            "draw": 1 if len(winners) > 1 else 0,
            "p0_loss": 1 if 0 not in winners else 0,
            "winner_count": len(winners),
            "first_lead_loss_step": lead_loss_step,
            "lead_loss_reason": lead_reason,
            "symmetry_opening": symmetry,
            "p0_prod_80": s80["prod"][0],
            "p0_ships_80": s80["ships"][0],
            "p0_planets_80": s80["planets"][0],
            "neutral_big_left_80": s80["neutral_big"],
            "neutral_prod_left_80": s80["neutral_prod"],
            "p0_final_prod": sf["prod"][0],
            "p0_final_ships": sf["ships"][0],
            "p0_action_turns": act["action_turns"][0],
            "p0_moves": act["moves"][0],
            "p0_ships_sent": act["ships_sent"][0],
        }
    except Exception:
        return None


# Source lines 1330–1334.
def rank_desc(vals: List[float], idx: int) -> int:
    try:
        return sorted(range(len(vals)), key=lambda i: vals[i], reverse=True).index(idx) + 1
    except Exception:
        return 999


# Source lines 1337–1348.
def replay_outcome_label(rewards: List[float]) -> str:
    if not rewards:
        return "unknown"
    maxr = max(rewards)
    winners = [i for i, r in enumerate(rewards) if abs(float(r) - float(maxr)) < 1e-9]
    if winners == [0]:
        return "p0_win"
    if 0 in winners and len(winners) > 1:
        return "p0_draw_shared_win"
    if len(winners) > 1:
        return "draw_without_p0"
    return "p0_loss"


# Source lines 1351–1383.
def snapshot_extended(rep: Dict[str, Any], t: int, players: int) -> Optional[Dict[str, Any]]:
    s = snapshot(rep, t, players)
    if not s:
        return None

    prod = s["prod"]
    ships = s["ships"]
    planets = s["planets"]
    max_prod = max(prod) if prod else 0.0
    max_ships = max(ships) if ships else 0.0
    avg_prod = statistics.mean(prod) if prod else 0.0
    avg_ships = statistics.mean(ships) if ships else 0.0
    spread_prod = (statistics.pstdev(prod) if len(prod) > 1 else 0.0)
    spread_ships = (statistics.pstdev(ships) if len(ships) > 1 else 0.0)

    s.update({
        "t": t,
        "p0_prod": prod[0] if prod else 0.0,
        "p0_ships": ships[0] if ships else 0.0,
        "p0_planets": planets[0] if planets else 0.0,
        "p0_prod_rank": rank_desc(prod, 0),
        "p0_ship_rank": rank_desc(ships, 0),
        "p0_planet_rank": rank_desc(planets, 0),
        "max_prod": max_prod,
        "max_ships": max_ships,
        "avg_prod": avg_prod,
        "avg_ships": avg_ships,
        "spread_prod": spread_prod,
        "spread_ships": spread_ships,
        "p0_prod_gap_to_best": max_prod - (prod[0] if prod else 0.0),
        "p0_ship_gap_to_best": max_ships - (ships[0] if ships else 0.0),
    })
    return s


# Source lines 1386–1437.
def action_phase_rows(name: str, rep: Dict[str, Any], players: int) -> List[Dict[str, Any]]:
    phases = [
        ("opening_0_40", 0, 40),
        ("mid_41_100", 41, 100),
        ("late_101_200", 101, 200),
        ("end_201_plus", 201, 999999),
    ]
    rows = []
    phase_stats = {
        ph: {
            "name": name,
            "mode": f"{players}P",
            "phase": ph,
            "p0_action_turns": 0,
            "p0_moves": 0,
            "p0_ships_sent": 0.0,
            "all_moves": 0,
            "all_ships_sent": 0.0,
        }
        for ph, _, _ in phases
    }

    steps = rep.get("steps", []) or []
    for t, step in enumerate(steps):
        phase_name = None
        for ph, a, b in phases:
            if a <= t <= b:
                phase_name = ph
                break
        if phase_name is None:
            continue

        row = phase_stats[phase_name]
        for i in range(min(players, len(step))):
            acts = step[i].get("action", [])
            if isinstance(acts, list) and acts:
                row["all_moves"] += len(acts)
                if i == 0:
                    row["p0_action_turns"] += 1
                    row["p0_moves"] += len(acts)
                for m in acts:
                    try:
                        ships = float(m[2])
                    except Exception:
                        ships = 0.0
                    row["all_ships_sent"] += ships
                    if i == 0:
                        row["p0_ships_sent"] += ships

    for ph, _, _ in phases:
        rows.append(phase_stats[ph])
    return rows


# Source lines 1440–1491.
def classify_failure_situations(case: Dict[str, Any]) -> List[str]:
    if case.get("outcome") == "p0_win":
        return ["p0_win_reference"]

    tags: List[str] = []

    players = int(case.get("players", 0) or 0)
    lead_loss_step = safe_float(case.get("first_lead_loss_step_num"), 9999)
    p0_prod_80 = safe_float(case.get("p0_prod_80"))
    p0_ships_80 = safe_float(case.get("p0_ships_80"))
    p0_ship_rank_80 = int(case.get("p0_ship_rank_80") or 999)
    p0_prod_rank_80 = int(case.get("p0_prod_rank_80") or 999)
    neutral_big_80 = safe_float(case.get("neutral_big_left_80"))
    symmetry = safe_float(case.get("symmetry_opening"))
    p0_moves_opening = safe_float(case.get("p0_moves_opening"))
    p0_ships_sent_opening = safe_float(case.get("p0_ships_sent_opening"))
    p0_prod_final = safe_float(case.get("p0_final_prod"))
    max_prod_final = safe_float(case.get("max_final_prod"))
    p0_ship_gap_80 = safe_float(case.get("p0_ship_gap_to_best_80"))
    p0_prod_gap_80 = safe_float(case.get("p0_prod_gap_to_best_80"))

    if lead_loss_step <= 80:
        tags.append("early_lead_loss")
    elif lead_loss_step <= 140:
        tags.append("midgame_lead_loss")

    if neutral_big_80 >= 2 and (p0_prod_rank_80 > 1 or p0_prod_gap_80 >= 1.0):
        tags.append("expansion_stall_big_neutrals")

    if p0_ship_rank_80 >= (3 if players >= 4 else 2) or p0_ship_gap_80 >= 20:
        tags.append("ship_deficit_midgame")

    if p0_moves_opening <= 2:
        tags.append("passive_low_actions")

    if p0_ships_sent_opening > 0 and p0_ships_80 > 0:
        if p0_ships_sent_opening / max(1.0, p0_ships_80) >= 2.5 and p0_ship_rank_80 > 1:
            tags.append("overcommit_or_bad_trade")

    if case.get("outcome") in ("p0_draw_shared_win", "draw_without_p0") and symmetry >= 0.82:
        tags.append("draw_symmetric_lock")

    if case.get("outcome") != "p0_win" and p0_prod_final >= max_prod_final - 0.1 and p0_prod_final > 0:
        tags.append("endgame_not_converting")

    if players >= 4 and case.get("outcome") != "p0_win" and p0_prod_rank_80 <= 2 and p0_ship_rank_80 >= 3:
        tags.append("fourp_politics_surrounded")

    if not tags:
        tags.append("unclassified_failure")

    return tags


# Source lines 1494–1630.
def analyse_one_replay_situations(name: str, rep: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    try:
        steps = rep.get("steps", []) or []
        if not steps:
            return None, [], []

        players = len(steps[0])
        rewards = [float(x) for x in rep.get("rewards", [0.0] * players)]
        outcome = replay_outcome_label(rewards)

        checkpoints = sorted(set([0, 10, 20, 40, 60, 80, 100, 140, 200, len(steps) - 1]))
        checkpoints = [t for t in checkpoints if 0 <= t < len(steps)]

        phase_rows = []
        snaps: Dict[int, Dict[str, Any]] = {}
        for t in checkpoints:
            s = snapshot_extended(rep, t, players)
            if not s:
                continue
            snaps[t] = s
            phase_rows.append({
                "name": name,
                "mode": f"{players}P",
                "outcome": outcome,
                "t": t,
                "p0_prod": s["p0_prod"],
                "p0_ships": s["p0_ships"],
                "p0_planets": s["p0_planets"],
                "p0_prod_rank": s["p0_prod_rank"],
                "p0_ship_rank": s["p0_ship_rank"],
                "p0_planet_rank": s["p0_planet_rank"],
                "p0_prod_gap_to_best": s["p0_prod_gap_to_best"],
                "p0_ship_gap_to_best": s["p0_ship_gap_to_best"],
                "neutral_big_left": s["neutral_big"],
                "neutral_prod_left": s["neutral_prod"],
                "spread_prod": s["spread_prod"],
                "spread_ships": s["spread_ships"],
            })

        if not snaps:
            return None, [], []

        # Opening symmetry.
        sym_vals = []
        for t in [20, 40, 60, 80]:
            if t in snaps:
                for key in ["prod", "ships"]:
                    vals = snaps[t][key]
                    mean = statistics.mean(vals) if vals else 0.0
                    if mean <= 0:
                        sym_vals.append(1.0)
                    else:
                        sym_vals.append(max(0.0, 1.0 - statistics.pstdev(vals) / max(1.0, mean)))
        symmetry = statistics.mean(sym_vals) if sym_vals else 0.0

        first_lead_loss_step = ""
        first_lead_loss_step_num = 9999
        first_lead_loss_reason = ""
        for t in checkpoints:
            if t < 40 or t not in snaps:
                continue
            s = snaps[t]
            if s["p0_prod_rank"] > 1 or s["p0_ship_rank"] > 2:
                first_lead_loss_step = str(t)
                first_lead_loss_step_num = t
                first_lead_loss_reason = f"prod_rank={s['p0_prod_rank']};ship_rank={s['p0_ship_rank']}"
                break

        def nearest_snap(target: int) -> Dict[str, Any]:
            candidates = [t for t in snaps if t <= target]
            if not candidates:
                return snaps[min(snaps)]
            return snaps[max(candidates)]

        s40 = nearest_snap(40)
        s80 = nearest_snap(80)
        sfinal = snaps[max(snaps)]

        action_rows = action_phase_rows(name, rep, players)
        opening_actions = next((r for r in action_rows if r["phase"] == "opening_0_40"), {})
        mid_actions = next((r for r in action_rows if r["phase"] == "mid_41_100"), {})

        case = {
            "name": name,
            "mode": f"{players}P",
            "players": players,
            "steps": len(steps),
            "rewards": json.dumps(rewards),
            "outcome": outcome,
            "symmetry_opening": symmetry,
            "first_lead_loss_step": first_lead_loss_step,
            "first_lead_loss_step_num": first_lead_loss_step_num,
            "first_lead_loss_reason": first_lead_loss_reason,

            "p0_prod_40": s40["p0_prod"],
            "p0_ships_40": s40["p0_ships"],
            "p0_prod_rank_40": s40["p0_prod_rank"],
            "p0_ship_rank_40": s40["p0_ship_rank"],
            "neutral_big_left_40": s40["neutral_big"],

            "p0_prod_80": s80["p0_prod"],
            "p0_ships_80": s80["p0_ships"],
            "p0_planets_80": s80["p0_planets"],
            "p0_prod_rank_80": s80["p0_prod_rank"],
            "p0_ship_rank_80": s80["p0_ship_rank"],
            "p0_prod_gap_to_best_80": s80["p0_prod_gap_to_best"],
            "p0_ship_gap_to_best_80": s80["p0_ship_gap_to_best"],
            "neutral_big_left_80": s80["neutral_big"],
            "neutral_prod_left_80": s80["neutral_prod"],

            "p0_final_prod": sfinal["p0_prod"],
            "p0_final_ships": sfinal["p0_ships"],
            "p0_final_prod_rank": sfinal["p0_prod_rank"],
            "p0_final_ship_rank": sfinal["p0_ship_rank"],
            "max_final_prod": sfinal["max_prod"],
            "max_final_ships": sfinal["max_ships"],
            "neutral_big_final": sfinal["neutral_big"],

            "p0_moves_opening": opening_actions.get("p0_moves", 0),
            "p0_ships_sent_opening": opening_actions.get("p0_ships_sent", 0.0),
            "p0_moves_mid": mid_actions.get("p0_moves", 0),
            "p0_ships_sent_mid": mid_actions.get("p0_ships_sent", 0.0),
        }
        tags = classify_failure_situations(case)
        case["situation_tags"] = "|".join(tags)
        case["primary_situation"] = tags[0]

        return case, phase_rows, action_rows
    except Exception as e:
        return {
            "name": name,
            "mode": "unknown",
            "outcome": "error",
            "primary_situation": "analysis_error",
            "situation_tags": "analysis_error",
            "error": repr(e),
        }, [], []


# Source lines 1633–1720.
def run_failure_situation_analysis(replay_files: List[Path], tables_dir: Path, charts_dir: Optional[Path] = None) -> Dict[str, Any]:
    mkdir(tables_dir)

    cases: List[Dict[str, Any]] = []
    phase_rows: List[Dict[str, Any]] = []
    action_rows: List[Dict[str, Any]] = []

    for name, rep in load_replay_objects(replay_files):
        case, ph, act = analyse_one_replay_situations(name, rep)
        if not case or case.get('outcome') == 'error':
            raise ValueError(f'Beast Lab could not analyze {name}')
        cases.append(case)
        phase_rows.extend(ph)
        action_rows.extend(act)

    write_csv(tables_dir / "replay_failure_cases.csv", cases)
    write_csv(tables_dir / "replay_phase_metrics.csv", phase_rows)
    write_csv(tables_dir / "replay_action_phase_summary.csv", action_rows)

    # Situation summary.
    summary_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for c in cases:
        tags = str(c.get("situation_tags", "unclassified_failure")).split("|")
        for tag in tags:
            key = (str(c.get("mode", "")), str(c.get("outcome", "")), tag)
            row = summary_map.setdefault(key, {
                "mode": key[0],
                "outcome": key[1],
                "situation": key[2],
                "count": 0,
                "avg_symmetry_opening": 0.0,
                "avg_neutral_big_left_80": 0.0,
                "avg_p0_prod_gap_to_best_80": 0.0,
                "avg_p0_ship_gap_to_best_80": 0.0,
            })
            row["count"] += 1
            row["avg_symmetry_opening"] += safe_float(c.get("symmetry_opening"))
            row["avg_neutral_big_left_80"] += safe_float(c.get("neutral_big_left_80"))
            row["avg_p0_prod_gap_to_best_80"] += safe_float(c.get("p0_prod_gap_to_best_80"))
            row["avg_p0_ship_gap_to_best_80"] += safe_float(c.get("p0_ship_gap_to_best_80"))

    summary_rows = []
    for row in summary_map.values():
        n = max(1, int(row["count"]))
        for k in ["avg_symmetry_opening", "avg_neutral_big_left_80", "avg_p0_prod_gap_to_best_80", "avg_p0_ship_gap_to_best_80"]:
            row[k] = row[k] / n
        summary_rows.append(row)
    summary_rows.sort(key=lambda r: (r["mode"], -int(r["count"]), r["situation"]))
    write_csv(tables_dir / "replay_situation_summary.csv", summary_rows)

    # Lead loss timeline.
    bins = {
        "no_lead_loss": 0,
        "loss_0_40": 0,
        "loss_41_80": 0,
        "loss_81_140": 0,
        "loss_141_plus": 0,
    }
    for c in cases:
        step = safe_float(c.get("first_lead_loss_step_num"), 9999)
        if step >= 9999:
            bins["no_lead_loss"] += 1
        elif step <= 40:
            bins["loss_0_40"] += 1
        elif step <= 80:
            bins["loss_41_80"] += 1
        elif step <= 140:
            bins["loss_81_140"] += 1
        else:
            bins["loss_141_plus"] += 1
    lead_rows = [{"lead_loss_bin": k, "count": v} for k, v in bins.items()]
    write_csv(tables_dir / "replay_lead_loss_timeline.csv", lead_rows)

    if charts_dir is not None:
        make_failure_charts(cases, summary_rows, lead_rows, charts_dir)

    log(f"Analyse situations: {len(cases)} cas, {len(summary_rows)} lignes de synthèse")
    if summary_rows:
        log("Top situations:")
        for r in summary_rows[:8]:
            log(f"  {r['mode']} {r['outcome']} {r['situation']}: {r['count']}")

    return {
        "cases": len(cases),
        "summary_rows": len(summary_rows),
    }


# Source lines 1723–1780.
def make_failure_charts(cases: List[Dict[str, Any]], summary_rows: List[Dict[str, Any]], lead_rows: List[Dict[str, Any]], charts: Path) -> None:
    if not cases:
        return
    mkdir(charts)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Situation counts excluding p0 wins for readability.
    counts: Dict[str, int] = {}
    for c in cases:
        if c.get("outcome") == "p0_win":
            continue
        for tag in str(c.get("situation_tags", "unclassified_failure")).split("|"):
            counts[tag] = counts.get(tag, 0) + 1

    if counts:
        items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:16]
        labels = [x[0] for x in items]
        vals = [x[1] for x in items]
        fig = plt.figure(figsize=(11, 6))
        ax = fig.add_subplot(111)
        ax.bar(labels, vals)
        ax.set_title("Failure situation counts")
        ax.set_ylabel("Count")
        ax.set_xticklabels(labels, rotation=45, ha="right")
        fig.tight_layout()
        fig.savefig(charts / "failure_situation_counts.png", dpi=140)
        plt.close(fig)

    if lead_rows:
        labels = [r["lead_loss_bin"] for r in lead_rows]
        vals = [int(r["count"]) for r in lead_rows]
        fig = plt.figure(figsize=(8, 5))
        ax = fig.add_subplot(111)
        ax.bar(labels, vals)
        ax.set_title("Lead loss timing")
        ax.set_ylabel("Replays")
        ax.set_xticklabels(labels, rotation=30, ha="right")
        fig.tight_layout()
        fig.savefig(charts / "lead_loss_timing.png", dpi=140)
        plt.close(fig)

    # Neutral big by outcome.
    outcomes = sorted(set(str(c.get("outcome", "")) for c in cases))
    vals = []
    for o in outcomes:
        ss = [c for c in cases if str(c.get("outcome", "")) == o]
        vals.append(statistics.mean([safe_float(c.get("neutral_big_left_80")) for c in ss]) if ss else 0.0)
    fig = plt.figure(figsize=(9, 5))
    ax = fig.add_subplot(111)
    ax.bar(outcomes, vals)
    ax.set_title("Big neutrals left at t=80 by outcome")
    ax.set_ylabel("Average big neutrals left")
    ax.set_xticklabels(outcomes, rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(charts / "neutral_big_by_outcome.png", dpi=140)
    plt.close(fig)


# Source lines 1959–1966.
def read_csv_dicts(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


# Source lines 1969–2024.
def load_failure_profile(tables_dir: Path) -> Dict[str, Any]:
    """
    Lit replay_situation_summary.csv et transforme l'analyse en profil utilisable.
    Ce profil va piloter les variantes : ce n'est plus juste du reporting joli.
    """
    rows = read_csv_dicts(tables_dir / "replay_situation_summary.csv")
    if not rows:
        return {
            "dominant": [],
            "counts": {},
            "by_mode": {},
            "total_failures": 0,
            "notes": ["no situation summary"],
        }

    counts: Dict[str, float] = {}
    by_mode: Dict[str, Dict[str, float]] = {}
    total_failures = 0.0

    for r in rows:
        situation = str(r.get("situation", "") or "")
        outcome = str(r.get("outcome", "") or "")
        mode = str(r.get("mode", "") or "")
        if not situation or situation == "p0_win_reference" or outcome == "p0_win":
            continue
        c = safe_float(r.get("count"), 0.0)
        counts[situation] = counts.get(situation, 0.0) + c
        by_mode.setdefault(mode, {})[situation] = by_mode.setdefault(mode, {}).get(situation, 0.0) + c
        total_failures += c

    dominant = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    profile = {
        "dominant": dominant[:12],
        "counts": counts,
        "by_mode": by_mode,
        "total_failures": total_failures,
        "notes": [],
    }

    plan = build_failure_guidance_plan(profile)
    profile["plan"] = plan

    try:
        (tables_dir / "failure_guidance_plan.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    log("========== FAILURE-GUIDED PLAN ==========")
    if not dominant:
        log("Aucune défaillance dominante détectée, fallback variantes mixtes.")
    for situation, count in dominant[:8]:
        log(f"Situation dominante: {situation} count={count}")
    for item in plan[:8]:
        log(f"Guidance: {item['family']} weight={item['weight']} gp={item['global_params']} fp={item['fourp_params']}")
    log("=========================================")
    return profile


# Source lines 2027–2030.
def guidance_weight(profile: Dict[str, Any], situation: str, default: float = 1.0) -> float:
    c = safe_float(profile.get("counts", {}).get(situation), 0.0)
    total = max(1.0, safe_float(profile.get("total_failures"), 1.0))
    return max(default, 1.0 + 6.0 * c / total)


# Source lines 2033–2127.
def build_failure_guidance_plan(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Chaque plan = une hypothèse corrigée testable.
    On ne patch pas au hasard : on relie une famille de variante à une défaillance.
    """
    counts = profile.get("counts", {}) or {}
    plan: List[Dict[str, Any]] = []

    def add(situation: str, gp: Dict[str, Any], fp: Dict[str, Any], rationale: str) -> None:
        if safe_float(counts.get(situation), 0.0) <= 0 and situation != "fallback_mixed":
            return
        plan.append({
            "situation": situation,
            "family": "guided_" + situation,
            "weight": guidance_weight(profile, situation),
            "global_params": gp,
            "fourp_params": fp,
            "rationale": rationale,
        })

    add(
        "expansion_stall_big_neutrals",
        {"horizon": 20, "max_offensive_targets": 14, "max_waves_per_turn": 7, "roi_threshold": 1.20, "min_ships_to_launch": 3.0},
        {"horizon": 15, "max_offensive_targets": 12, "max_sources_per_lane": 8, "max_waves_per_turn": 5, "roi_threshold": 1.35, "min_ships_to_launch": 3.0},
        "Les grosses neutres restent libres: augmenter horizon/cibles/vagues et baisser un peu le seuil ROI."
    )

    add(
        "draw_symmetric_lock",
        {"horizon": 22, "max_offensive_targets": 14, "max_waves_per_turn": 7, "roi_threshold": 1.35},
        {"horizon": 15, "max_offensive_targets": 12, "max_sources_per_lane": 7, "max_waves_per_turn": 5, "roi_threshold": 1.50},
        "Draw symétrique: casser la symétrie avec horizon plus long et attaque plus assertive."
    )

    add(
        "ship_deficit_midgame",
        {"max_defensive_targets": 5, "reinforce_size_beta": 2.8, "roi_threshold": 1.65, "min_ships_to_launch": 4.0},
        {"max_defensive_targets": 4, "max_sources_per_lane": 5, "max_waves_per_turn": 3, "roi_threshold": 1.75, "max_regroup_time": 7.0},
        "Déficit de flotte au midgame: préserver les vaisseaux, renforcer, limiter les drains trop agressifs."
    )

    add(
        "overcommit_or_bad_trade",
        {"max_sources_per_lane": 8, "max_waves_per_turn": 5, "roi_threshold": 1.80, "min_ships_to_launch": 5.0, "reinforce_size_beta": 2.8},
        {"max_sources_per_lane": 5, "max_waves_per_turn": 3, "roi_threshold": 2.0, "min_ships_to_launch": 5.0, "max_regroup_time": 7.0},
        "Overcommit: réduire les vagues/sources et exiger un meilleur ROI."
    )

    add(
        "passive_low_actions",
        {"max_offensive_targets": 14, "max_sources_per_lane": 12, "max_waves_per_turn": 7, "roi_threshold": 1.20, "min_ships_to_launch": 3.0},
        {"max_offensive_targets": 12, "max_sources_per_lane": 8, "max_waves_per_turn": 5, "roi_threshold": 1.35, "min_ships_to_launch": 3.0},
        "Bot trop passif: plus de cibles et seuils de lancement plus bas."
    )

    add(
        "early_lead_loss",
        {"horizon": 20, "max_defensive_targets": 5, "reinforce_size_beta": 2.8, "roi_threshold": 1.65},
        {"horizon": 14, "max_defensive_targets": 4, "max_sources_per_lane": 6, "roi_threshold": 1.75, "max_regroup_time": 7.0},
        "Lead perdu trop tôt: plus de défense/réassurance et moins de prise de risque en 4P."
    )

    add(
        "midgame_lead_loss",
        {"horizon": 20, "max_defensive_targets": 5, "max_offensive_targets": 12, "reinforce_size_beta": 2.5},
        {"horizon": 15, "max_defensive_targets": 4, "max_offensive_targets": 10, "roi_threshold": 1.75, "max_regroup_time": 7.0},
        "Perte de lead au midgame: équilibrer expansion et conservation."
    )

    add(
        "endgame_not_converting",
        {"horizon": 22, "max_offensive_targets": 14, "max_waves_per_turn": 7, "roi_threshold": 1.20},
        {"horizon": 15, "max_offensive_targets": 12, "max_waves_per_turn": 5, "roi_threshold": 1.35},
        "Bonne position non convertie: rendre la fin de partie plus proactive."
    )

    add(
        "fourp_politics_surrounded",
        {"max_defensive_targets": 5, "reinforce_size_beta": 2.8, "roi_threshold": 1.65},
        {"horizon": 13, "max_sources_per_lane": 5, "max_defensive_targets": 4, "max_waves_per_turn": 3, "roi_threshold": 2.0, "max_regroup_time": 7.0},
        "En 4P il se fait entourer: politique plus conservatrice, moins de drains, plus de défense."
    )

    if not plan:
        plan.append({
            "situation": "fallback_mixed",
            "family": "guided_fallback_mixed",
            "weight": 1.0,
            "global_params": {"horizon": 20, "roi_threshold": 1.35, "max_offensive_targets": 14},
            "fourp_params": {"horizon": 14, "roi_threshold": 1.75, "max_defensive_targets": 4},
            "rationale": "Fallback car pas assez de situations classées."
        })

    plan.sort(key=lambda x: safe_float(x.get("weight")), reverse=True)
    return plan


# Source lines 2130–2140.
def blend_params(base: Dict[str, Any], ranges: Dict[str, List[Any]], rng: random.Random, mutation_rate: float = 0.45) -> Dict[str, Any]:
    out = dict(base)
    for k, vals in ranges.items():
        if k in out and rng.random() < mutation_rate:
            out[k] = rng.choice(vals)
        elif k not in out and rng.random() < mutation_rate * 0.35:
            out[k] = rng.choice(vals)
    # Drop one param occasionally to avoid overfitting.
    if out and rng.random() < 0.12:
        out.pop(rng.choice(list(out)), None)
    return out


# Source lines 2143–2149.
def spec_from_guidance(item: Dict[str, Any], rng: random.Random, idx: int, generation: int) -> VariantSpec:
    gp = blend_params(dict(item.get("global_params", {})), GLOBAL_RANGES, rng, mutation_rate=0.35)
    fp = blend_params(dict(item.get("fourp_params", {})), FOURP_RANGES, rng, mutation_rate=0.35)

    sig = hashlib.md5(json.dumps([item.get("situation"), gp, fp, idx, generation], sort_keys=True).encode()).hexdigest()[:8]
    fam = str(item.get("family", "guided_unknown"))
    return VariantSpec(f"g{generation:02d}_{fam}_{idx:04d}_{sig}", fam, generation, "", gp, fp)


# Source lines 2152–2170.
def choose_guidance_item(profile: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    plan = list(profile.get("plan") or [])
    if not plan:
        return {
            "family": "guided_fallback_mixed",
            "situation": "fallback_mixed",
            "weight": 1.0,
            "global_params": {"horizon": 20, "roi_threshold": 1.35},
            "fourp_params": {"horizon": 14, "roi_threshold": 1.75},
        }
    weights = [max(0.1, safe_float(x.get("weight"), 1.0)) for x in plan]
    total = sum(weights)
    pick = rng.random() * total
    acc = 0.0
    for item, w in zip(plan, weights):
        acc += w
        if pick <= acc:
            return item
    return plan[0]


# Source lines 2173–2190.
def build_guided_population(profile: Dict[str, Any], rng: random.Random, population_size: int, generation: int) -> List[VariantSpec]:
    specs: List[VariantSpec] = []
    plan = list(profile.get("plan") or [])

    # First include direct representatives of the most important failure families.
    for item in plan[:min(len(plan), max(1, population_size // 2))]:
        if len(specs) >= population_size:
            break
        specs.append(spec_from_guidance(item, rng, len(specs), generation))

    # Fill with weighted guided variants.
    while len(specs) < population_size:
        if rng.random() < 0.82:
            specs.append(spec_from_guidance(choose_guidance_item(profile, rng), rng, len(specs), generation))
        else:
            specs.append(random_spec(rng, len(specs), generation, rng.choice(["global", "fourp", "mixed"])))

    return specs


# Source lines 2193–2214.
def mutate_spec_guided(parent: VariantSpec, profile: Dict[str, Any], rng: random.Random, idx: int, generation: int) -> VariantSpec:
    # 65%: mutate an elite toward a dominant failure correction.
    if rng.random() < 0.65:
        item = choose_guidance_item(profile, rng)
        gp = dict(parent.global_params)
        fp = dict(parent.fourp_params)

        for k, v in dict(item.get("global_params", {})).items():
            if rng.random() < 0.55:
                gp[k] = v
        for k, v in dict(item.get("fourp_params", {})).items():
            if rng.random() < 0.65:
                fp[k] = v

        gp = blend_params(gp, GLOBAL_RANGES, rng, mutation_rate=0.22)
        fp = blend_params(fp, FOURP_RANGES, rng, mutation_rate=0.28)

        sig = hashlib.md5(json.dumps([parent.name, item.get("situation"), gp, fp, idx, generation], sort_keys=True).encode()).hexdigest()[:8]
        fam = "guided_child_" + str(item.get("situation", "mixed"))
        return VariantSpec(f"g{generation:02d}_{fam}_{idx:04d}_{sig}", fam, generation, parent.name, gp, fp)

    return mutate_spec(parent, rng, idx, generation)


# Source lines 2257–2273.
def file_looks_patchable(path: Path) -> bool:
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    needles = [
        "CONFIG_4P = dataclasses.replace(",
        "PlannerConfig",
        "roi_threshold",
        "max_offensive_targets",
        "max_defensive_targets",
        "reinforce_size_beta",
        "min_ships_to_launch",
        "max_waves_per_turn",
        "max_sources_per_lane",
    ]
    return any(n in txt for n in needles)


# Source lines 2276–2318.
def discover_patch_targets(root: Path) -> List[Path]:
    """
    Trouve les fichiers réellement patchables dans la base actuelle.
    Compatible avec :
    - ancienne base combo*.py ;
    - nouvelle base flat portfolio b01_*.py / b02_*.py ;
    - configs dans orbit_lite/*.py.
    """
    targets: List[Path] = []
    seen = set()

    preferred_names = [
        "combo0_main.py",
        "combo1_combo0_main.py",
        "combo1_combo1_main.py",
        "b01_032_submission_v40_exact_producer_control_main.py",
        "b02_014_submission_21_agent_producer_v2.py",
        "b02_014_submission_21_agent_v21b_base.py",
        "b02_014_submission_21_main.py",
    ]

    def add(p: Path) -> None:
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        if p.exists() and p.is_file() and p.suffix == ".py" and str(rp) not in seen and file_looks_patchable(p):
            seen.add(str(rp))
            targets.append(p)

    for name in preferred_names:
        add(root / name)

    for p in sorted(root.glob("*.py")):
        # main.py est souvent un routeur ; on le patch seulement s'il contient vraiment des paramètres.
        add(p)

    orbit_lite = root / "orbit_lite"
    if orbit_lite.is_dir():
        for p in sorted(orbit_lite.glob("*.py")):
            add(p)

    return targets


# Source lines 2321–2327.
def describe_patch_targets(root: Path) -> str:
    targets = discover_patch_targets(root)
    if not targets:
        root_files = [p.name for p in sorted(root.glob("*.py"))]
        lite_files = ["orbit_lite/" + p.name for p in sorted((root / "orbit_lite").glob("*.py"))] if (root / "orbit_lite").is_dir() else []
        return "aucune target patchable. root_py=" + ",".join(root_files[:20]) + " orbit_lite_py=" + ",".join(lite_files[:20])
    return ", ".join(str(p.relative_to(root)) for p in targets)
