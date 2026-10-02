"""
MySQL-backed logging of predictions so the admin dashboard can show real
usage statistics. Defaults match XAMPP's stock MySQL (host 127.0.0.1, port
3306, user root, no password) for local development — override via the
DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME env vars for any other
MySQL instance (docker-compose points DB_HOST at its own `mysql` service).
Start MySQL (via XAMPP, or `docker compose up`) before running the backend.
"""

from __future__ import annotations

import os
import time
from contextlib import closing
from datetime import datetime, timezone

import pymysql
import pymysql.cursors

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "pcos_care")


class _Connection:
    """Thin shim over a PyMySQL connection so call sites can keep using the
    sqlite3-style `conn.execute(sql, params).fetchone()/.fetchall()` pattern
    (translating the `?` placeholders used throughout this file to the `%s`
    style PyMySQL expects)."""

    def __init__(self, raw: pymysql.connections.Connection):
        self._raw = raw

    def execute(self, sql: str, params: tuple = ()) -> pymysql.cursors.Cursor:
        cur = self._raw.cursor()
        cur.execute(sql.replace("?", "%s"), params)
        return cur

    def commit(self) -> None:
        self._raw.commit()

    def close(self) -> None:
        self._raw.close()


def _ensure_database(retries: int = 10, delay_seconds: float = 2.0) -> None:
    # In Docker Compose the app container can start fetching connections
    # slightly before MySQL is ready to accept them even with a healthcheck
    # in place, so retry briefly instead of crashing on the first attempt.
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD)
            break
        except pymysql.err.OperationalError as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(delay_seconds)
    else:
        raise ConnectionError(
            f"Could not reach MySQL at {DB_HOST}:{DB_PORT} after {retries} attempts. "
            "Start MySQL first (e.g. XAMPP's MySQL module, or `docker compose up`)."
        ) from last_error

    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()


def _connect() -> _Connection:
    raw = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    return _Connection(raw)


def init_db() -> None:
    _ensure_database()
    with closing(_connect()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                created_at VARCHAR(40) NOT NULL,
                name VARCHAR(100),
                age INT,
                bmi DOUBLE,
                probability DOUBLE,
                risk_level VARCHAR(20),
                user_id INT,
                user_email VARCHAR(120),
                details LONGTEXT,
                recommendations LONGTEXT
            )
            """
        )
        # Migrations: add columns to databases created before they existed.
        columns = {
            row["COLUMN_NAME"]
            for row in conn.execute(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'predictions'"
            )
        }
        for col in ("name", "user_id", "user_email", "details", "recommendations"):
            if col not in columns:
                sql_type = "INT" if col == "user_id" else "LONGTEXT"
                conn.execute(f"ALTER TABLE predictions ADD COLUMN {col} {sql_type}")

        # Prescriptions uploaded by doctors/counselors for patients.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prescriptions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                created_at VARCHAR(40) NOT NULL,
                assessment_id INT,
                patient_email VARCHAR(120) NOT NULL,
                doctor_name VARCHAR(100),
                doctor_id INT,
                note TEXT,
                filename VARCHAR(255) NOT NULL,
                stored_name VARCHAR(255) NOT NULL,
                content_type VARCHAR(100),
                provider_role VARCHAR(20),
                superseded TINYINT NOT NULL DEFAULT 0
            )
            """
        )
        rx_columns = {
            row["COLUMN_NAME"]
            for row in conn.execute(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'prescriptions'"
            )
        }
        for col, sql_type in (
            ("provider_role", "VARCHAR(20)"),
            ("superseded", "TINYINT NOT NULL DEFAULT 0"),
        ):
            if col not in rx_columns:
                conn.execute(f"ALTER TABLE prescriptions ADD COLUMN {col} {sql_type}")

        # Blood/lab reports uploaded by patients for their doctor/counselor.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blood_reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                created_at VARCHAR(40) NOT NULL,
                assessment_id INT,
                patient_email VARCHAR(120) NOT NULL,
                patient_name VARCHAR(100),
                note TEXT,
                filename VARCHAR(255) NOT NULL,
                stored_name VARCHAR(255) NOT NULL,
                content_type VARCHAR(100)
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


