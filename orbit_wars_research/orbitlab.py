"""Reviewed excerpt from historical Python source. See PROVENANCE.md for source and scope."""

import argparse
import itertools
import json
import random
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# PyPI registry name, verified in the Phase 2 smoke test.
NOM_ENV = "orbit_wars"

def json_dump_compact(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return str(obj)

def parse_planete(planete: Any) -> Optional[Tuple[int, int, float, float, float, float, float]]:
    try:
        if isinstance(planete, dict):
            pid = int(planete.get("id", planete.get("planet_id", 0)))
            owner = int(planete.get("owner", -1))
            x = float(planete.get("x", 0.0))
            y = float(planete.get("y", 0.0))
            radius = float(planete.get("radius", 0.0))
            ships = float(planete.get("ships", planete.get("ship_count", 0.0)))
            prod = float(planete.get("production", planete.get("growth", 0.0)))
            return pid, owner, x, y, radius, ships, prod
        if isinstance(planete, (list, tuple)) and len(planete) >= 7:
            return int(planete[0]), int(planete[1]), float(planete[2]), float(planete[3]), float(planete[4]), float(planete[5]), float(planete[6])
    except Exception:
        return None
    return None

def parse_flotte(flotte: Any) -> Optional[Tuple[int, int, float]]:
    try:
        if isinstance(flotte, dict):
            fid = int(flotte.get("id", 0))
            owner = int(flotte.get("owner", -1))
            ships = float(flotte.get("ships", flotte.get("ship_count", 0.0)))
            return fid, owner, ships
        if isinstance(flotte, (list, tuple)) and len(flotte) >= 7:
            return int(flotte[0]), int(flotte[1]), float(flotte[6])
    except Exception:
        return None
    return None

def extraire_observation_depuis_etape(etape: Any) -> Optional[Dict[str, Any]]:
    try:
        if isinstance(etape, list):
            for etat in etape:
                if isinstance(etat, dict):
                    obs = etat.get("observation")
                    if isinstance(obs, dict) and ("planets" in obs or "fleets" in obs):
                        return obs
                    if isinstance(obs, dict) and "remainingOverageTime" in obs:
                        # parfois obs imbrique ailleurs, on garde si pas mieux
                        return obs
        if isinstance(etape, dict):
            obs = etape.get("observation")
            if isinstance(obs, dict):
                return obs
    except Exception:
        return None
    return None

def compter_joueurs_actifs(obs: Dict[str, Any]) -> int:
    owners = set()
    for p in obs.get("planets", []) or []:
        pp = parse_planete(p)
        if pp and pp[1] >= 0 and pp[5] > 0:
            owners.add(pp[1])
    for fl in obs.get("fleets", []) or []:
        ff = parse_flotte(fl)
        if ff and ff[1] >= 0 and ff[2] > 0:
            owners.add(ff[1])
    return len(owners)

def snapshots_depuis_env_steps(match_id: str, mode: str, noms_agents: List[str], steps: Any, pas_snapshot: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    lignes_snap: List[Dict[str, Any]] = []
    lignes_actions: List[Dict[str, Any]] = []
    if not isinstance(steps, list):
        return lignes_snap, lignes_actions

    for idx_step, etape in enumerate(steps):
        if idx_step % max(1, pas_snapshot) == 0 or idx_step == len(steps) - 1:
            obs = extraire_observation_depuis_etape(etape)
            if isinstance(obs, dict):
                step_obs = int(obs.get("step", idx_step) or idx_step)
                stats: Dict[int, Dict[str, float]] = {}
                for joueur in range(len(noms_agents)):
                    stats[joueur] = {
                        "planetes": 0,
                        "ships_planetes": 0.0,
                        "production": 0.0,
                        "flottes": 0,
                        "ships_flottes": 0.0,
                    }
                neutres = 0
                ships_neutres = 0.0
                for p in obs.get("planets", []) or []:
                    pp = parse_planete(p)
                    if not pp:
                        continue
                    _, owner, _, _, _, ships, prod = pp
                    if owner >= 0 and owner in stats:
                        stats[owner]["planetes"] += 1
                        stats[owner]["ships_planetes"] += ships
                        stats[owner]["production"] += prod
                    elif owner < 0:
                        neutres += 1
                        ships_neutres += ships
                for fl in obs.get("fleets", []) or []:
                    ff = parse_flotte(fl)
                    if not ff:
                        continue
                    _, owner, ships = ff
                    if owner >= 0 and owner in stats:
                        stats[owner]["flottes"] += 1
                        stats[owner]["ships_flottes"] += ships
                actifs = compter_joueurs_actifs(obs)
                totaux = {j: stats[j]["ships_planetes"] + stats[j]["ships_flottes"] for j in stats}
                leader = max(totaux, key=totaux.get) if totaux else -1
                for joueur, nom in enumerate(noms_agents):
                    st = stats.get(joueur, {})
                    lignes_snap.append({
                        "match_id": match_id,
                        "mode": mode,
                        "step": step_obs,
                        "slot": joueur,
                        "agent": nom,
                        "actifs": actifs,
                        "est_leader": int(joueur == leader),
                        "planetes": int(st.get("planetes", 0)),
                        "ships_planetes": round(float(st.get("ships_planetes", 0.0)), 3),
                        "production": round(float(st.get("production", 0.0)), 3),
                        "flottes": int(st.get("flottes", 0)),
                        "ships_flottes": round(float(st.get("ships_flottes", 0.0)), 3),
                        "ships_total": round(float(totaux.get(joueur, 0.0)), 3),
                        "neutres": neutres,
                        "ships_neutres": round(ships_neutres, 3),
                    })
        # actions, si disponibles dans steps
        if isinstance(etape, list):
            for slot, etat in enumerate(etape):
                if isinstance(etat, dict) and "action" in etat:
                    action = etat.get("action")
                    nb_actions = 0
                    ships_envoyes = 0.0
                    try:
                        if isinstance(action, list):
                            nb_actions = len(action)
                            for a in action:
                                if isinstance(a, (list, tuple)) and len(a) >= 3:
                                    ships_envoyes += float(a[2])
                    except Exception:
                        pass
                    lignes_actions.append({
                        "match_id": match_id,
                        "mode": mode,
                        "step": idx_step,
                        "slot": slot,
                        "agent": noms_agents[slot] if slot < len(noms_agents) else f"slot_{slot}",
                        "nb_actions": nb_actions,
                        "ships_envoyes": round(ships_envoyes, 3),
                        "action_json": json_dump_compact(action)[:2000],
                    })
    return lignes_snap, lignes_actions

def worker_match(task: Dict[str, Any], output_path: str) -> None:
    """Execute un match dans un process isole. Ecrit un JSON resultat."""
    resultat: Dict[str, Any] = {
        "match_id": task["match_id"],
        "mode": task["mode"],
        "agents": task["agents"],
        "agent_paths": task["agent_paths"],
        "status": "UNKNOWN",
        "error": "",
        "rewards": [],
        "duration_sec": 0.0,
        "snapshots": [],
        "actions": [],
    }
    debut = time.time()
    try:
        # Import ici seulement, pour que le process parent reste propre.
        from kaggle_environments import make  # type: ignore

        seed = task.get("seed")
        configuration = {}
        if seed is not None:
            configuration["seed"] = int(seed)
        try:
            env = make(NOM_ENV, configuration=configuration, debug=False)
        except Exception:
            env = make(NOM_ENV, debug=False)

        # Chemins absolus de main.py. Kaggle env les importe comme agents fichier.
        agent_paths = [str(Path(p).resolve()) for p in task["agent_paths"]]
        env.run(agent_paths)
        rewards: List[Any] = []
        statuses: List[str] = []
        try:
            derniere = env.steps[-1]
            for etat in derniere:
                if isinstance(etat, dict):
                    rewards.append(etat.get("reward"))
                    statuses.append(str(etat.get("status", "")))
                else:
                    rewards.append(None)
                    statuses.append("")
        except Exception:
            rewards = []
            statuses = []

        snapshots, actions = snapshots_depuis_env_steps(
            task["match_id"], task["mode"], task["agents"], getattr(env, "steps", []), int(task.get("pas_snapshot", 25))
        )
        resultat.update({
            "status": "OK",
            "rewards": rewards,
            "agent_statuses": statuses,
            "duration_sec": round(time.time() - debut, 3),
            "snapshots": snapshots,
            "actions": actions,
        })
    except Exception as exc:
        resultat.update({
            "status": "ERROR",
            "error": str(exc) + "\n" + traceback.format_exc(),
            "duration_sec": round(time.time() - debut, 3),
        })
    try:
        Path(output_path).write_text(json.dumps(resultat, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

def construire_taches(agents: List[Dict[str, Any]], args: argparse.Namespace) -> List[Dict[str, Any]]:
    rng = random.Random(args.seed)
    taches: List[Dict[str, Any]] = []
    noms = [a["agent"] for a in agents]
    chemins = {a["agent"]: a["path"] for a in agents}

    def ajouter(mode: str, ordre: List[str], rep: int, tag: str) -> None:
        taches.append({
            "match_id": f"{mode}_{tag}_{rep:03d}_{len(taches):06d}",
            "mode": mode,
            "agents": ordre,
            "agent_paths": [chemins[n] for n in ordre],
            "seed": rng.randint(1, 2_000_000_000),
            "pas_snapshot": args.snapshot_step,
        })

    if "2p" in args.modes:
        for a, b in itertools.combinations(noms, 2):
            for rep in range(args.repeats_2p):
                ajouter("2p", [a, b], rep, "ab")
                if args.swap_positions:
                    ajouter("2p", [b, a], rep, "ba")

    if "3p" in args.modes and len(noms) >= 3:
        combos3 = list(itertools.combinations(noms, 3))
        rng.shuffle(combos3)
        max3 = min(args.max_3p, len(combos3) * max(1, args.repeats_3p))
        compteur = 0
        for combo in combos3:
            for rep in range(args.repeats_3p):
                ordre = list(combo)
                rng.shuffle(ordre)
                ajouter("3p", ordre, rep, "mix")
                compteur += 1
                if compteur >= max3:
                    break
            if compteur >= max3:
                break

    if "4p" in args.modes and len(noms) >= 4:
        combos4 = list(itertools.combinations(noms, 4))
        rng.shuffle(combos4)
        max4 = min(args.max_4p, len(combos4) * max(1, args.repeats_4p))
        compteur = 0
        for combo in combos4:
            for rep in range(args.repeats_4p):
                ordre = list(combo)
                rng.shuffle(ordre)
                ajouter("4p", ordre, rep, "mix")
                compteur += 1
                if compteur >= max4:
                    break
            if compteur >= max4:
                break

    rng.shuffle(taches)
    return taches

def resume_match_depuis_resultat(res: Dict[str, Any]) -> Dict[str, Any]:
    rewards = res.get("rewards") or []
    gagnants_slots: List[int] = []
    try:
        valeurs = [float(x) if x is not None else -9999.0 for x in rewards]
        maxv = max(valeurs) if valeurs else None
        if maxv is not None:
            gagnants_slots = [i for i, v in enumerate(valeurs) if abs(v - maxv) < 1e-9]
    except Exception:
        gagnants_slots = []
    agents = res.get("agents") or []
    gagnants_agents = [agents[i] for i in gagnants_slots if i < len(agents)]
    return {
        "match_id": res.get("match_id"),
        "mode": res.get("mode"),
        "status": res.get("status"),
        "duration_sec": res.get("duration_sec"),
        "agents_json": json_dump_compact(agents),
        "rewards_json": json_dump_compact(rewards),
        "winner_slots_json": json_dump_compact(gagnants_slots),
        "winner_agents_json": json_dump_compact(gagnants_agents),
        "error": (res.get("error") or "")[-2000:],
    }
