"""
Demo-only script (not wired into the live app): trains two Random Forest
variants on the real Kaggle PCOS dataset (backend/data/PCOS_data_without_infertility.xlsx)
and reports their metrics side by side with the current synthetic-data model.

  Version A - overlapping features: the same 13 inputs app/features.py already
              asks for, but trained on real patient data instead of fabricated
              correlations. Two of those 13 (mood_swings, family_history) don't
              exist in this dataset and are excluded here.
  Version B - full clinical dataset: every usable column (hormone levels,
              follicle counts, blood pressure, etc.), ~38 features.

Run: backend/.venv/Scripts/python.exe backend/scripts/demo_kaggle_models.py
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX_PATH = os.path.join(BASE_DIR, "data", "PCOS_data_without_infertility.xlsx")
SEED = 42


def load_raw() -> pd.DataFrame:
    df = pd.read_excel(XLSX_PATH, sheet_name="Full_new")
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])
    df.columns = [c.strip() for c in df.columns]
    # A couple of known data-entry typos in this real-world dataset
    # ("1.99." and "a") -> coerce to numeric, NaN on failure, then fill
    # with the column median so a couple of bad cells don't lose rows.
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.fillna(df.median(numeric_only=True))
    return df


def evaluate(X: np.ndarray, y: np.ndarray, label: str) -> dict:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )
    model = RandomForestClassifier(
        n_estimators=300, min_samples_leaf=2, random_state=SEED,
        n_jobs=-1, class_weight="balanced",
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_proba),
    }
    print(f"\n=== {label} ===")
    print(f"  train/test sizes: {len(X_train)}/{len(X_test)}  (n_features={X.shape[1]})")
    for k, v in metrics.items():
        print(f"  {k:10s}: {v:.4f}")
    importances = sorted(
        zip(feature_names_for(X), model.feature_importances_),
        key=lambda t: t[1], reverse=True,
    )[:8]
    print("  top features:")
    for name, imp in importances:
        print(f"    {name:30s} {imp:.4f}")
    return metrics


_current_feature_names: list[str] = []


def feature_names_for(X):
    return _current_feature_names


def set_feature_names(names):
    global _current_feature_names
    _current_feature_names = names


def main():
    df = load_raw()
    y = df["PCOS (Y/N)"].astype(int).values

    # ---- Version A: overlapping with the app's existing 13 inputs -------
    col_map = {
        "age": "Age (yrs)",
        "bmi": "BMI",
        "cycle_length": "Cycle length(days)",
        "cycle_irregular": "Cycle(R/I)",          # 2=regular, else irregular
        "weight_gain": "Weight gain(Y/N)",
        "hair_growth": "hair growth(Y/N)",
        "skin_darkening": "Skin darkening (Y/N)",
        "hair_loss": "Hair loss(Y/N)",
        "pimples": "Pimples(Y/N)",
        "fast_food": "Fast food (Y/N)",
        "exercise": "Reg.Exercise(Y/N)",
        # mood_swings, family_history: not present in this dataset.
    }
    a = pd.DataFrame()
    for feat, src in col_map.items():
        if feat == "cycle_irregular":
            a[feat] = (df[src] != 2).astype(int)
        else:
            a[feat] = df[src]
    set_feature_names(list(a.columns))
    evaluate(a.values, y, "Version A - overlapping features (real data, 11/13 inputs)")

    # ---- Version B: full clinical dataset --------------------------------
    drop_cols = {"Sl. No", "Patient File No.", "PCOS (Y/N)"}
    b = df.drop(columns=[c for c in drop_cols if c in df.columns])
    set_feature_names(list(b.columns))
    evaluate(b.values, y, "Version B - full clinical dataset (real data, all features)")

    print(
        "\nFor reference, the current live app's synthetic-data model scores "
        "~90.75% accuracy on its own fabricated 2000-sample dataset (not "
        "comparable 1:1 since it's a different, much larger, and fabricated "
        "dataset - shown only for context)."
    )


if __name__ == "__main__":
    main()
