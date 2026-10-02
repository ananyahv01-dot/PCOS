"""
Lightweight role-based authentication (patient / doctor / counselor / admin).

Uses only the Python standard library:
  - PBKDF2-HMAC-SHA256 for password hashing (no external crypto dependency)
  - in-memory bearer-token sessions (reset on server restart — fine for a demo;
    swap for JWT + a persistent session store in production)

Users are stored in the same MySQL database as predictions. Doctors and
counselors ("providers") additionally carry a specialty/phone/available
status, and patients carry a preferred_provider_id pointing at the provider
they've chosen to share their results with.
"""

from __future__ import annotations

import binascii
import hashlib
import os
import secrets
from contextlib import closing
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException

from .db import _connect  # reuse the shared MySQL connection helper

ROLES = {"patient", "doctor", "counselor", "admin"}
PROVIDER_ROLES = ("doctor", "counselor")

# token -> user dict ({id, name, email, role})
_sessions: dict[str, dict] = {}

RESET_TOKEN_TTL = timedelta(minutes=30)


# --------------------------------------------------------------------------- #
# Password hashing
# --------------------------------------------------------------------------- #
def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return binascii.hexlify(salt).decode(), binascii.hexlify(dk).decode()


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    salt = binascii.unhexlify(salt_hex)
    _, computed = hash_password(password, salt)
    return secrets.compare_digest(computed, hash_hex)


# --------------------------------------------------------------------------- #
# User store
# --------------------------------------------------------------------------- #
def init_auth_db() -> None:
    with closing(_connect()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(120) NOT NULL UNIQUE,
                salt VARCHAR(64) NOT NULL,
                password_hash VARCHAR(128) NOT NULL,
                role VARCHAR(20) NOT NULL,
                created_at VARCHAR(40) NOT NULL,
                specialty VARCHAR(150),
                phone VARCHAR(30),
                available TINYINT NOT NULL DEFAULT 1,
                preferred_provider_id INT
            )
            """
        )
        # Migrations: add columns to databases created before they existed.
        columns = {
            row["COLUMN_NAME"]
            for row in conn.execute(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users'"
            )
        }
        for col, sql_type in (
            ("specialty", "VARCHAR(150)"),
            ("phone", "VARCHAR(30)"),
            ("available", "TINYINT NOT NULL DEFAULT 1"),
            ("preferred_provider_id", "INT"),
        ):
            if col not in columns:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} {sql_type}")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS password_resets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                token_hash VARCHAR(64) NOT NULL UNIQUE,
                expires_at VARCHAR(40) NOT NULL,
                used TINYINT NOT NULL DEFAULT 0,
                created_at VARCHAR(40) NOT NULL
            )
            """
        )
        conn.commit()

    # Seed demo admin, doctor and counselor accounts (override passwords via
    # env vars).
    _seed_user(
        name="Administrator",
        email=os.getenv("PCOS_ADMIN_EMAIL", "admin@pcos.ai"),
        password=os.getenv("PCOS_ADMIN_PASS", "admin123"),
        role="admin",
    )
    _seed_user(
        name="Dr. Demo",
        email=os.getenv("PCOS_DOCTOR_EMAIL", "doctor@pcos.ai"),
        password=os.getenv("PCOS_DOCTOR_PASS", "doctor123"),
        role="doctor",
        specialty="Gynaecologist",
        phone="+91 90000 00000",
    )
    counselor_password = os.getenv("PCOS_COUNSELOR_PASS", "counselor123")
    for name, email, specialty, phone in (
        ("Ananya Rao", "ananya.counselor@pcos.ai", "Mental Health Counselor", "+91 90000 11111"),
        ("Priya Menon", "priya.counselor@pcos.ai", "Nutrition & Lifestyle Counselor", "+91 90000 22222"),
        ("Fatima Sheikh", "fatima.counselor@pcos.ai", "Wellness & Peer Support Counselor", "+91 90000 33333"),
    ):
        _seed_user(
            name=name, email=email, password=counselor_password, role="counselor",
            specialty=specialty, phone=phone,
        )

    # Backfill: patients created before the default-provider behaviour existed
    # (or from a run with no doctor account yet) also default to the doctor.
    default_doctor = get_default_doctor()
    if default_doctor:
        with closing(_connect()) as conn:
            conn.execute(
                "UPDATE users SET preferred_provider_id = ? "
                "WHERE role = 'patient' AND preferred_provider_id IS NULL",
                (default_doctor["id"],),
            )
            conn.commit()


def _seed_user(name: str, email: str, password: str, role: str,
                specialty: str | None = None, phone: str | None = None) -> None:
    if get_user_by_email(email):
        return
    create_user(name=name, email=email, password=password, role=role,
                specialty=specialty, phone=phone)


