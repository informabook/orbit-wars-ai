"""V14 source excerpts from code cell 2. See PROVENANCE.md."""

import math
import random

from .ranker_v14 import FEATURES

SEED = 13
MAX_NEG_PAR_POS = 6

TAILLE_CARTE = 100.0
CENTRE_X = 50.0
CENTRE_Y = 50.0
RAYON_SOLEIL = 10.0
LIMITE_ORBITE = 50.0
VITESSE_MAX = 6.0
ETAPES_MAX = 500

def distance(ax, ay, bx, by):
    return math.hypot(float(ax) - float(bx), float(ay) - float(by))

def angle_vers(ax, ay, bx, by):
    return math.atan2(float(by) - float(ay), float(bx) - float(ax))

def norm_angle(a):
    a = float(a)
    while a <= -math.pi:
        a += 2.0 * math.pi
    while a > math.pi:
        a -= 2.0 * math.pi
    return a

def vitesse_flotte(n):
    n = max(1.0, float(n))
    ratio = max(0.0, min(1.0, math.log(n) / math.log(1000.0)))
    return 1.0 + (VITESSE_MAX - 1.0) * (ratio ** 1.5)

def dist_point_segment(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    den = vx * vx + vy * vy
    if den <= 1e-12:
        return math.hypot(px - ax, py - ay), 0.0
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / den))
    cx, cy = ax + t * vx, ay + t * vy
    return math.hypot(px - cx, py - cy), t

def log1p_pos(x):
    return math.log1p(max(0.0, float(x)))

def bord_normalise(p):
    x, y = float(p[2]), float(p[3])
    return max(0.0, min(1.0, min(x, y, 100.0 - x, 100.0 - y) / 50.0))

def index_cometes(obs):
    res = {}
    for groupe in obs.get("comets", []) or []:
        ids = groupe.get("planet_ids", [])
        for i, pid in enumerate(ids):
            res[int(pid)] = (groupe, i)
    return res

def position_future_planete(p, k, obs, init_by_id, comet_idx):
    pid = int(p[0])
    k = max(0.0, float(k))

    if pid in comet_idx:
        groupe, idx = comet_idx[pid]
        chemins = groupe.get("paths", [])
        path_index = int(round(float(groupe.get("path_index", 0)) + k))
        try:
            if 0 <= path_index < len(chemins[idx]):
                return float(chemins[idx][path_index][0]), float(chemins[idx][path_index][1])
        except Exception:
            pass
        return float(p[2]), float(p[3])

    init = init_by_id.get(pid)
    if init is None:
        return float(p[2]), float(p[3])

    ix, iy = float(init[2]), float(init[3])
    r_orb = distance(ix, iy, CENTRE_X, CENTRE_Y)
    if r_orb + float(p[4]) >= LIMITE_ORBITE:
        return float(p[2]), float(p[3])

    omega = float(obs.get("angular_velocity", 0.0) or 0.0)
    a = math.atan2(float(p[3]) - CENTRE_Y, float(p[2]) - CENTRE_X) + omega * k
    return CENTRE_X + r_orb * math.cos(a), CENTRE_Y + r_orb * math.sin(a)

def viser_approximatif(source, cible, ships, obs, planets, init_by_id, comet_idx):
    sx, sy = float(source[2]), float(source[3])
    spd = vitesse_flotte(ships)
    eta = distance(sx, sy, float(cible[2]), float(cible[3])) / max(1e-6, spd)
    angle = angle_vers(sx, sy, float(cible[2]), float(cible[3]))
    for _ in range(4):
        tx, ty = position_future_planete(cible, eta, obs, init_by_id, comet_idx)
        dist = max(0.0, distance(sx, sy, tx, ty) - float(source[4]) - 0.7 * float(cible[4]))
        eta = dist / max(1e-6, spd)
        angle = angle_vers(sx, sy, tx, ty)
    return angle, eta

def stats_joueurs(planets, fleets=None):
    ships, prod, count = {}, {}, {}
    for p in planets:
        owner = int(p[1])
        if owner >= 0:
            ships[owner] = ships.get(owner, 0.0) + float(p[5])
            prod[owner] = prod.get(owner, 0.0) + float(p[6])
            count[owner] = count.get(owner, 0) + 1
    if fleets:
        for f in fleets:
            owner = int(f[1])
            if owner >= 0:
                ships[owner] = ships.get(owner, 0.0) + float(f[6])
    return ships, prod, count

