"""Reviewed excerpt from historical Python source. See PROVENANCE.md for source and scope."""

from pathlib import Path
from typing import List

def write_intelligent_variant_main(build_dir: Path, module: str, variant: str, generation: int, side: str, parent_name: str) -> None:
    code = f"""# -*- coding: utf-8 -*-
# Intelligent single-parent variant.
# It never combines several models. It calls one base model, then applies a
# situation-aware tactical mutation to the returned moves.

import os
import sys
import math
import random

try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _HERE = os.getcwd()
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import {module} as BASE

VARIANT = {variant!r}
GENERATION = {generation!r}
SIDE = {side!r}
PARENT_NAME = {parent_name!r}
_RNG = random.Random(abs(hash((VARIANT, GENERATION, SIDE, PARENT_NAME))) % (2**31))


def _obs_dict(obs):
    if isinstance(obs, dict):
        return obs
    d = {{}}
    for k in ("step", "player", "planets", "fleets"):
        try:
            d[k] = getattr(obs, k)
        except Exception:
            pass
    return d


def _step(obs):
    try:
        return int(_obs_dict(obs).get("step", 0) or 0)
    except Exception:
        return 0


def _player(obs):
    try:
        return int(_obs_dict(obs).get("player", 0) or 0)
    except Exception:
        return 0


def _planet_fields(p):
    # Robust adapter for most Orbit Wars observation shapes.
    # Known public bots often see planets as lists/tuples with id/owner/ships/prod-ish values,
    # but wrappers differ, so this is intentionally defensive.
    try:
        if isinstance(p, dict):
            pid = int(p.get("id", p.get("planet_id", p.get("index", 0))))
            owner = int(p.get("owner", -1))
            ships = float(p.get("ships", p.get("ship_count", p.get("num_ships", 0.0))))
            prod = float(p.get("production", p.get("growth", p.get("prod", 1.0))))
            x = float(p.get("x", 0.0))
            y = float(p.get("y", 0.0))
            return pid, owner, ships, prod, x, y
        if isinstance(p, (list, tuple)):
            vals = list(p)
            pid = int(vals[0]) if len(vals) > 0 else 0
            owner = int(vals[1]) if len(vals) > 1 else -1
            ships = float(vals[2]) if len(vals) > 2 else 0.0
            prod = float(vals[3]) if len(vals) > 3 else 1.0
            x = float(vals[4]) if len(vals) > 4 else 0.0
            y = float(vals[5]) if len(vals) > 5 else 0.0
            return pid, owner, ships, prod, x, y
    except Exception:
        pass
    return 0, -1, 0.0, 1.0, 0.0, 0.0


def _fleet_owner(f):
    try:
        if isinstance(f, dict):
            return int(f.get("owner", -1))
        if isinstance(f, (list, tuple)) and len(f) > 1:
            return int(f[1])
    except Exception:
        pass
    return -1


def _game_stats(obs):
    d = _obs_dict(obs)
    pid = _player(obs)
    planets = d.get("planets", []) or []
    fleets = d.get("fleets", []) or []

    my_ships = 0.0
    enemy_ships = 0.0
    neutral_ships = 0.0
    my_prod = 0.0
    enemy_prod = 0.0
    neutral_prod = 0.0
    my_count = 0
    enemy_count = 0
    neutral_count = 0
    owners = set()

    enemy_by_owner = {{}}

    for p in planets:
        _, owner, ships, prod, _, _ = _planet_fields(p)
        if owner >= 0:
            owners.add(owner)
        if owner == pid:
            my_ships += ships
            my_prod += prod
            my_count += 1
        elif owner < 0:
            neutral_ships += ships
            neutral_prod += prod
            neutral_count += 1
        else:
            enemy_ships += ships
            enemy_prod += prod
            enemy_count += 1
            enemy_by_owner[owner] = enemy_by_owner.get(owner, 0.0) + ships + prod * 6.0

    for f in fleets:
        o = _fleet_owner(f)
        if o >= 0:
            owners.add(o)

    leader_owner = None
    if enemy_by_owner:
        leader_owner = max(enemy_by_owner.items(), key=lambda kv: kv[1])[0]

    total_prod = my_prod + enemy_prod + neutral_prod
    total_ships = my_ships + enemy_ships + neutral_ships

    return {{
        "pid": pid,
        "step": _step(obs),
        "players": max(2, len(owners)),
        "my_ships": my_ships,
        "enemy_ships": enemy_ships,
        "neutral_ships": neutral_ships,
        "my_prod": my_prod,
        "enemy_prod": enemy_prod,
        "neutral_prod": neutral_prod,
        "my_count": my_count,
        "enemy_count": enemy_count,
        "neutral_count": neutral_count,
        "leader_owner": leader_owner,
        "prod_ratio": my_prod / max(1.0, enemy_prod),
        "ship_ratio": my_ships / max(1.0, enemy_ships),
        "total_prod": total_prod,
        "total_ships": total_ships,
    }}


def _call_base(obs, conf):
    try:
        try:
            out = BASE.agent(obs, conf)
        except TypeError:
            out = BASE.agent(obs)
        return out if isinstance(out, list) else []
    except BaseException:
        return []


def _move_parts(move):
    # Standard Orbit moves are usually [source, angle, ships].
    try:
        if isinstance(move, (list, tuple)) and len(move) >= 3:
            return move[0], float(move[1]), int(round(float(move[2]))), list(move)
    except Exception:
        pass
    return None, 0.0, 0, None


def _rebuild(template, src, angle, ships):
    try:
        if template is None:
            return template
        out = list(template)
        out[0] = src
        out[1] = float(angle)
        out[2] = int(max(1, round(ships)))
        return out
    except Exception:
        return template


def _scale_actions(actions, multiplier, angle_shift=0.0, drop_small_under=0):
    out = []
    for mv in actions:
        src, angle, ships, temp = _move_parts(mv)
        if temp is None:
            out.append(mv)
            continue
        new_ships = int(round(ships * multiplier))
        if drop_small_under and new_ships < drop_small_under:
            continue
        out.append(_rebuild(temp, src, angle + angle_shift, new_ships))
    return out if out else actions


def _cap_action_count(actions, max_count):
    if max_count <= 0 or len(actions) <= max_count:
        return actions
    return actions[:max_count]


def _spread_angles(actions, spread):
    out = []
    n = max(1, len(actions))
    for i, mv in enumerate(actions):
        src, angle, ships, temp = _move_parts(mv)
        if temp is None:
            out.append(mv)
            continue
        delta = ((i - (n - 1) / 2.0) / max(1.0, n)) * spread
        out.append(_rebuild(temp, src, angle + delta, ships))
    return out


def _random_jitter(actions, rng, ship_low, ship_high, angle_abs, keep_prob):
    out = []
    for mv in actions:
        if rng.random() > keep_prob:
            continue
        src, angle, ships, temp = _move_parts(mv)
        if temp is None:
            out.append(mv)
            continue
        mult = rng.uniform(ship_low, ship_high)
        angle_shift = rng.uniform(-angle_abs, angle_abs)
        out.append(_rebuild(temp, src, angle + angle_shift, max(1, ships * mult)))
    return out if out else actions


def _mutate(actions, obs):
    if not actions:
        return actions

    st = _game_stats(obs)
    step = st["step"]
    players = st["players"]
    behind = (st["prod_ratio"] < 0.85) or (st["ship_ratio"] < 0.80)
    ahead = (st["prod_ratio"] > 1.20) and (st["ship_ratio"] > 1.10)
    early = step < 80
    mid = 80 <= step < 200
    late = step >= 200
    fourp = players >= 4

    # 1) Expand: early/mid faster capture pressure, but avoid overcommitting late.
    if VARIANT == "expand":
        mult = 1.22 if early else (1.10 if mid else 0.92)
        if fourp:
            mult *= 0.94
        out = _scale_actions(actions, mult, angle_shift=0.004 if early else 0.0)
        return _cap_action_count(out, 8 if early else 6)

    # 2) Defense: less donation, fewer waves, stronger in 4P and when ahead.
    if VARIANT == "defense":
        mult = 0.68 if fourp else 0.78
        if ahead:
            mult *= 0.90
        if behind and not fourp:
            mult *= 1.12
        out = _scale_actions(actions, mult)
        return _cap_action_count(out, 4 if fourp else 5)

    # 3) Comeback: aggressive only if losing; otherwise becomes conservative.
    if VARIANT == "comeback":
        if behind:
            mult = 1.42 if early or mid else 1.22
            out = _scale_actions(actions, mult, angle_shift=-0.006)
            return _cap_action_count(out, 9)
        if ahead:
            out = _scale_actions(actions, 0.74)
            return _cap_action_count(out, 4)
        return _scale_actions(actions, 1.04)

    # 4) Anti-leader: for 4P, more pressure and spread; in 2P, mild aggression.
    if VARIANT == "anti_leader":
        mult = 1.18 if fourp else 1.08
        if ahead:
            mult *= 0.90
        if behind:
            mult *= 1.15
        out = _scale_actions(actions, mult)
        out = _spread_angles(out, 0.035 if fourp else 0.015)
        return _cap_action_count(out, 7 if fourp else 8)

    # 5) Sniper: fewer, stronger, short decisive waves.
    if VARIANT == "sniper":
        out = _cap_action_count(actions, 3 if fourp else 4)
        mult = 1.34 if not ahead else 1.08
        out = _scale_actions(out, mult, drop_small_under=3)
        return _spread_angles(out, 0.012)

    # 6) Timing wave: alternate quiet/punchy phases by turn window.
    if VARIANT == "timing_wave":
        cycle = (step // 25) % 3
        if cycle == 0:
            mult = 0.62 if not behind else 0.82
            count = 3
        elif cycle == 1:
            mult = 1.05
            count = 5
        else:
            mult = 1.55 if not ahead else 1.20
            count = 9
        out = _scale_actions(actions, mult)
        return _cap_action_count(out, count)

    # 7/8) Random strategic discoveries. Random but deterministic per agent,
    # and situation-aware so it is not pure casino roulette.
    if VARIANT == "random_alpha":
        seed = int(step * 131 + st["my_count"] * 17 + st["enemy_count"] * 31 + GENERATION * 997)
        rng = random.Random(seed + 12345)
        low = 0.55 if ahead else 0.80
        high = 1.85 if behind else 1.35
        keep = 0.65 if fourp else 0.82
        out = _random_jitter(actions, rng, low, high, 0.045, keep)
        if rng.random() < 0.35:
            out = list(reversed(out))
        return _cap_action_count(out, rng.randint(2, 9))

    if VARIANT == "random_beta":
        seed = int(step * 257 + len(actions) * 19 + GENERATION * 1009 + (7 if behind else 0))
        rng = random.Random(seed + 67890)
        if early:
            low, high = 0.75, 1.95
        elif late:
            low, high = 0.45, 1.25
        else:
            low, high = 0.65, 1.60
        keep = rng.uniform(0.50, 0.95)
        out = _random_jitter(actions, rng, low, high, rng.uniform(0.005, 0.060), keep)
        if rng.random() < 0.45:
            out = _spread_angles(out, rng.uniform(-0.050, 0.050))
        return _cap_action_count(out, rng.randint(1, 10))

    return actions


def agent(obs, conf=None):
    actions = _call_base(obs, conf)
    return _mutate(actions, obs)
"""
    (build_dir / "main.py").write_text(code, encoding="utf-8")

