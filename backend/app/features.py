"""
Central definition of the feature set used across data generation,
model training and prediction. Keeping this in one place guarantees the
training pipeline and the live prediction endpoint always agree on the
order and meaning of every feature fed to the Random Forest model.
"""

from __future__ import annotations

# The exact order of columns the model is trained on and expects at
# prediction time. DO NOT reorder without retraining the model.
FEATURE_ORDER = [
    "age",
    "bmi",
    "cycle_length",
    "cycle_irregular",
    "weight_gain",
    "hair_growth",
    "skin_darkening",
    "hair_loss",
    "pimples",
    "fast_food",
    "exercise",
    "mood_swings",
    "family_history",
]

# Human-friendly labels used by the admin dashboard / feature importance chart.
FEATURE_LABELS = {
    "age": "Age",
    "bmi": "BMI",
    "cycle_length": "Menstrual cycle length",
    "cycle_irregular": "Irregular cycles",
    "weight_gain": "Recent weight gain",
    "hair_growth": "Excess hair growth (hirsutism)",
    "skin_darkening": "Skin darkening",
    "hair_loss": "Hair loss / thinning",
    "pimples": "Acne / pimples",
    "fast_food": "Frequent fast food",
    "exercise": "Regular exercise",
    "mood_swings": "Mood swings",
    "family_history": "Family history of PCOS",
}


def compute_bmi(weight_kg: float, height_cm: float) -> float:
    """Body Mass Index = weight(kg) / height(m)^2."""
    height_m = height_cm / 100.0
    if height_m <= 0:
        raise ValueError("Height must be greater than zero.")
    return round(weight_kg / (height_m * height_m), 2)


def build_feature_vector(payload: dict) -> tuple[list[float], float]:
    """
    Turn a validated assessment payload into the ordered numeric feature
    vector the model consumes. Booleans are cast to 0/1.

    Returns a tuple of (feature_vector, computed_bmi).
    """
    bmi = compute_bmi(payload["weight_kg"], payload["height_cm"])
    values = {
        "age": float(payload["age"]),
        "bmi": float(bmi),
        "cycle_length": float(payload["cycle_length"]),
        "cycle_irregular": float(bool(payload["cycle_irregular"])),
        "weight_gain": float(bool(payload["weight_gain"])),
        "hair_growth": float(bool(payload["hair_growth"])),
        "skin_darkening": float(bool(payload["skin_darkening"])),
        "hair_loss": float(bool(payload["hair_loss"])),
        "pimples": float(bool(payload["pimples"])),
        "fast_food": float(bool(payload["fast_food"])),
        "exercise": float(bool(payload["exercise"])),
        "mood_swings": float(bool(payload["mood_swings"])),
        "family_history": float(bool(payload["family_history"])),
    }
    return [values[name] for name in FEATURE_ORDER], bmi
