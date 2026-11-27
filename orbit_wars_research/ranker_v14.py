"""Reviewed excerpt from V14 notebook code cell 2 (zero-based). See PROVENANCE.md for source and scope."""

import time

import numpy as np

VERSION = 'V14_fast_cpu_ranker_topk_selfplay'
VALIDATION_FRAC = 0.2
SEED = 13
MAX_EPOCHS = 2600
MIN_EPOCHS = 500
PATIENCE_CHECKS = 42
CHECK_EVERY = 20
PRINT_EVERY = 100
BATCH_SIZE = 16384
WEIGHT_DECAY = 0.0008
MIN_DELTA_AUC = 6e-05
PLATEAU_LR_PATIENCE = 16
PLATEAU_LR_FACTOR = 0.7

FEATURES = [
    "source_ships_log",
    "source_prod",
    "target_ships_log",
    "target_prod",
    "distance",
    "eta",
    "need_log",
    "cost_ratio",
    "roi",
    "remaining_frac",
    "is_neutral",
    "is_enemy",
    "is_friend",
    "is_comet",
    "is_orbit",
    "step_early",
    "step_mid",
    "step_late",
    "my_prod_norm",
    "enemy_prod_norm",
    "prod_diff_norm",
    "my_ships_norm",
    "enemy_ships_norm",
    "ship_diff_norm",
    "target_owner_strength_norm",
    "leader_target",
    "source_edge",
    "target_edge",
    "central_cross_risk",
    "same_quadrant",
    "need_vs_target",
    "prod_per_need",
    "eta_per_prod",
    "target_weak",
    "source_rich",
    "ships_send_log",
    "send_frac",
    "send_vs_need",
    "overkill_ratio",
    "source_after_send_log",
    "source_after_send_ratio",
    "source_spare_prod_ratio",
    "step_norm",
    "turns_left_norm",
    "step_very_early",
    "step_opening",
    "step_endgame",
    "source_x",
    "source_y",
    "target_x",
    "target_y",
    "source_center_dist",
    "target_center_dist",
    "radial_delta",
    "source_angle_sin",
    "source_angle_cos",
    "target_angle_sin",
    "target_angle_cos",
    "angle_delta_center",
    "source_quadrant",
    "target_quadrant",
    "source_is_orbit",
    "source_is_comet",
    "target_static",
    "my_planet_count_norm",
    "enemy_planet_count_norm",
    "planet_count_diff_norm",
    "neutral_planet_frac",
    "owned_planet_frac",
    "target_prod_rank",
    "target_ship_rank",
    "target_roi_rank_like",
    "incoming_my_target",
    "incoming_enemy_target",
    "incoming_net_target",
    "incoming_my_count",
    "incoming_enemy_count",
    "incoming_my_eta_norm",
    "incoming_enemy_eta_norm",
    "incoming_enemy_source",
    "source_under_threat_hint",
    "source_reinforced_hint",
    "nearest_my_to_target",
    "nearest_enemy_to_target",
    "nearest_enemy_to_source",
    "frontline_source",
    "frontline_target",
    "prod_distance_ratio",
    "need_eta_product",
    "cost_eta_product",
    "distance_prod_ratio",
    "leader_prod_target",
    "leader_ships_target",
    "target_owner_prod_norm",
    "target_owner_planets_norm",
    "two_player_hint",
    "four_player_hint",
    "comet_spawn_window_hint",
    "target_close_to_sun",
    "source_close_to_sun",
    "edge_to_edge",
    "ally_density_target",
    "enemy_density_target",
    "future_target_ships_norm",
    "future_need_ratio",
    "capture_payoff"
]

def sigmoid_np(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35.0, 35.0)))

def auc_approx_scores(pred, y):
    y = np.asarray(y)
    pred = np.asarray(pred)
    pos = y > 0.5
    neg = ~pos
    if pos.sum() == 0 or neg.sum() == 0:
        return 0.5
    order = np.argsort(pred)
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(len(pred), dtype=np.float64)
    return float((ranks[pos].sum() - pos.sum() * (pos.sum() - 1) / 2.0) / max(1.0, float(pos.sum() * neg.sum())))

def accuracy_scores(pred, y, seuil=0.5):
    return float(((pred > seuil) == (y > 0.5)).mean())

def bce_from_pred(pred, y, sw):
    eps = 1e-9
    return float(-np.mean(sw * (y * np.log(pred + eps) + (1.0 - y) * np.log(1.0 - pred + eps))))