def besoin_approx(cible, eta, joueur):
    owner = int(cible[1])
    ships = float(cible[5])
    prod = float(cible[6])
    if owner == joueur:
        return 0
    if owner == -1:
        return int(math.ceil(ships + 1.2))
    return int(math.ceil(ships + prod * max(0.0, eta) + 2.2))


def quadrant_id_xy(x, y):
    x = float(x); y = float(y)
    return (1 if x >= 50.0 else 0) + (2 if y >= 50.0 else 0)

def angle_centre_features(p):
    dx = float(p[2]) - CENTRE_X
    dy = float(p[3]) - CENTRE_Y
    a = math.atan2(dy, dx)
    return math.sin(a), math.cos(a), a

def rayon_centre(p):
    return distance(float(p[2]), float(p[3]), CENTRE_X, CENTRE_Y)

def approx_incoming_to_point(x, y, fleets, joueur, horizon=95.0):
    my_ships = enemy_ships = 0.0
    my_count = enemy_count = 0.0
    my_eta = 999.0
    enemy_eta = 999.0
    for f in fleets:
        try:
            owner = int(f[1])
            fx, fy = float(f[2]), float(f[3])
            angle = float(f[4])
            ships = float(f[6])
            dist = distance(fx, fy, x, y)
            if dist <= 1e-6:
                continue
            direct = angle_vers(fx, fy, x, y)
            align = abs(norm_angle(direct - angle))
            if align > 0.42:
                continue
            eta = dist / max(0.2, vitesse_flotte(ships))
            if eta > horizon:
                continue
            poids_align = max(0.0, 1.0 - align / 0.42)
            eff = ships * poids_align
            if owner == joueur:
                my_ships += eff
                my_count += poids_align
                my_eta = min(my_eta, eta)
            elif owner >= 0:
                enemy_ships += eff
                enemy_count += poids_align
                enemy_eta = min(enemy_eta, eta)
        except Exception:
            continue
    if my_eta >= 999.0:
        my_eta = horizon
    if enemy_eta >= 999.0:
        enemy_eta = horizon
    return my_ships, enemy_ships, my_count, enemy_count, my_eta, enemy_eta

def nearest_distance_to_owner(p, planets, owner_filter):
    best = 999.0
    px, py = float(p[2]), float(p[3])
    for q in planets:
        try:
            if int(q[0]) == int(p[0]):
                continue
            if owner_filter(int(q[1])):
                best = min(best, distance(px, py, q[2], q[3]))
        except Exception:
            pass
    return best if best < 999.0 else 120.0

def local_density(p, planets, joueur, enemy=False, rayon=26.0):
    total = 0.0
    px, py = float(p[2]), float(p[3])
    for q in planets:
        try:
            if int(q[0]) == int(p[0]):
                continue
            owner = int(q[1])
            ok = (owner >= 0 and owner != joueur) if enemy else (owner == joueur)
            if not ok:
                continue
            d = distance(px, py, q[2], q[3])
            if d <= rayon:
                total += (float(q[5]) + 7.0 * float(q[6])) * max(0.0, 1.0 - d / rayon)
        except Exception:
            pass
    return total

