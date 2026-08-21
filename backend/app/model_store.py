"""
Loads and holds the trained model + metrics in memory for the API, and
provides the training routine used by both `train.py` and the automatic
first-run bootstrap in `main.py`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from .data import generate_dataset
from .features import FEATURE_LABELS, FEATURE_ORDER

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACT_DIR = os.path.join(BASE_DIR, "artifacts")
MODEL_PATH = os.path.join(ARTIFACT_DIR, "rf_model.joblib")
METRICS_PATH = os.path.join(ARTIFACT_DIR, "metrics.json")


def train_and_save(n_samples: int = 2000, seed: int = 42) -> dict:
    """Train the Random Forest, evaluate it and persist model + metrics."""
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    df = generate_dataset(n_samples=n_samples, seed=seed)
    X = df[FEATURE_ORDER].values
    y = df["pcos"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        random_state=seed,
        n_jobs=-1,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    importances = model.feature_importances_
    feature_importance = sorted(
        [
            {
                "feature": name,
                "label": FEATURE_LABELS[name],
                "importance": round(float(imp), 4),
            }
            for name, imp in zip(FEATURE_ORDER, importances)
        ],
        key=lambda d: d["importance"],
        reverse=True,
    )

    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": int(len(df)),
        "n_features": len(FEATURE_ORDER),
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred)), 4),
        "recall": round(float(recall_score(y_test, y_pred)), 4),
        "f1": round(float(f1_score(y_test, y_pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_proba)), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "feature_importance": feature_importance,
    }

    joblib.dump(model, MODEL_PATH)
    with open(METRICS_PATH, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)

    return metrics


class ModelStore:
    """Singleton-ish holder loaded once at startup."""

    def __init__(self) -> None:
        self.model = None
        self.metrics: dict | None = None

    def load_or_train(self) -> None:
        if os.path.exists(MODEL_PATH) and os.path.exists(METRICS_PATH):
            self.model = joblib.load(MODEL_PATH)
            with open(METRICS_PATH, encoding="utf-8") as fh:
                self.metrics = json.load(fh)
        else:
            self.metrics = train_and_save()
            self.model = joblib.load(MODEL_PATH)

    def predict_proba(self, feature_vector: list[float]) -> float:
        if self.model is None:
            raise RuntimeError("Model not loaded.")
        arr = np.array(feature_vector, dtype=float).reshape(1, -1)
        return float(self.model.predict_proba(arr)[0, 1])


store = ModelStore()
