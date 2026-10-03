"""
PCOS training dataset.

Primary source: the extended PCOS clinical dataset (`PCOS_extended_dataset.csv`,
backend/data/) — 2,000 patient records following the same schema as the
original Kaggle "Polycystic ovary syndrome (PCOS)" dataset by
prasoonkottarathil (541 patients across 10 hospitals in Kerala, India).

Two of the app's existing inputs (mood_swings, family_history) aren't
recorded in that dataset. Rather than fabricate a relationship for them,
they're included as constant/zero columns here — the model learns no real
signal from them, but the assessment form still asks for them since
`recommendations.py`'s rule-based advice still uses the raw answers.

If the data file isn't present (e.g. a checkout without it), this falls
back to a fabricated synthetic dataset so the pipeline still runs end to
end — see `_generate_synthetic_dataset` below.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .features import FEATURE_ORDER

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "data", "PCOS_extended_dataset.csv")

# Not recorded in the real dataset — see module docstring.
_FEATURES_NOT_IN_REAL_DATA = ("mood_swings", "family_history")

_REAL_COLUMN_MAP = {
    "age": "Age (yrs)",
    "bmi": "BMI",
    "cycle_length": "Cycle length(days)",
    "cycle_irregular": "Cycle(R/I)",  # 2 = regular, 4/5 = irregular
    "weight_gain": "Weight gain(Y/N)",
    "hair_growth": "hair growth(Y/N)",
    "skin_darkening": "Skin darkening (Y/N)",
    "hair_loss": "Hair loss(Y/N)",
    "pimples": "Pimples(Y/N)",
    "fast_food": "Fast food (Y/N)",
    "exercise": "Reg.Exercise(Y/N)",
}


def _load_real_dataset() -> pd.DataFrame:
    raw = pd.read_csv(DATASET_PATH)
    raw = raw.drop(columns=[c for c in raw.columns if c.startswith("Unnamed")])
    raw.columns = [c.strip() for c in raw.columns]

    # A couple of known data-entry typos in this real-world dataset
    # (e.g. "1.99.", "a") -> coerce to numeric, fill with the column median
    # rather than drop the row.
    for col in raw.columns:
        if raw[col].dtype == object:
            raw[col] = pd.to_numeric(raw[col], errors="coerce")
    raw = raw.fillna(raw.median(numeric_only=True))

    df = pd.DataFrame()
    for feature, source_col in _REAL_COLUMN_MAP.items():
        if feature == "cycle_irregular":
            df[feature] = (raw[source_col] != 2).astype(int)
        else:
            df[feature] = raw[source_col]
    for feature in _FEATURES_NOT_IN_REAL_DATA:
        df[feature] = 0
    df["pcos"] = raw["PCOS (Y/N)"].astype(int)

    return df[FEATURE_ORDER + ["pcos"]]


def _generate_synthetic_dataset(n_samples: int = 2000, seed: int = 42) -> pd.DataFrame:
    """Fabricated fallback dataset, used only if the real data file (see
    DATASET_PATH) isn't present. Builds correlated features and derives the
    label from a latent risk score plus random noise, so the pattern is
    learnable but not trivially perfect."""
    rng = np.random.default_rng(seed)

    age = rng.integers(18, 45, size=n_samples)
    height_cm = rng.normal(160, 7, size=n_samples).clip(140, 185)
    weight_kg = rng.normal(64, 14, size=n_samples).clip(40, 120)
    bmi = (weight_kg / ((height_cm / 100) ** 2)).round(2)

    cycle_length = rng.normal(30, 6, size=n_samples).clip(21, 55).round().astype(int)
    irregular_p = 0.15 + 0.010 * (cycle_length - 28) + 0.010 * (bmi - 24)
    cycle_irregular = (rng.random(n_samples) < irregular_p.clip(0.05, 0.9)).astype(int)

    def bernoulli(base, bmi_coef=0.0):
        p = (base + bmi_coef * (bmi - 24)).clip(0.03, 0.95)
        return (rng.random(n_samples) < p).astype(int)

    weight_gain = bernoulli(0.30, 0.020)
    hair_growth = bernoulli(0.25, 0.015)
    skin_darkening = bernoulli(0.20, 0.015)
    hair_loss = bernoulli(0.25, 0.008)
    pimples = bernoulli(0.35, 0.006)
    fast_food = bernoulli(0.40, 0.010)
    exercise = bernoulli(0.45, -0.012)
    mood_swings = bernoulli(0.35, 0.004)
    family_history = bernoulli(0.20)

    score = (
        0.90 * cycle_irregular
        + 0.60 * weight_gain
        + 1.00 * hair_growth
        + 0.70 * skin_darkening
        + 0.45 * hair_loss
        + 0.40 * pimples
        + 0.35 * fast_food
        - 0.55 * exercise
        + 0.30 * mood_swings
        + 0.80 * family_history
        + 0.06 * (bmi - 25)
        + 0.02 * (cycle_length - 30)
        + rng.normal(0, 0.2, size=n_samples)
    )

    threshold = np.quantile(score, 0.60)
    pcos = (score > threshold).astype(int)

    df = pd.DataFrame(
        {
            "age": age,
            "bmi": bmi,
            "cycle_length": cycle_length,
            "cycle_irregular": cycle_irregular,
            "weight_gain": weight_gain,
            "hair_growth": hair_growth,
            "skin_darkening": skin_darkening,
            "hair_loss": hair_loss,
            "pimples": pimples,
            "fast_food": fast_food,
            "exercise": exercise,
            "mood_swings": mood_swings,
            "family_history": family_history,
            "pcos": pcos,
        }
    )
    return df[FEATURE_ORDER + ["pcos"]]


def generate_dataset(n_samples: int = 2000, seed: int = 42) -> pd.DataFrame:
    """Returns the training DataFrame: the real dataset if available,
    otherwise a fabricated fallback. `n_samples`/`seed` only apply to the
    fallback — the real dataset's size is fixed (2,000 patients)."""
    if os.path.exists(DATASET_PATH):
        return _load_real_dataset()
    return _generate_synthetic_dataset(n_samples=n_samples, seed=seed)


if __name__ == "__main__":
    data = generate_dataset()
    print(data.head())
    print("\nClass balance:\n", data["pcos"].value_counts(normalize=True))
