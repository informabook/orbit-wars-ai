"""Replay-grouped linear training with tie-aware ROC AUC and JSON inference."""

import csv
import hashlib
import json

import numpy as np

METADATA = {"replay_id", "label", "weight"}


def sigmoid(values):
    return 1.0 / (1.0 + np.exp(-np.clip(values, -35, 35)))


def auc(labels, scores):
    labels, scores = np.asarray(labels), np.asarray(scores, dtype=float)
    if labels.ndim != 1 or scores.shape != labels.shape or not np.isfinite(scores).all():
        raise ValueError("AUC requires finite scores and one label per score")
    if set(labels.tolist()) != {0, 1}:
        raise ValueError("AUC requires both binary classes")
    order = np.argsort(scores, kind="stable")
    sorted_scores, sorted_labels = scores[order], labels[order]
    ends = np.r_[np.flatnonzero(sorted_scores[:-1] != sorted_scores[1:]) + 1, len(order)]
    starts = np.r_[0, ends[:-1]]
    positives = np.add.reduceat(sorted_labels.astype(int), starts)
    negatives = ends - starts - positives
    negative_before = np.cumsum(negatives) - negatives
    return float(np.sum(positives * (negative_before + negatives * 0.5)) /
                 (np.sum(positives) * np.sum(negatives)))


def grouped_split(groups, labels, seed, fraction=0.25):
    groups, labels = np.asarray(groups), np.asarray(labels)
    if groups.ndim != 1 or not len(groups) or labels.shape != groups.shape or any(not group for group in groups):
        raise ValueError("Each training row needs a nonempty replay identifier")
    unique, group_index = np.unique(groups, return_inverse=True)
    if not 0 < fraction < 1 or len(unique) < 2 or set(labels.tolist()) != {0, 1}:
        raise ValueError("Use a fraction in (0, 1), both classes and at least two replay groups")
    size = min(len(unique) - 1, max(1, round(len(unique) * fraction)))
    rng = np.random.default_rng(seed)
    for _ in range(128):
        selected = rng.choice(len(unique), size=size, replace=False)
        validation = np.isin(group_index, selected)
        if np.unique(labels[validation]).size == np.unique(labels[~validation]).size == 2:
            return ~validation, validation
    raise ValueError("Could not form class-complete, disjoint splits at this fraction. Add replay groups or change the fraction.")


def read_table(path, feature_names=None):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        if len(columns) != len(set(columns)) or any(not name for name in columns):
            raise ValueError("CSV needs a unique, nonempty column name for each field")
        features = [name for name in columns if name not in METADATA] if feature_names is None else feature_names
        if not features or not set(features).issubset(columns):
            raise ValueError("CSV is missing required feature columns")
        keys = features if feature_names is not None else features + ["replay_id", "label"]
        if not set(keys).issubset(columns):
            raise ValueError("Training mode requires replay_id and label")
        data = list(reader)
    if not data or any(None in row or any(value is None for value in row.values()) for row in data):
        raise ValueError("CSV is empty or has malformed rows")
    matrix = np.asarray([[float(row[f]) for f in features] for row in data])
    if not np.isfinite(matrix).all():
        raise ValueError("Features must be finite")
    return features, matrix, data


def train(path, seed, epochs=30, fraction=0.25):
    if not 1 <= epochs <= 1000:
        raise ValueError("epochs must be between one and one thousand")
    feature_names, matrix, rows = read_table(path)
    labels = np.array([float(row["label"]) for row in rows])
    groups = np.array([row["replay_id"].strip() for row in rows])
    weights = np.array([float(row.get("weight", "1")) for row in rows])
    if not np.isfinite(weights).all() or np.any(weights <= 0):
        raise ValueError("Weights must be finite and positive")
    train_mask, valid_mask = grouped_split(groups, labels, seed, fraction)
    mean, std = matrix[train_mask].mean(axis=0), matrix[train_mask].std(axis=0)
    std[std < 1e-8] = 1.0
    normalized = (matrix - mean) / std
    x, y = normalized[train_mask], labels[train_mask]
    w = weights[train_mask]
    w = w / w.mean()
    beta = np.zeros(matrix.shape[1])
    bias = 0.0
    history = []
    for epoch in range(1, epochs + 1):
        residual = w * (sigmoid(x @ beta + bias) - y)
        beta -= 0.055 * (x.T @ residual / len(y) + 0.0008 * beta)
        bias -= 0.055 * float(residual.mean())
        if not np.isfinite(beta).all() or not np.isfinite(bias):
            raise ValueError("Training diverged on the provided input")
        history.append({"epoch": epoch, "validation_auc": auc(labels[valid_mask], normalized[valid_mask] @ beta + bias)})
    return {"schema_version": 1, "implementation": "phase3_grouped_linear", "features": feature_names,
            "mean": mean.tolist(), "scale": std.tolist(), "weights": beta.tolist(), "bias": bias,
            "run": {"dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "seed": seed,
                    "validation_fraction": fraction, "train_rows": int(train_mask.sum()),
                    "validation_rows": int(valid_mask.sum()), "train_replays": np.unique(groups[train_mask]).size,
                    "validation_replays": np.unique(groups[valid_mask]).size, "history": history}}


def predict(model_path, input_path):
    model = json.loads(model_path.read_text(encoding="utf-8"))
    if model.get("schema_version") != 1 or model.get("implementation") != "phase3_grouped_linear":
        raise ValueError("Unsupported model format")
    features = model["features"]
    if not isinstance(features, list) or not features or any(not isinstance(f, str) or f in METADATA for f in features):
        raise ValueError("Invalid model feature names")
    if len(set(features)) != len(features):
        raise ValueError("Duplicate model features")
    _, matrix, _ = read_table(input_path, features)
    mean, scale, weights = (np.array(model[name], dtype=float) for name in ("mean", "scale", "weights"))
    bias = float(model["bias"])
    if any(arr.shape != (len(features),) or not np.isfinite(arr).all() for arr in (mean, scale, weights)):
        raise ValueError("Incompatible model dimensions or values")
    if np.any(scale <= 0) or not np.isfinite(bias):
        raise ValueError("Invalid model scaling or bias")
    logits = ((matrix - mean) / scale) @ weights + bias
    if not np.isfinite(logits).all():
        raise ValueError("Inference overflowed on the provided input")
    return sigmoid(logits).tolist()

