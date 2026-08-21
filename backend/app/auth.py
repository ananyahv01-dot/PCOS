"""
Lightweight role-based authentication (patient / doctor / admin).

Uses only the Python standard library:
  - PBKDF2-HMAC-SHA256 for password hashing (no external crypto dependency)
  - in-memory bearer-token sessions (reset on server restart — fine for a demo;
    swap for JWT + a persistent session store in production)

Users are stored in the same SQLite database as predictions.
"""

from __future__ import annotations

import binascii
import hashlib
import os
import secrets
from contextlib import closing
from datetime import datetime, timezone

from fastapi import Header, HTTPException

from .db import _connect  # reuse the shared SQLite connection helper

ROLES = {"patient", "doctor", "admin"}

# token -> user dict ({id, name, email, role})
_sessions: dict[str, dict] = {}


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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

    # Seed demo doctor + admin accounts (override passwords via env vars).
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
    )


def _seed_user(name: str, email: str, password: str, role: str) -> None:
    if get_user_by_email(email):
        return
    create_user(name=name, email=email, password=password, role=role)


def get_user_by_email(email: str) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
    return dict(row) if row else None


def create_user(name: str, email: str, password: str, role: str) -> dict:
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}")
    email = email.lower().strip()
    if get_user_by_email(email):
        raise ValueError("An account with this email already exists.")
    salt_hex, hash_hex = hash_password(password)
    with closing(_connect()) as conn:
        cur = conn.execute(
            "INSERT INTO users (name, email, salt, password_hash, role, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name.strip(), email, salt_hex, hash_hex, role,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        user_id = cur.lastrowid
    return {"id": user_id, "name": name.strip(), "email": email, "role": role}


def authenticate(email: str, password: str) -> dict | None:
    user = get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["salt"], user["password_hash"]):
        return None
    return {"id": user["id"], "name": user["name"], "email": user["email"],
            "role": user["role"]}


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