def get_user_by_email(email: str) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_default_doctor() -> dict | None:
    """The doctor new patients are assigned to by default (the first doctor
    account, i.e. the seeded demo doctor on a fresh install)."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT id, name, email FROM users WHERE role = 'doctor' ORDER BY id LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def create_user(name: str, email: str, password: str, role: str,
                 specialty: str | None = None, phone: str | None = None) -> dict:
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}")
    email = email.lower().strip()
    if get_user_by_email(email):
        raise ValueError("An account with this email already exists.")

    # New patients default to the doctor, unless there isn't one yet.
    preferred_provider_id = None
    if role == "patient":
        default_doctor = get_default_doctor()
        preferred_provider_id = default_doctor["id"] if default_doctor else None

    salt_hex, hash_hex = hash_password(password)
    with closing(_connect()) as conn:
        cur = conn.execute(
            "INSERT INTO users (name, email, salt, password_hash, role, created_at, "
            "specialty, phone, preferred_provider_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name.strip(), email, salt_hex, hash_hex, role,
             datetime.now(timezone.utc).isoformat(), specialty, phone,
             preferred_provider_id),
        )
        conn.commit()
        user_id = cur.lastrowid
    return _public_user(
        {"id": user_id, "name": name.strip(), "email": email, "role": role,
         "specialty": specialty, "phone": phone, "available": 1,
         "preferred_provider_id": preferred_provider_id}
    )


def _public_user(user: dict) -> dict:
    """Strip auth secrets, keeping only what sessions/responses should carry."""
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "specialty": user.get("specialty"),
        "phone": user.get("phone"),
        "available": bool(user["available"]) if user.get("available") is not None else None,
        "preferred_provider_id": user.get("preferred_provider_id"),
    }


def authenticate(email: str, password: str) -> dict | None:
    user = get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["salt"], user["password_hash"]):
        return None
    return _public_user(user)


def update_password(user_id: int, new_password: str) -> None:
    salt_hex, hash_hex = hash_password(new_password)
    with closing(_connect()) as conn:
        conn.execute(
            "UPDATE users SET salt = ?, password_hash = ? WHERE id = ?",
            (salt_hex, hash_hex, user_id),
        )
        conn.commit()
    # A changed password invalidates any session issued before the change.
    for token in [t for t, u in _sessions.items() if u["id"] == user_id]:
        _sessions.pop(token, None)


# --------------------------------------------------------------------------- #
# Providers (doctor / counselor) & patient selection
# --------------------------------------------------------------------------- #
def _update_session_user(user_id: int, **fields) -> None:
    # Sessions cache a snapshot of the user dict at login time, so mutations
    # made via these endpoints need to patch any live sessions too, or the
    # change wouldn't show up until the user logs in again.
    for u in _sessions.values():
        if u["id"] == user_id:
            u.update(fields)


def get_providers() -> list[dict]:
    placeholders = ", ".join("?" * len(PROVIDER_ROLES))
    with closing(_connect()) as conn:
        rows = conn.execute(
            f"SELECT id, name, email, role, specialty, phone, available FROM users "
            f"WHERE role IN ({placeholders}) ORDER BY role, name",
            tuple(PROVIDER_ROLES),
        )
        return [{**dict(r), "available": bool(r["available"])} for r in rows]


def get_provider_by_id(provider_id: int) -> dict | None:
    placeholders = ", ".join("?" * len(PROVIDER_ROLES))
    with closing(_connect()) as conn:
        row = conn.execute(
            f"SELECT id, name, email, role, specialty, phone, available FROM users "
            f"WHERE id = ? AND role IN ({placeholders})",
            (provider_id, *PROVIDER_ROLES),
        ).fetchone()
    return {**row, "available": bool(row["available"])} if row else None


def set_availability(user_id: int, available: bool) -> None:
    with closing(_connect()) as conn:
        conn.execute(
            "UPDATE users SET available = ? WHERE id = ?", (1 if available else 0, user_id)
        )
        conn.commit()
    _update_session_user(user_id, available=available)


def set_preferred_provider(patient_id: int, provider_id: int | None) -> None:
    with closing(_connect()) as conn:
        conn.execute(
            "UPDATE users SET preferred_provider_id = ? WHERE id = ?",
            (provider_id, patient_id),
        )
        conn.commit()
    _update_session_user(patient_id, preferred_provider_id=provider_id)


# --------------------------------------------------------------------------- #
# Password reset
# --------------------------------------------------------------------------- #
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(email: str) -> str | None:
    """Issue a reset token for the given email, or None if no such account.

    The raw token is only ever returned here / logged to the server console —
    only its hash is persisted, so a leaked database can't be used to reset
    passwords. Swap `_deliver_reset_link` for a real email provider in
    production.
    """
    user = get_user_by_email(email)
    if not user:
        return None

    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + RESET_TOKEN_TTL).isoformat()
    with closing(_connect()) as conn:
        conn.execute(
            "INSERT INTO password_resets (user_id, token_hash, expires_at, used, created_at) "
            "VALUES (?, ?, ?, 0, ?)",
            (user["id"], _hash_token(token), expires_at,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    _deliver_reset_link(user["email"], token)
    return token


def _deliver_reset_link(email: str, token: str) -> None:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    link = f"{frontend_url.rstrip('/')}/reset-password?token={token}"
    # No email provider is configured for this demo; print the link instead
    # so it's visible in the server console to whoever is running it locally.
    print(f"[password reset] {email}: {link}", flush=True)


def reset_password(token: str, new_password: str) -> bool:
    token_hash = _hash_token(token)
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM password_resets WHERE token_hash = ?", (token_hash,)
        ).fetchone()
        if not row:
            return False
        if row["used"] or datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            return False

        conn.execute(
            "UPDATE password_resets SET used = 1 WHERE id = ?", (row["id"],)
        )
        conn.commit()

    update_password(row["user_id"], new_password)
    return True


# --------------------------------------------------------------------------- #
# Sessions / dependencies
# --------------------------------------------------------------------------- #
def create_session(user: dict) -> str:
    token = secrets.token_urlsafe(24)
    _sessions[token] = user
    return token


def destroy_session(token: str) -> None:
    _sessions.pop(token, None)


def _user_from_header(authorization: str | None) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    return _sessions.get(token)


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """FastAPI dependency: require any authenticated user."""
    user = _user_from_header(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def optional_user(authorization: str | None = Header(default=None)) -> dict | None:
    """FastAPI dependency: attach the user if a valid token is present, else None."""
    return _user_from_header(authorization)


def require_role(*allowed_roles: str):
    """Dependency factory enforcing that the user has one of the given roles."""

    def _dep(authorization: str | None = Header(default=None)) -> dict:
        user = _user_from_header(authorization)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required.")
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions.")
        return user

    return _dep
