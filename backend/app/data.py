"""
Synthetic PCOS dataset generator.

A real deployment should replace this with a validated clinical dataset
(e.g. the public Kaggle "PCOS" dataset). Because no such file ships with
this project, we generate a realistic, internally-consistent synthetic
dataset so the full ML pipeline (training -> evaluation -> prediction)
runs end to end and the admin dashboard has meaningful numbers to show.

The generator builds correlated features and derives the label from a
latent risk score plus random noise, so the pattern is learnable but not
trivially perfect. The reported accuracy therefore reflects a genuine
train/test split rather than a hard-coded figure.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .features import FEATURE_ORDER


def generate_dataset(n_samples: int = 2000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # --- Base demographics ---------------------------------------------
    age = rng.integers(18, 45, size=n_samples)
    height_cm = rng.normal(160, 7, size=n_samples).clip(140, 185)
    weight_kg = rng.normal(64, 14, size=n_samples).clip(40, 120)
    bmi = (weight_kg / ((height_cm / 100) ** 2)).round(2)

    # --- Menstrual features --------------------------------------------
    cycle_length = rng.normal(30, 6, size=n_samples).clip(21, 55).round().astype(int)
    # Irregularity is more likely with longer cycles and higher BMI.
    irregular_p = 0.15 + 0.010 * (cycle_length - 28) + 0.010 * (bmi - 24)
    cycle_irregular = (rng.random(n_samples) < irregular_p.clip(0.05, 0.9)).astype(int)

    # --- Symptom / lifestyle features (correlated with BMI) ------------
    def bernoulli(base, bmi_coef=0.0):
        p = (base + bmi_coef * (bmi - 24)).clip(0.03, 0.95)
        return (rng.random(n_samples) < p).astype(int)

    weight_gain = bernoulli(0.30, 0.020)
    hair_growth = bernoulli(0.25, 0.015)
    skin_darkening = bernoulli(0.20, 0.015)
    hair_loss = bernoulli(0.25, 0.008)
    pimples = bernoulli(0.35, 0.006)
    fast_food = bernoulli(0.40, 0.010)
    exercise = bernoulli(0.45, -0.012)  # heavier -> less likely to exercise
    mood_swings = bernoulli(0.35, 0.004)
    family_history = bernoulli(0.20)

    # --- Latent risk score ---------------------------------------------
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
        + rng.normal(0, 0.2, size=n_samples)  # irreducible noise
    )

    # Threshold chosen to give a roughly balanced (~40% positive) dataset.
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
    # Guarantee column ordering matches the model contract.
    return df[FEATURE_ORDER + ["pcos"]]


if __name__ == "__main__":
    data = generate_dataset()
    print(data.head())
    print("\nClass balance:\n", data["pcos"].value_counts(normalize=True))
