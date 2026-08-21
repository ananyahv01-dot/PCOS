"""
Lightweight SQLite logging of predictions so the admin dashboard can show
real usage statistics. SQLite ships with Python, so no external database
is required to run the project (MongoDB/MySQL can be swapped in later).
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "artifacts", "pcos_care.db")


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(_connect()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT,
                age INTEGER,
                bmi REAL,
                probability REAL,
                risk_level TEXT,
                user_id INTEGER,
                user_email TEXT,
                details TEXT,
                recommendations TEXT
            )
            """
        )
        # Migrations: add columns to databases created before they existed.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(predictions)")}
        for col in ("name", "user_id", "user_email", "details", "recommendations"):
            if col not in columns:
                sql_type = "INTEGER" if col == "user_id" else "TEXT"
                conn.execute(f"ALTER TABLE predictions ADD COLUMN {col} {sql_type}")

        # Prescriptions uploaded by doctors for patients.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prescriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                assessment_id INTEGER,
                patient_email TEXT NOT NULL,
                doctor_name TEXT,
                doctor_id INTEGER,
                note TEXT,
                filename TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                content_type TEXT
            )
            """
        )
        conn.commit()


def log_prediction(name: str, age: int, bmi: float, probability: float,
                   risk_level: str, user_id: int | None = None,
                   user_email: str | None = None, details: str | None = None,
                   recommendations: str | None = None) -> int:
    with closing(_connect()) as conn:
        cur = conn.execute(
            "INSERT INTO predictions "
            "(created_at, name, age, bmi, probability, risk_level, user_id, "
            "user_email, details, recommendations) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), name, age, round(bmi, 2),
             round(probability, 4), risk_level, user_id, user_email, details,
             recommendations),
        )
        conn.commit()
        return cur.lastrowid


def get_assessment(assessment_id: int) -> dict | None:
    """Full record for one assessment (used to build downloadable reports)."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM predictions WHERE id = ?", (assessment_id,)
        ).fetchone()
    return dict(row) if row else None


def get_history(user_id: int, limit: int = 50) -> list[dict]:
    """All assessments belonging to one patient, newest first."""
    with closing(_connect()) as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT id, created_at, name, age, bmi, probability, risk_level "
                "FROM predictions WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            )
        ]


def get_all_assessments(limit: int = 200) -> list[dict]:
    """Every assessment (for the doctor review dashboard), newest first."""
    with closing(_connect()) as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT id, created_at, name, age, bmi, probability, risk_level, "
                "user_email FROM predictions ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        ]


def get_stats() -> dict:
    with closing(_connect()) as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM predictions").fetchone()["c"]

        by_level = {row["risk_level"]: row["c"] for row in conn.execute(
            "SELECT risk_level, COUNT(*) AS c FROM predictions GROUP BY risk_level"
        )}

        avg_prob_row = conn.execute(
            "SELECT AVG(probability) AS a FROM predictions"
        ).fetchone()
        avg_prob = round(avg_prob_row["a"], 4) if avg_prob_row["a"] is not None else 0.0

        recent = [
            dict(row)
            for row in conn.execute(
                "SELECT created_at, name, age, bmi, probability, risk_level "
                "FROM predictions ORDER BY id DESC LIMIT 10"
            )
        ]

    return {
        "total_assessments": total,
        "risk_distribution": {
            "Low": by_level.get("Low", 0),
            "Moderate": by_level.get("Moderate", 0),
            "High": by_level.get("High", 0),
        },
        "average_probability": avg_prob,
        "recent": recent,
    }


# --------------------------------------------------------------------------- #
# Prescriptions
# --------------------------------------------------------------------------- #
def add_prescription(patient_email: str, doctor_name: str, doctor_id: int,
                     filename: str, stored_name: str, content_type: str | None,
                     note: str | None = None,
                     assessment_id: int | None = None) -> int:
    with closing(_connect()) as conn:
        cur = conn.execute(
            "INSERT INTO prescriptions "
            "(created_at, assessment_id, patient_email, doctor_name, doctor_id, "
            "note, filename, stored_name, content_type) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), assessment_id,
             patient_email.lower().strip(), doctor_name, doctor_id, note,
             filename, stored_name, content_type),
        )
        conn.commit()
        return cur.lastrowid


def get_prescriptions_for_patient(patient_email: str) -> list[dict]:
    with closing(_connect()) as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT id, created_at, assessment_id, doctor_name, note, "
                "filename, content_type FROM prescriptions "
                "WHERE patient_email = ? ORDER BY id DESC",
                (patient_email.lower().strip(),),
            )
        ]


def get_prescription(prescription_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM prescriptions WHERE id = ?", (prescription_id,)
        ).fetchone()
    return dict(row) if row else None
