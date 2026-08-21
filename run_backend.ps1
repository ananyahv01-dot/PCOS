# PCOS Care AI - backend launcher (Windows PowerShell)
# Creates a virtualenv, installs deps, and starts the FastAPI server.
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\backend"

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}

& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "Starting FastAPI on http://127.0.0.1:8000 (docs at /docs)" -ForegroundColor Green
& ".venv\Scripts\python.exe" -m uvicorn app.main:app --reload
