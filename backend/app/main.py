"""
PCOS Care AI - FastAPI application.

Roles
-----
- patient : self-registers, takes assessments (saved to their history)
- doctor  : reviews all patients' assessments
- admin   : model metrics, usage stats, retraining

Endpoints
---------
GET  /api/health
POST /api/predict                  run a risk assessment (optionally authenticated)
POST /api/auth/register            patient self-registration
POST /api/auth/login               login for any role
POST /api/auth/logout              invalidate the current token
GET  /api/auth/me                  current user
GET  /api/patient/history          the patient's own assessments        (patient)
GET  /api/doctor/assessments       all assessments for review            (doctor)
GET  /api/admin/metrics            model evaluation metrics              (admin)
GET  /api/admin/stats              aggregate prediction statistics       (admin)
POST /api/admin/retrain            retrain the model                     (admin)
"""

from __future__ import annotations

import json
import os
import uuid

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import auth, db
from .auth import (
    create_session,
    destroy_session,
    get_current_user,
    optional_user,
    require_role,
)
from .features import build_feature_vector
from .model_store import store, train_and_save
from .recommendations import DISCLAIMER, build_recommendations
from .schemas import (
    AuthResponse,
    LoginInput,
    MetricsResponse,
    PredictionResponse,
    RegisterInput,
    UserOut,
)

app = FastAPI(
    title="PCOS Care AI",
    description="AI-based preliminary PCOS risk assessment (not a medical diagnosis).",
    version="2.0.0",
)

# Directory where uploaded prescription files are stored.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRESCRIPTION_DIR = os.path.join(BASE_DIR, "artifacts", "prescriptions")

# Built React app (produced by `npm run build`). When present, the API also
# serves the frontend so the whole app can run as a single deployment.
FRONTEND_DIST = os.getenv("FRONTEND_DIST", os.path.join(BASE_DIR, "frontend_dist"))
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_UPLOAD_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
}

# Same-origin single-service deploys need no CORS; for split frontend/backend
# deploys set ALLOWED_ORIGINS to a comma-separated list of frontend URLs.
_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()
    auth.init_auth_db()
    store.load_or_train()


def _risk_level(probability: float) -> str:
    if probability < 0.34:
        return "Low"
    if probability < 0.67:
        return "Moderate"
    return "High"


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": store.model is not None}


# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #
@app.post("/api/auth/register", response_model=AuthResponse)
def register(payload: RegisterInput) -> AuthResponse:
    # Public registration is always for the `patient` role.
    try:
        user = auth.create_user(
            name=payload.name, email=payload.email,
            password=payload.password, role="patient",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    token = create_session(user)
    return AuthResponse(token=token, user=UserOut(**user))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginInput) -> AuthResponse:
    user = auth.authenticate(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_session(user)
    return AuthResponse(token=token, user=UserOut(**user))


@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None)) -> dict:
    if authorization and authorization.startswith("Bearer "):
        destroy_session(authorization.split(" ", 1)[1])
    return {"status": "ok"}


