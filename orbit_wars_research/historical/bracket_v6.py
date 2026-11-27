"""Reviewed excerpts from orbit_evolution_intelligent_variants_v6_fixed.py. See HISTORICAL_COVERAGE.md."""





import random
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# Source lines 135–141.
@dataclass
class Candidate:
    name: str
    source: str = "original"
    generation: int = 0
    parents: Optional[List[str]] = None


# Source lines 148–150.
def safe_name(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]+", "_", str(s))
    return re.sub(r"_+", "_", s).strip("_") or "agent"


# Source lines 381–392.
def pair_tasks(a: Candidate, b: Candidate, phase: str, round_no: int, best_of: int, rng: random.Random) -> List[Dict[str, Any]]:
    tasks = []
    for k in range(best_of):
        aa, bb = (a, b) if k % 2 == 0 else (b, a)
        tasks.append({
            "phase": phase, "round": round_no,
            "match_id": f"{phase}_r{round_no:02d}_{safe_name(a.name)}_{safe_name(b.name)}_{k:02d}",
            "seed": rng.randint(1, 2_000_000_000),
            "a_name": aa.name, "b_name": bb.name,
        })
    return tasks


# Source lines 413–489.
def initial_left_right_finalists(pool: List[Candidate], phase: str, best_of: int, seed: int, run_round) -> List[Candidate]:
    """Bracket élimination parallèle par round.

    Ancienne version: lançait un duel à la fois, donc seulement 3 matchs en parallèle
    avec best-of=3. Cette version lance tous les duels du round en même temps, donc
    workers=8 sert vraiment.
    """
    rng = random.Random(seed)
    current = list(pool)
    rng.shuffle(current)
    round_no = 0

    while len(current) > 2:
        round_no += 1

        auto: List[Candidate] = []
        if len(current) % 2 == 1:
            bye = current.pop()
            auto.append(bye)

        # Tous les duels du round sont préparés d'abord, puis exécutés ensemble.
        pairs: List[tuple[Candidate, Candidate]] = []
        tasks: List[Dict[str, Any]] = []
        for i in range(0, len(current), 2):
            a = current[i]
            b = current[i + 1]
            pairs.append((a, b))
            tasks += pair_tasks(a, b, phase, round_no, best_of, rng)

        rows = run_round(tasks)

        # Agrégation par paire réelle, même si l'ordre a/b est alterné.
        pair_by_key: Dict[tuple[str, str], tuple[Candidate, Candidate]] = {}
        for a, b in pairs:
            pair_by_key[tuple(sorted([a.name, b.name]))] = (a, b)

        wins: Dict[tuple[str, str], Dict[str, int]] = {}
        reward_sum: Dict[tuple[str, str], Dict[str, float]] = {}
        for row in rows:
            key = tuple(sorted([str(row.get("a", "")), str(row.get("b", ""))]))
            wins.setdefault(key, {})
            reward_sum.setdefault(key, {})
            winner = str(row.get("winner", ""))
            wins[key][winner] = wins[key].get(winner, 0) + 1

            for side, reward_key in [("a", "reward_a"), ("b", "reward_b")]:
                name = str(row.get(side, ""))
                try:
                    reward_sum[key][name] = reward_sum[key].get(name, 0.0) + float(row.get(reward_key, 0) or 0)
                except Exception:
                    reward_sum[key][name] = reward_sum[key].get(name, 0.0)

        nxt: List[Candidate] = list(auto)
        for key, (a, b) in pair_by_key.items():
            sc = wins.get(key, {})
            rw = reward_sum.get(key, {})
            wa = sc.get(a.name, 0)
            wb = sc.get(b.name, 0)
            if wa > wb:
                winner = a
            elif wb > wa:
                winner = b
            else:
                winner = a if rw.get(a.name, 0.0) >= rw.get(b.name, 0.0) else b
            nxt.append(winner)

        current = nxt
        rng.shuffle(current)

    if len(current) == 1:
        current = [current[0], current[0]]
    return current[:2]


# Source lines 1279–1301.
def bracket_rank(pool: List[Candidate], rows, phase_prefix: str = "") -> List[Candidate]:
    if phase_prefix:
        rows = [r for r in rows if r.get("phase", "").startswith(phase_prefix)]
    stats = {c.name: {"g": 0, "w": 0, "r": 0.0} for c in pool}
    for r in rows:
        for side, reward_key in [("a", "reward_a"), ("b", "reward_b")]:
            name = r.get(side, "")
            if name in stats:
                stats[name]["g"] += 1
                try:
                    stats[name]["r"] += float(r.get(reward_key, 0) or 0)
                except Exception:
                    pass
                if r.get("winner") == name:
                    stats[name]["w"] += 1

    def key(c: Candidate):
        s = stats.get(c.name, {"g": 0, "w": 0, "r": 0.0})
        g = max(1, s["g"])
        return (s["w"] / g, s["r"] / g, s["g"])

    return sorted(pool, key=key, reverse=True)
