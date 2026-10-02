"""Pydantic request/response models for the API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AssessmentInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the person")
    age: int = Field(..., ge=10, le=70, description="Age in years")
    weight_kg: float = Field(..., ge=25, le=200, description="Weight in kilograms")
    height_cm: float = Field(..., ge=120, le=210, description="Height in centimetres")
    cycle_length: int = Field(..., ge=15, le=90, description="Average menstrual cycle length (days)")
    cycle_irregular: bool = Field(..., description="Are your cycles irregular?")
    weight_gain: bool = Field(..., description="Recent unexplained weight gain?")
    hair_growth: bool = Field(..., description="Excess hair growth (face/body)?")
    skin_darkening: bool = Field(..., description="Darkening of skin (neck/underarms)?")
    hair_loss: bool = Field(..., description="Hair loss / thinning on scalp?")
    pimples: bool = Field(..., description="Frequent acne / pimples?")
    fast_food: bool = Field(..., description="Frequent fast food consumption?")
    exercise: bool = Field(..., description="Regular physical exercise?")
    mood_swings: bool = Field(..., description="Frequent mood swings?")
    family_history: bool = Field(..., description="Family history of PCOS?")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Sneha",
                "age": 27,
                "weight_kg": 74,
                "height_cm": 160,
                "cycle_length": 38,
                "cycle_irregular": True,
                "weight_gain": True,
                "hair_growth": True,
                "skin_darkening": True,
                "hair_loss": False,
                "pimples": True,
                "fast_food": True,
                "exercise": False,
                "mood_swings": True,
                "family_history": True,
            }
        }
    }


class Recommendation(BaseModel):
    title: str
    detail: str
    category: str


class PredictionResponse(BaseModel):
    risk_level: Literal["Low", "Moderate", "High"]
    probability: float = Field(..., description="Model probability of PCOS (0-1)")
    bmi: float
    recommendations: list[Recommendation]
    disclaimer: str


class MetricsResponse(BaseModel):
    trained_at: str | None
    n_samples: int
    n_features: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    confusion_matrix: list[list[int]]
    feature_importance: list[dict]
    roc_auc: float


class AdminLoginInput(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    token: str


# ---- Role-based auth ------------------------------------------------------ #
class RegisterInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=6, max_length=100)


class LoginInput(BaseModel):
    email: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=1, max_length=100)


class ForgotPasswordInput(BaseModel):
    email: str = Field(..., min_length=3, max_length=120)


class ResetPasswordInput(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=100)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: Literal["patient", "doctor", "counselor", "admin"]
    specialty: str | None = None
    phone: str | None = None
    available: bool | None = None
    preferred_provider_id: int | None = None


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# ---- Providers (doctor / counselor) & patient selection -------------------- #
class ProviderOut(BaseModel):
    id: int
    name: str
    role: Literal["doctor", "counselor"]
    email: str
    specialty: str | None = None
    phone: str | None = None
    available: bool


class AvailabilityInput(BaseModel):
    available: bool


class SelectProviderInput(BaseModel):
    provider_id: int | None = Field(
        default=None, description="Provider to select, or null to clear the selection"
    )