@app.get("/api/auth/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)) -> UserOut:
    return UserOut(**user)


# --------------------------------------------------------------------------- #
# Prediction (optionally authenticated so patients build a history)
# --------------------------------------------------------------------------- #
from .schemas import AssessmentInput  # noqa: E402  (kept near usage)


@app.post("/api/predict", response_model=PredictionResponse)
def predict(payload: AssessmentInput,
            user: dict | None = Depends(optional_user)) -> PredictionResponse:
    data = payload.model_dump()
    feature_vector, bmi = build_feature_vector(data)
    probability = store.predict_proba(feature_vector)
    risk_level = _risk_level(probability)

    recommendations = build_recommendations(data, bmi, risk_level)

    db.log_prediction(
        name=data["name"], age=data["age"], bmi=bmi, probability=probability,
        risk_level=risk_level,
        user_id=user["id"] if user else None,
        user_email=user["email"] if user else None,
        details=json.dumps(data),
        recommendations=json.dumps(recommendations),
    )

    return PredictionResponse(
        risk_level=risk_level,
        probability=round(probability, 4),
        bmi=bmi,
        recommendations=recommendations,
        disclaimer=DISCLAIMER,
    )


# --------------------------------------------------------------------------- #
# Patient
# --------------------------------------------------------------------------- #
@app.get("/api/patient/history")
def patient_history(user: dict = Depends(require_role("patient"))) -> dict:
    return {"history": db.get_history(user["id"])}


# --------------------------------------------------------------------------- #
# Doctor
# --------------------------------------------------------------------------- #
@app.get("/api/doctor/assessments")
def doctor_assessments(user: dict = Depends(require_role("doctor", "admin"))) -> dict:
    rows = db.get_all_assessments()
    counts = {"Low": 0, "Moderate": 0, "High": 0}
    for r in rows:
        counts[r["risk_level"]] = counts.get(r["risk_level"], 0) + 1
    return {"assessments": rows, "counts": counts, "total": len(rows)}


# --------------------------------------------------------------------------- #
# Assessment detail (for downloadable reports) — doctor/admin or owning patient
# --------------------------------------------------------------------------- #
@app.get("/api/assessments/{assessment_id}")
def assessment_detail(assessment_id: int,
                      user: dict = Depends(get_current_user)) -> dict:
    record = db.get_assessment(assessment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    # Access control: doctors/admins can view any; patients only their own.
    if user["role"] not in ("doctor", "admin") and record.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorised to view this record.")

    recommendations = json.loads(record["recommendations"]) if record.get("recommendations") else []
    responses = json.loads(record["details"]) if record.get("details") else None
    return {
        "id": record["id"],
        "created_at": record["created_at"],
        "name": record["name"],
        "age": record["age"],
        "bmi": record["bmi"],
        "probability": record["probability"],
        "risk_level": record["risk_level"],
        "recommendations": recommendations,
        "responses": responses,
        "disclaimer": DISCLAIMER,
    }


# --------------------------------------------------------------------------- #
# Prescriptions
# --------------------------------------------------------------------------- #
@app.post("/api/doctor/prescriptions")
async def upload_prescription(
    patient_email: str = Form(...),
    note: str | None = Form(default=None),
    assessment_id: int | None = Form(default=None),
    file: UploadFile = File(...),
    doctor: dict = Depends(require_role("doctor", "admin")),
) -> dict:
    if file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload a PDF or image (PNG/JPEG/WebP).",
        )

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds the 10 MB limit.")

    # Only allow attaching to a real patient account.
    if not auth.get_user_by_email(patient_email):
        raise HTTPException(
            status_code=400,
            detail="No patient account found for that email.",
        )

    os.makedirs(PRESCRIPTION_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1][:10]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(PRESCRIPTION_DIR, stored_name), "wb") as fh:
        fh.write(contents)

    pid = db.add_prescription(
        patient_email=patient_email,
        doctor_name=doctor["name"],
        doctor_id=doctor["id"],
        filename=file.filename or stored_name,
        stored_name=stored_name,
        content_type=file.content_type,
        note=note,
        assessment_id=assessment_id,
    )
    return {"status": "uploaded", "id": pid}


@app.get("/api/patient/prescriptions")
def patient_prescriptions(user: dict = Depends(require_role("patient"))) -> dict:
    return {"prescriptions": db.get_prescriptions_for_patient(user["email"])}


@app.get("/api/prescriptions/{prescription_id}/download")
def download_prescription(prescription_id: int,
                          user: dict = Depends(get_current_user)) -> FileResponse:
    record = db.get_prescription(prescription_id)
    if not record:
        raise HTTPException(status_code=404, detail="Prescription not found.")

    # Access control: doctors/admins, or the patient it belongs to.
    is_owner = user["email"].lower() == record["patient_email"].lower()
    if user["role"] not in ("doctor", "admin") and not is_owner:
        raise HTTPException(status_code=403, detail="Not authorised.")

    path = os.path.join(PRESCRIPTION_DIR, record["stored_name"])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File missing on server.")

    return FileResponse(
        path,
        media_type=record["content_type"] or "application/octet-stream",
        filename=record["filename"],
    )


# --------------------------------------------------------------------------- #
# Admin
# --------------------------------------------------------------------------- #
@app.get("/api/admin/metrics", response_model=MetricsResponse)
def admin_metrics(_: dict = Depends(require_role("admin"))) -> MetricsResponse:
    if store.metrics is None:
        raise HTTPException(status_code=503, detail="Model metrics unavailable.")
    return MetricsResponse(**store.metrics)


@app.get("/api/admin/stats")
def admin_stats(_: dict = Depends(require_role("admin"))) -> dict:
    return db.get_stats()


@app.post("/api/admin/retrain")
def admin_retrain(_: dict = Depends(require_role("admin"))) -> dict:
    metrics = train_and_save()
    store.load_or_train()
    return {"status": "retrained", "metrics": metrics}


# --------------------------------------------------------------------------- #
# Serve the built React app (single-service deployment). Registered last so it
# only catches routes not handled by the API above.
# --------------------------------------------------------------------------- #
if os.path.isdir(FRONTEND_DIST):

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        # Never let the catch-all shadow the API surface.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        # Serve real static files (JS/CSS/images) when they exist...
        candidate = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        # ...otherwise fall back to index.html for client-side routing.
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