def entrainer_ranker_numpy_lineaire(X, y, sample_weight):
    debut = time.time()
    X = X.astype(np.float32)
    y = y.astype(np.float32)
    sw = sample_weight.astype(np.float32)
    sw = sw / (sw.mean() + 1e-9)
    rng = np.random.default_rng(SEED)
    idx = rng.permutation(len(y))
    n_valid = max(1, int(len(idx) * VALIDATION_FRAC))
    valid_idx = idx[:n_valid]
    train_idx = idx[n_valid:]
    mean = X[train_idx].mean(axis=0).astype(np.float32)
    std = (X[train_idx].std(axis=0) + 1e-6).astype(np.float32)
    Xn = ((X - mean) / std).astype(np.float32)
    theta = np.zeros(Xn.shape[1], dtype=np.float32)
    bias = 0.0
    lr = 0.055
    best = {"val_auc": -1, "val_loss": 999, "epoch": 0, "theta": theta.copy(), "bias": bias}
    no_imp = 0
    hist = []
    for ep in range(1, MAX_EPOCHS + 1):
        rng.shuffle(train_idx)
        for start in range(0, len(train_idx), BATCH_SIZE):
            b = train_idx[start:start+BATCH_SIZE]
            xb = Xn[b]
            pred = sigmoid_np(xb.dot(theta) + bias).astype(np.float32)
            err = ((pred - y[b]) * sw[b]).astype(np.float32)
            theta -= lr * (xb.T.dot(err) / max(1, len(b)) + WEIGHT_DECAY * theta)
            bias -= lr * float(err.mean())
        if ep % CHECK_EVERY == 0 or ep == 1:
            p_val = sigmoid_np(Xn[valid_idx].dot(theta) + bias)
            p_train = sigmoid_np(Xn[train_idx[:min(25000, len(train_idx))]].dot(theta) + bias)
            val_auc = auc_approx_scores(p_val, y[valid_idx])
            val_loss = bce_from_pred(p_val, y[valid_idx], sw[valid_idx])
            item = {"epoch": ep, "train_auc": auc_approx_scores(p_train, y[train_idx[:min(25000, len(train_idx))]]), "val_auc": val_auc, "val_loss": val_loss, "train_loss": bce_from_pred(p_train, y[train_idx[:min(25000, len(train_idx))]], sw[train_idx[:min(25000, len(train_idx))]]), "val_acc": accuracy_scores(p_val, y[valid_idx]), "lr": lr}
            hist.append(item)
            improved = val_auc > best["val_auc"] + MIN_DELTA_AUC or (abs(val_auc - best["val_auc"]) <= MIN_DELTA_AUC and val_loss < best["val_loss"])
            if improved:
                best.update({"val_auc": val_auc, "val_loss": val_loss, "epoch": ep, "theta": theta.copy(), "bias": bias})
                no_imp = 0
            else:
                no_imp += 1
            if ep == 1 or ep % PRINT_EVERY == 0:
                print(f"epoch {ep:04d}/{MAX_EPOCHS} | val_auc={val_auc:.4f} val_loss={val_loss:.4f} | best_ep={best['epoch']} best_auc={best['val_auc']:.4f}")
            if no_imp and no_imp % PLATEAU_LR_PATIENCE == 0:
                lr *= PLATEAU_LR_FACTOR
            if ep >= MIN_EPOCHS and no_imp >= PATIENCE_CHECKS:
                print("Early stopping:", ep, "best_epoch:", best["epoch"])
                break
    theta = best["theta"]; bias = float(best["bias"])
    pred_all = sigmoid_np(Xn.dot(theta) + bias)
    return {
        "model_type": "linear",
        "features": FEATURES,
        "mean": mean.tolist(), "std": std.tolist(),
        "weights": theta.tolist(), "bias": bias,
        "coef": 3.05,
        "version": VERSION,
        "metrics": {"n": int(len(y)), "positives": int((y>0.5).sum()), "negatives": int((y<=0.5).sum()), "accuracy_05": accuracy_scores(pred_all, y), "auc_approx": auc_approx_scores(pred_all, y), "best_val_auc": float(best["val_auc"]), "best_val_loss": float(best["val_loss"]), "best_epoch": int(best["epoch"]), "epochs_ran": int(hist[-1]["epoch"] if hist else 0), "elapsed_seconds": float(time.time()-debut), "trainer": "numpy_linear"},
        "history": hist,
        "diagnostics": {"pred_pos_sample": pred_all[y>0.5][:5000].tolist(), "pred_neg_sample": pred_all[y<=0.5][:5000].tolist()},
    }