def write_combo_variant_main(build_dir: Path, modules: List[str], variant: str, generation: int, parent_names: List[str]) -> None:
    imports = "\n".join([f"import {m} as BRAIN_{i}" for i, m in enumerate(modules)])
    brains = ", ".join([f"BRAIN_{i}" for i in range(len(modules))])
    code = f"""# -*- coding: utf-8 -*-
# Combo variant: combines several parent models.
# These are intentionally limited to 2 combo strategies to avoid turning the
# evolution into a giant wrapper zoo.

import os
import sys
import random

try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _HERE = os.getcwd()
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

{imports}

BRAINS = [{brains}]
VARIANT = {variant!r}
GENERATION = {generation!r}
PARENT_NAMES = {parent_names!r}
_STATE = {{"bad": 0, "last_step": -1, "sticky": 0}}


def _obs_dict(obs):
    if isinstance(obs, dict):
        return obs
    d = {{}}
    for k in ("step", "player", "planets", "fleets"):
        try:
            d[k] = getattr(obs, k)
        except Exception:
            pass
    return d


def _step(obs):
    try:
        return int(_obs_dict(obs).get("step", 0) or 0)
    except Exception:
        return 0


def _player(obs):
    try:
        return int(_obs_dict(obs).get("player", 0) or 0)
    except Exception:
        return 0


def _owner_planet(p):
    try:
        if isinstance(p, dict):
            return int(p.get("owner", -1))
        if isinstance(p, (list, tuple)) and len(p) > 1:
            return int(p[1])
    except Exception:
        pass
    return -1


def _ships_planet(p):
    try:
        if isinstance(p, dict):
            return float(p.get("ships", p.get("ship_count", p.get("num_ships", 0.0))))
        if isinstance(p, (list, tuple)) and len(p) > 2:
            return float(p[2])
    except Exception:
        pass
    return 0.0


def _prod_planet(p):
    try:
        if isinstance(p, dict):
            return float(p.get("production", p.get("growth", p.get("prod", 1.0))))
        if isinstance(p, (list, tuple)) and len(p) > 3:
            return float(p[3])
    except Exception:
        pass
    return 1.0


def _fleet_owner(f):
    try:
        if isinstance(f, dict):
            return int(f.get("owner", -1))
        if isinstance(f, (list, tuple)) and len(f) > 1:
            return int(f[1])
    except Exception:
        pass
    return -1


def _stats(obs):
    d = _obs_dict(obs)
    pid = _player(obs)
    owners = set()
    my_ships = enemy_ships = my_prod = enemy_prod = neutral_prod = 0.0
    my_count = enemy_count = neutral_count = 0

    for p in d.get("planets", []) or []:
        o = _owner_planet(p)
        ships = _ships_planet(p)
        prod = _prod_planet(p)
        if o >= 0:
            owners.add(o)
        if o == pid:
            my_ships += ships
            my_prod += prod
            my_count += 1
        elif o < 0:
            neutral_prod += prod
            neutral_count += 1
        else:
            enemy_ships += ships
            enemy_prod += prod
            enemy_count += 1

    for f in d.get("fleets", []) or []:
        o = _fleet_owner(f)
        if o >= 0:
            owners.add(o)

    return {{
        "step": _step(obs),
        "players": max(2, len(owners)),
        "my_ships": my_ships,
        "enemy_ships": enemy_ships,
        "my_prod": my_prod,
        "enemy_prod": enemy_prod,
        "neutral_prod": neutral_prod,
        "my_count": my_count,
        "enemy_count": enemy_count,
        "neutral_count": neutral_count,
        "ship_ratio": my_ships / max(1.0, enemy_ships),
        "prod_ratio": my_prod / max(1.0, enemy_prod),
    }}


def _call(module, obs, conf):
    try:
        try:
            out = module.agent(obs, conf)
        except TypeError:
            out = module.agent(obs)
        return out if isinstance(out, list) else None
    except BaseException:
        return None


def _has_action(out):
    return isinstance(out, list) and len(out) > 0


def _move_key(m):
    try:
        if isinstance(m, (list, tuple)) and len(m) >= 3:
            return (m[0], round(float(m[1]), 3), int(round(float(m[2]))))
    except Exception:
        pass
    return str(m)


def _merge_actions(a, b, max_count):
    out = []
    seen = set()
    for m in list(a or []) + list(b or []):
        k = _move_key(m)
        if k in seen:
            continue
        seen.add(k)
        out.append(m)
        if len(out) >= max_count:
            break
    return out


def _choose_primary(obs):
    st = _stats(obs)
    step = st["step"]
    fourp = st["players"] >= 4
    behind = st["prod_ratio"] < 0.85 or st["ship_ratio"] < 0.80
    ahead = st["prod_ratio"] > 1.20 and st["ship_ratio"] > 1.15

    if VARIANT == "combo_situation":
        # BRAIN_0 = gauche, BRAIN_1 = droite.
        # Early: modèle le plus expansionniste supposé = brain0.
        # 4P ou position favorable: brain1 plus conservateur.
        if fourp and not behind:
            return min(1, len(BRAINS) - 1)
        if ahead and step > 120:
            return min(1, len(BRAINS) - 1)
        return 0

    if VARIANT == "combo_vote_merge":
        # Primary sticky but changes by phase to test synergies.
        if step < 80:
            return 0
        if step < 180:
            return min(1, len(BRAINS) - 1)
        return int(_STATE.get("sticky", 0)) % max(1, len(BRAINS))

    return 0


def agent(obs, conf=None):
    if not BRAINS:
        return []

    step = _step(obs)
    if step <= 1 or step < _STATE.get("last_step", -1):
        _STATE["bad"] = 0
        _STATE["sticky"] = 0
    _STATE["last_step"] = step

    primary = max(0, min(_choose_primary(obs), len(BRAINS) - 1))
    secondary = 1 - primary if len(BRAINS) > 1 else primary

    if VARIANT == "combo_situation":
        out = _call(BRAINS[primary], obs, conf)
        if _has_action(out):
            _STATE["bad"] = 0
            return out
        _STATE["bad"] = int(_STATE.get("bad", 0)) + 1
        out2 = _call(BRAINS[secondary], obs, conf)
        if out2 is not None:
            if _has_action(out2):
                _STATE["sticky"] = secondary
                _STATE["bad"] = 0
            return out2
        return out or []

    if VARIANT == "combo_vote_merge":
        out1 = _call(BRAINS[primary], obs, conf) or []
        out2 = _call(BRAINS[secondary], obs, conf) or []

        st = _stats(obs)
        if st["players"] >= 4:
            max_count = 5
        elif st["prod_ratio"] < 0.85:
            max_count = 9
        else:
            max_count = 7

        # When both models propose moves, merge. Otherwise fallback to whichever acts.
        if out1 and out2:
            merged = _merge_actions(out1, out2, max_count=max_count)
            return merged if merged else out1
        if out1:
            return out1
        if out2:
            _STATE["sticky"] = secondary
            return out2
        return []

    out = _call(BRAINS[primary], obs, conf)
    return out if out is not None else []
"""
    (build_dir / "main.py").write_text(code, encoding="utf-8")