def get_latest_risk_level(user_id: int) -> str | None:
    """The patient's most recent risk level, or None if they have no
    assessments yet. Used to gate the counselor concept to High-risk
    patients only — Moderate/Low risk stays doctor-only."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT risk_level FROM predictions WHERE user_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    return row["risk_level"] if row else None


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
    """Every assessment (admin-only, unrestricted review), newest first."""
    with closing(_connect()) as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT id, created_at, name, age, bmi, probability, risk_level, "
                "user_email FROM predictions ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        ]


def get_assessments_for_provider(provider_id: int, limit: int = 200) -> list[dict]:
    """Assessments belonging to patients who selected this doctor/counselor
    as their provider (for the doctor/counselor review dashboard), newest
    first. Guest/unauthenticated assessments have no owning account and so
    never appear here — only an admin's unrestricted view includes them."""
    with closing(_connect()) as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT p.id, p.created_at, p.name, p.age, p.bmi, p.probability, "
                "p.risk_level, p.user_email FROM predictions p "
                "JOIN users u ON p.user_id = u.id "
                "WHERE u.preferred_provider_id = ? ORDER BY p.id DESC LIMIT ?",
                (provider_id, limit),
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
                     provider_role: str, note: str | None = None,
                     assessment_id: int | None = None) -> int:
    with closing(_connect()) as conn:
        cur = conn.execute(
            "INSERT INTO prescriptions "
            "(created_at, assessment_id, patient_email, doctor_name, doctor_id, "
            "note, filename, stored_name, content_type, provider_role, superseded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
            (datetime.now(timezone.utc).isoformat(), assessment_id,
             patient_email.lower().strip(), doctor_name, doctor_id, note,
             filename, stored_name, content_type, provider_role),
        )
        conn.commit()
        return cur.lastrowid


def supersede_counselor_prescriptions(patient_email: str) -> None:
    """A doctor's prescription takes priority: mark any not-yet-superseded
    counselor prescriptions for this patient as superseded. Keeps the
    records (for history) rather than deleting them."""
    with closing(_connect()) as conn:
        conn.execute(
            "UPDATE prescriptions SET superseded = 1 "
            "WHERE patient_email = ? AND provider_role = 'counselor' AND superseded = 0",
            (patient_email.lower().strip(),),
        )
        conn.commit()


def get_prescriptions_for_patient(patient_email: str) -> list[dict]:
    with closing(_connect()) as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT id, created_at, assessment_id, doctor_name, note, "
                "filename, content_type, provider_role, superseded FROM prescriptions "
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


# --------------------------------------------------------------------------- #
# Blood / lab reports (patient-uploaded, for their doctor/counselor to review)
# --------------------------------------------------------------------------- #
def add_blood_report(patient_email: str, patient_name: str, filename: str,
                     stored_name: str, content_type: str | None,
                     note: str | None = None,
                     assessment_id: int | None = None) -> int:
    with closing(_connect()) as conn:
        cur = conn.execute(
            "INSERT INTO blood_reports "
            "(created_at, assessment_id, patient_email, patient_name, note, "
            "filename, stored_name, content_type) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), assessment_id,
             patient_email.lower().strip(), patient_name, note,
             filename, stored_name, content_type),
        )
        conn.commit()
        return cur.lastrowid


def get_blood_reports_for_patient(patient_email: str) -> list[dict]:
    with closing(_connect()) as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT id, created_at, assessment_id, patient_name, note, "
                "filename, content_type FROM blood_reports "
                "WHERE patient_email = ? ORDER BY id DESC",
                (patient_email.lower().strip(),),
            )
        ]


def get_blood_report(report_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM blood_reports WHERE id = ?", (report_id,)
        ).fetchone()
    return dict(row) if row else None