def feature_candidat(obs, source, cible, ships_send=None, eta=None, need=None):
    planets = [list(p) for p in obs.get("planets", []) or []]
    fleets = [list(f) for f in obs.get("fleets", []) or []]
    joueur = int(obs.get("player", 0) or 0)
    step = int(obs.get("step", 0) or 0)

    init_by_id = {int(p[0]): list(p) for p in (obs.get("initial_planets", []) or [])}
    if not init_by_id:
        init_by_id = {int(p[0]): p for p in planets}

    comet_ids = set(int(x) for x in (obs.get("comet_planet_ids", []) or []))
    comet_idx = index_cometes(obs)

    if ships_send is None:
        ships_send = max(1, int(float(source[5]) // 2))
    if eta is None:
        _, eta = viser_approximatif(source, cible, ships_send, obs, planets, init_by_id, comet_idx)
    if need is None:
        need = besoin_approx(cible, eta, joueur)

    dist = distance(source[2], source[3], cible[2], cible[3])
    owner_reel = int(cible[1])
    is_neutral = 1.0 if owner_reel == -1 else 0.0
    is_enemy = 1.0 if owner_reel >= 0 and owner_reel != joueur else 0.0
    is_friend = 1.0 if owner_reel == joueur else 0.0
    is_comet = 1.0 if int(cible[0]) in comet_ids else 0.0
    source_is_comet = 1.0 if int(source[0]) in comet_ids else 0.0
    is_orbit = 1.0 if distance(cible[2], cible[3], CENTRE_X, CENTRE_Y) + float(cible[4]) < LIMITE_ORBITE else 0.0
    source_is_orbit = 1.0 if distance(source[2], source[3], CENTRE_X, CENTRE_Y) + float(source[4]) < LIMITE_ORBITE else 0.0
    target_static = 1.0 - is_orbit

    remaining = max(0.0, ETAPES_MAX - step - float(eta))
    ships_scores, prod_scores, planetes_scores = stats_joueurs(planets, fleets)
    total_my = ships_scores.get(joueur, 0.0)
    prod_my = prod_scores.get(joueur, 0.0)
    enemy_prod = max([v for k, v in prod_scores.items() if k != joueur] or [0.0])
    enemy_ships = max([v for k, v in ships_scores.items() if k != joueur] or [0.0])

    target_strength = ships_scores.get(owner_reel, 0.0) + 9.0 * prod_scores.get(owner_reel, 0.0) if owner_reel >= 0 else 0.0
    leader_strength = max([ships_scores.get(k, 0.0) + 9.0 * prod_scores.get(k, 0.0) for k in ships_scores] or [0.0])
    leader_target = 1.0 if owner_reel >= 0 and owner_reel != joueur and abs(target_strength - leader_strength) < 1e-6 else 0.0

    sx, sy = float(source[2]), float(source[3])
    tx, ty = float(cible[2]), float(cible[3])
    sun_dist, _ = dist_point_segment(CENTRE_X, CENTRE_Y, sx, sy, tx, ty)
    central_cross = max(0.0, min(1.0, (RAYON_SOLEIL + 8.0 - sun_dist) / 18.0))
    same_quad = 1.0 if ((sx >= 50.0) == (tx >= 50.0) and (sy >= 50.0) == (ty >= 50.0)) else 0.0

    need_f = max(0.0, float(need))
    eta_f = max(0.0, float(eta))
    ships_send_f = max(1.0, float(ships_send))
    ships_source = max(0.0, float(source[5]))
    ships_cible = max(0.0, float(cible[5]))
    prod_source = max(0.0, float(source[6]))
    prod_cible = max(0.0, float(cible[6]))

    roi = (prod_cible * min(remaining, 180.0) + 0.15 * ships_cible) / max(2.0, need_f + 0.35 * eta_f)
    cost_ratio = need_f / max(1.0, ships_source)
    need_vs_target = need_f / max(1.0, ships_cible + prod_cible * max(0.0, eta_f))
    prod_per_need = prod_cible / max(1.0, need_f)
    eta_per_prod = eta_f / max(1.0, prod_cible)
    target_weak = 1.0 if ships_cible <= 8.0 + 1.5 * prod_cible else 0.0
    source_rich = 1.0 if ships_source >= 22.0 + 4.0 * prod_source else 0.0

    source_after = max(0.0, ships_source - ships_send_f)
    send_frac = ships_send_f / max(1.0, ships_source)
    send_vs_need = ships_send_f / max(1.0, need_f)
    overkill_ratio = max(0.0, ships_send_f - need_f) / max(1.0, need_f)
    source_spare_prod_ratio = source_after / max(1.0, 5.0 + 3.0 * prod_source)

    step_norm = step / 500.0
    turns_left_norm = max(0.0, 500.0 - step) / 500.0
    source_r = rayon_centre(source)
    target_r = rayon_centre(cible)
    s_sin, s_cos, s_ang = angle_centre_features(source)
    t_sin, t_cos, t_ang = angle_centre_features(cible)
    angle_delta_center = abs(norm_angle(s_ang - t_ang)) / math.pi
    source_quad = quadrant_id_xy(sx, sy) / 3.0
    target_quad = quadrant_id_xy(tx, ty) / 3.0

    total_planets = max(1, len(planets))
    my_planets = sum(1 for p in planets if int(p[1]) == joueur)
    enemy_planets = max([sum(1 for p in planets if int(p[1]) == k) for k in set(int(p[1]) for p in planets if int(p[1]) >= 0 and int(p[1]) != joueur)] or [0])
    neutral_planets = sum(1 for p in planets if int(p[1]) == -1)
    owned_planets = sum(1 for p in planets if int(p[1]) >= 0)

    max_prod = max([float(p[6]) for p in planets] or [1.0])
    max_ships = max([float(p[5]) for p in planets] or [1.0])
    target_prod_rank = prod_cible / max(1.0, max_prod)
    target_ship_rank = ships_cible / max(1.0, max_ships)
    target_roi_rank_like = (prod_cible * 12.0 + (1.0 if owner_reel >= 0 else 0.0) * 3.0) / max(3.0, ships_cible + 0.35 * dist)

    inc_my_t, inc_enemy_t, inc_my_c_t, inc_enemy_c_t, inc_my_eta_t, inc_enemy_eta_t = approx_incoming_to_point(tx, ty, fleets, joueur)
    inc_my_s, inc_enemy_s, inc_my_c_s, inc_enemy_c_s, inc_my_eta_s, inc_enemy_eta_s = approx_incoming_to_point(sx, sy, fleets, joueur)
    source_under_threat = 1.0 if inc_enemy_s > max(3.0, source_after + prod_source * max(0.0, inc_enemy_eta_s)) else 0.0
    source_reinforced = 1.0 if inc_my_s > 1.0 else 0.0

    nearest_my_target = nearest_distance_to_owner(cible, planets, lambda o: o == joueur)
    nearest_enemy_target = nearest_distance_to_owner(cible, planets, lambda o: o >= 0 and o != joueur)
    nearest_enemy_source = nearest_distance_to_owner(source, planets, lambda o: o >= 0 and o != joueur)
    frontline_source = max(0.0, min(1.0, (35.0 - nearest_enemy_source) / 35.0))
    frontline_target = max(0.0, min(1.0, (35.0 - nearest_enemy_target) / 35.0))

    prod_distance_ratio = prod_cible / max(1.0, dist / 8.0)
    need_eta_product = (need_f / 80.0) * (eta_f / 80.0)
    cost_eta_product = cost_ratio * (eta_f / 80.0)
    distance_prod_ratio = (dist / 140.0) / max(0.2, prod_cible)

    leader_prod = max([prod_scores.get(k, 0.0) for k in prod_scores if k != joueur] or [0.0])
    leader_ships = max([ships_scores.get(k, 0.0) for k in ships_scores if k != joueur] or [0.0])
    leader_prod_target = 1.0 if owner_reel >= 0 and owner_reel != joueur and abs(prod_scores.get(owner_reel, 0.0) - leader_prod) < 1e-6 else 0.0
    leader_ships_target = 1.0 if owner_reel >= 0 and owner_reel != joueur and abs(ships_scores.get(owner_reel, 0.0) - leader_ships) < 1e-6 else 0.0

    active_owners = set(int(p[1]) for p in planets if int(p[1]) >= 0)
    nb_hint = max(2, len(active_owners))
    two_player_hint = 1.0 if nb_hint <= 2 else 0.0
    four_player_hint = 1.0 if nb_hint >= 4 else 0.0

    comet_spawn_window = 1.0 if any(abs(step - s) <= 9 for s in [50, 150, 250, 350, 450]) else 0.0
    target_close_to_sun = max(0.0, min(1.0, (28.0 - target_r) / 28.0))
    source_close_to_sun = max(0.0, min(1.0, (28.0 - source_r) / 28.0))
    edge_to_edge = 1.0 if bord_normalise(source) < 0.18 and bord_normalise(cible) < 0.18 else 0.0
    ally_density_t = local_density(cible, planets, joueur, enemy=False) / 700.0
    enemy_density_t = local_density(cible, planets, joueur, enemy=True) / 700.0
    future_target_ships = max(0.0, ships_cible + prod_cible * eta_f + inc_my_t - inc_enemy_t)
    future_need_ratio = need_f / max(1.0, future_target_ships)
    capture_payoff = (prod_cible * min(220.0, remaining) + 0.25 * ships_cible - need_f - 0.22 * eta_f) / 120.0

    x = [
        log1p_pos(ships_source) / 5.0,
        prod_source / 5.0,
        log1p_pos(ships_cible) / 5.0,
        prod_cible / 5.0,
        dist / 140.0,
        eta_f / 80.0,
        log1p_pos(need_f) / 5.0,
        cost_ratio,
        roi / 12.0,
        remaining / 500.0,
        is_neutral,
        is_enemy,
        is_friend,
        is_comet,
        is_orbit,
        1.0 if step < 60 else 0.0,
        1.0 if 60 <= step < 280 else 0.0,
        1.0 if step >= 280 else 0.0,
        prod_my / 90.0,
        enemy_prod / 90.0,
        (prod_my - enemy_prod) / 90.0,
        total_my / 1600.0,
        enemy_ships / 1600.0,
        (total_my - enemy_ships) / 1600.0,
        target_strength / 1800.0,
        leader_target,
        bord_normalise(source),
        bord_normalise(cible),
        central_cross,
        same_quad,
        need_vs_target,
        prod_per_need,
        eta_per_prod / 40.0,
        target_weak,
        source_rich,
        log1p_pos(ships_send_f) / 5.0,
        send_frac,
        send_vs_need,
        overkill_ratio,
        log1p_pos(source_after) / 5.0,
        source_after / max(1.0, ships_source),
        source_spare_prod_ratio,
        step_norm,
        turns_left_norm,
        1.0 if step < 25 else 0.0,
        1.0 if step < 90 else 0.0,
        1.0 if step > 400 else 0.0,
        sx / 100.0,
        sy / 100.0,
        tx / 100.0,
        ty / 100.0,
        source_r / 70.8,
        target_r / 70.8,
        (target_r - source_r) / 70.8,
        s_sin,
        s_cos,
        t_sin,
        t_cos,
        angle_delta_center,
        source_quad,
        target_quad,
        source_is_orbit,
        source_is_comet,
        target_static,
        my_planets / total_planets,
        enemy_planets / total_planets,
        (my_planets - enemy_planets) / total_planets,
        neutral_planets / total_planets,
        owned_planets / total_planets,
        target_prod_rank,
        target_ship_rank,
        target_roi_rank_like,
        inc_my_t / 180.0,
        inc_enemy_t / 180.0,
        (inc_my_t - inc_enemy_t) / 180.0,
        inc_my_c_t / 8.0,
        inc_enemy_c_t / 8.0,
        inc_my_eta_t / 95.0,
        inc_enemy_eta_t / 95.0,
        inc_enemy_s / 180.0,
        source_under_threat,
        source_reinforced,
        nearest_my_target / 140.0,
        nearest_enemy_target / 140.0,
        nearest_enemy_source / 140.0,
        frontline_source,
        frontline_target,
        prod_distance_ratio / 8.0,
        need_eta_product,
        cost_eta_product,
        distance_prod_ratio,
        leader_prod_target,
        leader_ships_target,
        (prod_scores.get(owner_reel, 0.0) if owner_reel >= 0 else 0.0) / 90.0,
        (planetes_scores.get(owner_reel, 0.0) if owner_reel >= 0 else 0.0) / total_planets,
        two_player_hint,
        four_player_hint,
        comet_spawn_window,
        target_close_to_sun,
        source_close_to_sun,
        edge_to_edge,
        ally_density_t,
        enemy_density_t,
        future_target_ships / 220.0,
        future_need_ratio,
        capture_payoff,
    ]
    if len(x) != len(FEATURES):
        raise RuntimeError(f"Nombre de features incoherent: {len(x)} vs {len(FEATURES)}")
    return [float(v) if math.isfinite(float(v)) else 0.0 for v in x]
def inferer_cible(obs, source, angle, ships):
    planets = [list(p) for p in obs.get("planets", []) or []]
    init_by_id = {int(p[0]): list(p) for p in (obs.get("initial_planets", []) or [])}
    if not init_by_id:
        init_by_id = {int(p[0]): p for p in planets}
    comet_idx = index_cometes(obs)

    meilleur = None
    for cible in planets:
        if int(cible[0]) == int(source[0]):
            continue
        a, eta = viser_approximatif(source, cible, ships, obs, planets, init_by_id, comet_idx)
        diff = abs(norm_angle(float(angle) - a))
        dist = distance(source[2], source[3], cible[2], cible[3])
        score = diff + 0.002 * dist + 0.001 * eta
        if meilleur is None or score < meilleur[0]:
            meilleur = (score, diff, eta, cible)

    if meilleur and meilleur[1] < 0.55:
        return meilleur[3], meilleur[2], meilleur[1]
    return None, None, None

def traiter_un_replay(args):
    nom, data = args
    rng = random.Random((hash(nom) ^ SEED) & 0xffffffff)
    X, y, poids = [], [], []
    stats = {"replay": nom, "actions_lues": 0, "actions_ciblees": 0, "positifs": 0, "negatifs": 0}
    steps = data.get("steps", [])
    rewards = data.get("rewards", [])
    if not steps or not rewards:
        return X, y, poids, stats
    rewards_num = [r if isinstance(r, (int, float)) else -999 for r in rewards]
    meilleur_reward = max(rewards_num)
    gagnants = [i for i, r in enumerate(rewards_num) if r == meilleur_reward]
    stats["gagnants"] = gagnants
    stats["rewards"] = rewards_num
    if len(gagnants) != 1:
        return X, y, poids, stats
    gagnant = gagnants[0]
    if gagnant >= len(steps[0]):
        return X, y, poids, stats

    marge = 0.0
    try:
        tries = sorted(rewards_num, reverse=True)
        marge = float(tries[0] - tries[1]) if len(tries) > 1 else 1.0
    except Exception:
        marge = 0.0
    qualite = 1.0 + min(1.0, max(0.0, marge) * 0.35)
    longueur = len(steps)
    if longueur < 180:
        qualite += 0.25

    for t in range(1, len(steps)):
        try:
            obs = steps[t - 1][gagnant].get("observation", {})
            action = steps[t][gagnant].get("action", []) or []
            if not action:
                continue
            planets = [list(p) for p in obs.get("planets", []) or []]
            by_id = {int(p[0]): p for p in planets}
            joueur = int(obs.get("player", gagnant) or gagnant)
            targets = [p for p in planets if int(p[1]) != joueur]
            if not targets:
                continue
            init_by_id = {int(p[0]): list(p) for p in (obs.get("initial_planets", []) or [])}
            if not init_by_id:
                init_by_id = {int(p[0]): p for p in planets}
            comet_idx = index_cometes(obs)

            for move in action:
                stats["actions_lues"] += 1
                if len(move) < 3:
                    continue
                sid, angle, ships = int(move[0]), float(move[1]), int(move[2])
                if sid not in by_id or ships <= 0:
                    continue
                source = by_id[sid]
                cible, eta, diff = inferer_cible(obs, source, angle, ships)
                if cible is None or int(cible[1]) == joueur:
                    continue
                stats["actions_ciblees"] += 1
                besoin = besoin_approx(cible, eta, joueur)
                X.append(feature_candidat(obs, source, cible, ships, eta, besoin))
                y.append(1.0)
                early_bonus = 1.35 if int(obs.get("step", 0) or 0) < 80 else 1.0
                high_prod_bonus = 1.0 + 0.12 * float(cible[6])
                poids.append(2.45 * qualite * early_bonus * high_prod_bonus)
                stats["positifs"] += 1

                negatifs = []
                for autre in targets:
                    if int(autre[0]) == int(cible[0]):
                        continue
                    try:
                        ships_test = max(2, min(int(float(source[5])), int(float(autre[5]) + float(autre[6]) * 4.0 + 5)))
                        _, eta_test = viser_approximatif(source, autre, ships_test, obs, planets, init_by_id, comet_idx)
                        besoin_test = besoin_approx(autre, eta_test, joueur)
                        # hard negatives plausibles, proches ou rentables, sinon le modele apprend trop facile.
                        plausible = besoin_test <= max(3, float(source[5]) * 1.65) or distance(source[2], source[3], autre[2], autre[3]) < 34.0 or float(autre[6]) >= 4.0
                        if plausible:
                            # heuristique simple pour prendre surtout les alternatives tentantes.
                            neg_score = 7.0 * float(autre[6]) - 0.4 * besoin_test - 0.18 * eta_test - 0.02 * distance(source[2], source[3], autre[2], autre[3])
                            negatifs.append((neg_score, autre, eta_test, besoin_test, ships_test))
                    except Exception:
                        pass
                negatifs.sort(key=lambda z: z[0], reverse=True)
                for neg_score, autre, eta_test, besoin_test, ships_test in negatifs[:MAX_NEG_PAR_POS]:
                    X.append(feature_candidat(obs, source, autre, ships_test, eta_test, besoin_test))
                    y.append(0.0)
                    poids.append(0.48)
                    stats["negatifs"] += 1
        except Exception:
            continue
    return X, y, poids, stats
