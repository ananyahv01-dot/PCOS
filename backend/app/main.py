"""
PCOS Care AI - FastAPI application.

Roles
-----
- patient   : self-registers, takes assessments (defaults to the doctor as
              their provider); offered a counselor instead only if/when the
              doctor is unavailable AND their assessment is High risk —
              Moderate/Low risk stays doctor-only, no counselor concept at all
- doctor    : unrestricted review/upload like admin, regardless of which
              patients selected them; the only role with an availability
              toggle
- counselor : reviews patients who selected them, but can only upload
              prescriptions for the ones who are High risk (no availability
              concept of their own — always offered as the fallback); a
              doctor's prescription supersedes a counselor's for that patient
- admin     : model metrics, usage stats, retraining, unrestricted review

Endpoints
---------
GET  /api/health
POST /api/predict                  run a risk assessment (optionally authenticated)
POST /api/auth/register            patient self-registration
POST /api/auth/login               login for any role
POST /api/auth/forgot-password     request a password reset link
POST /api/auth/reset-password      set a new password using a reset token
POST /api/auth/logout              invalidate the current token
GET  /api/auth/me                  current user
GET  /api/providers                list doctors & counselors (with availability)
PATCH /api/provider/availability   toggle own availability               (doctor only)
POST /api/patient/select-provider  choose/clear preferred provider        (patient)
GET  /api/patient/history          the patient's own assessments        (patient)
GET  /api/doctor/assessments       every assessment for doctor/admin;     (doctor/counselor/admin)
                                    counselor sees only selected patients'
POST /api/patient/blood-reports    upload a lab report (High risk only)   (patient)
GET  /api/patient/blood-reports    the patient's own uploaded reports     (patient)
GET  /api/doctor/blood-reports     a patient's reports (?patient_email=)  (doctor/counselor/admin)
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
    AvailabilityInput,
    ForgotPasswordInput,
    LoginInput,
    MetricsResponse,
    PredictionResponse,
    ProviderOut,
    RegisterInput,
    ResetPasswordInput,
    SelectProviderInput,
    UserOut,
)

app = FastAPI(
    title="PCOS Care AI",
    description="AI-based preliminary PCOS risk assessment (not a medical diagnosis).",
    version="2.0.0",
)

# Directories where uploaded prescription / blood report files are stored.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRESCRIPTION_DIR = os.path.join(BASE_DIR, "artifacts", "prescriptions")
BLOOD_REPORT_DIR = os.path.join(BASE_DIR, "artifacts", "blood_reports")

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
# Providers (doctor / counselor) — public directory, no login required
# --------------------------------------------------------------------------- #
@app.get("/api/providers", response_model=list[ProviderOut])
def list_providers() -> list[ProviderOut]:
    return [ProviderOut(**p) for p in auth.get_providers()]


@app.patch("/api/provider/availability")
def set_my_availability(payload: AvailabilityInput,
                         user: dict = Depends(require_role("doctor"))) -> dict:
    # Only the doctor has an availability switch — counselors are always
    # offered as the fallback when the doctor isn't available.
    auth.set_availability(user["id"], payload.available)
    return {"status": "ok", "available": payload.available}


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


@app.post("/api/auth/forgot-password")
def forgot_password(payload: ForgotPasswordInput) -> dict:
    # Always return the same generic message, whether or not the email is
    # registered, so this endpoint can't be used to enumerate accounts.
    auth.create_password_reset_token(payload.email)
    return {
        "status": "ok",
        "message": "If an account exists for that email, a reset link has been sent.",
    }


@app.post("/api/auth/reset-password")
def reset_password(payload: ResetPasswordInput) -> dict:
    if not auth.reset_password(payload.token, payload.new_password):
        raise HTTPException(
            status_code=400, detail="This reset link is invalid or has expired."
        )
    return {"status": "ok", "message": "Password updated. You can now log in."}


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


@app.post("/api/patient/select-provider")
def select_provider(payload: SelectProviderInput,
                     user: dict = Depends(require_role("patient"))) -> dict:
    provider = None
    if payload.provider_id is not None:
        provider = auth.get_provider_by_id(payload.provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found.")
        if not provider["available"]:
            raise HTTPException(status_code=400, detail="This provider isn't available right now.")
    auth.set_preferred_provider(user["id"], payload.provider_id)
    return {"status": "ok", "provider": provider}


# --------------------------------------------------------------------------- #
# Doctor / counselor ("provider") review dashboard
# --------------------------------------------------------------------------- #
@app.get("/api/doctor/assessments")
def doctor_assessments(user: dict = Depends(require_role("doctor", "counselor", "admin"))) -> dict:
    # Doctors have the same unrestricted oversight as admins — selection and
    # availability only gate counselors. A doctor who's marked themselves
    # unavailable still sees and can act on every patient's report.
    rows = db.get_all_assessments() if user["role"] in ("admin", "doctor") else db.get_assessments_for_provider(user["id"])
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

    # Access control: admins and doctors view any record; counselors only
    # their selected patients'; patients only their own.
    if user["role"] in ("admin", "doctor"):
        pass
    elif user["role"] == "counselor":
        owner = auth.get_user_by_id(record["user_id"]) if record.get("user_id") else None
        if not owner or owner.get("preferred_provider_id") != user["id"]:
            raise HTTPException(status_code=403, detail="Not authorised to view this record.")
    elif record.get("user_id") != user["id"]:
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
    doctor: dict = Depends(require_role("doctor", "counselor", "admin")),
) -> dict:
    if file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload a PDF or image (PNG/JPEG/WebP).",
        )

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds the 10 MB limit.")

    # Only allow attaching to a real patient account. Counselors may only
    # upload for High-risk patients who selected them — Moderate/Low risk
    # stays doctor-only, regardless of who's assigned. Doctors and admins can
    # always upload for any patient (a doctor's prescription takes priority —
    # see below).
    patient = auth.get_user_by_email(patient_email)
    if not patient:
        raise HTTPException(
            status_code=400,
            detail="No patient account found for that email.",
        )
    if doctor["role"] == "counselor":
        if patient.get("preferred_provider_id") != doctor["id"]:
            raise HTTPException(
                status_code=403,
                detail="This patient hasn't selected you as their provider.",
            )
        if assessment_id is not None:
            assessment = db.get_assessment(assessment_id)
            risk_level = assessment["risk_level"] if assessment else None
        else:
            risk_level = db.get_latest_risk_level(patient["id"])
        if risk_level != "High":
            raise HTTPException(
                status_code=403,
                detail="Counselors can only upload prescriptions for High-risk patients.",
            )

    os.makedirs(PRESCRIPTION_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1][:10]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(PRESCRIPTION_DIR, stored_name), "wb") as fh:
        fh.write(contents)

    if doctor["role"] == "doctor":
        # A doctor's prescription overrides any counselor's for this patient.
        db.supersede_counselor_prescriptions(patient_email)

    pid = db.add_prescription(
        patient_email=patient_email,
        doctor_name=doctor["name"],
        doctor_id=doctor["id"],
        filename=file.filename or stored_name,
        stored_name=stored_name,
        content_type=file.content_type,
        provider_role=doctor["role"],
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

    # Access control: admins/doctors can download any; a counselor only one
    # they uploaded themselves; or the patient it belongs to.
    is_owner = user["email"].lower() == record["patient_email"].lower()
    is_assigned_provider = user["role"] == "counselor" and record.get("doctor_id") == user["id"]
    if user["role"] not in ("admin", "doctor") and not is_owner and not is_assigned_provider:
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
# Blood / lab reports — patients upload for their doctor/counselor to review
# --------------------------------------------------------------------------- #
@app.post("/api/patient/blood-reports")
async def upload_blood_report(
    note: str | None = Form(default=None),
    assessment_id: int | None = Form(default=None),
    file: UploadFile = File(...),
    patient: dict = Depends(require_role("patient")),
) -> dict:
    if file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload a PDF or image (PNG/JPEG/WebP).",
        )

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds the 10 MB limit.")

    # Only High-risk patients can share a blood report with their provider.
    if assessment_id is not None:
        assessment = db.get_assessment(assessment_id)
        risk_level = assessment["risk_level"] if assessment else None
    else:
        risk_level = db.get_latest_risk_level(patient["id"])
    if risk_level != "High":
        raise HTTPException(
            status_code=403,
            detail="Blood reports can only be uploaded for a High-risk assessment.",
        )

    os.makedirs(BLOOD_REPORT_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1][:10]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(BLOOD_REPORT_DIR, stored_name), "wb") as fh:
        fh.write(contents)

    rid = db.add_blood_report(
        patient_email=patient["email"],
        patient_name=patient["name"],
        filename=file.filename or stored_name,
        stored_name=stored_name,
        content_type=file.content_type,
        note=note,
        assessment_id=assessment_id,
    )
    return {"status": "uploaded", "id": rid}


@app.get("/api/patient/blood-reports")
def patient_blood_reports(user: dict = Depends(require_role("patient"))) -> dict:
    return {"blood_reports": db.get_blood_reports_for_patient(user["email"])}


@app.get("/api/doctor/blood-reports")
def provider_blood_reports(
    patient_email: str,
    user: dict = Depends(require_role("doctor", "counselor", "admin")),
) -> dict:
    patient = auth.get_user_by_email(patient_email)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    if user["role"] == "counselor":
        if patient.get("preferred_provider_id") != user["id"]:
            raise HTTPException(
                status_code=403, detail="This patient hasn't selected you as their provider."
            )
        if db.get_latest_risk_level(patient["id"]) != "High":
            raise HTTPException(
                status_code=403,
                detail="Counselors can only view blood reports for High-risk patients.",
            )
    return {"blood_reports": db.get_blood_reports_for_patient(patient_email)}


@app.get("/api/blood-reports/{report_id}/download")
def download_blood_report(report_id: int,
                          user: dict = Depends(get_current_user)) -> FileResponse:
    record = db.get_blood_report(report_id)
    if not record:
        raise HTTPException(status_code=404, detail="Blood report not found.")

    is_owner = user["email"].lower() == record["patient_email"].lower()
    if user["role"] not in ("admin", "doctor") and not is_owner:
        if user["role"] == "counselor":
            patient = auth.get_user_by_email(record["patient_email"])
            if (
                not patient
                or patient.get("preferred_provider_id") != user["id"]
                or db.get_latest_risk_level(patient["id"]) != "High"
            ):
                raise HTTPException(status_code=403, detail="Not authorised.")
        else:
            raise HTTPException(status_code=403, detail="Not authorised.")

    path = os.path.join(BLOOD_REPORT_DIR, record["stored_name"])
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
