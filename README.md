# PCOS Care AI

AI-based **preliminary PCOS risk assessment** and personalized (non-diagnostic)
care system. A Random Forest machine-learning model analyses health &amp;
lifestyle inputs and returns a risk estimate plus general wellness guidance.

> ⚠️ **Not a medical device.** PCOS Care AI provides an AI-generated preliminary
> risk estimate only. It does **not** diagnose PCOS and does not replace a
> qualified healthcare professional.

---

## Architecture

```
React + Vite frontend  ──HTTP──▶  FastAPI backend  ──▶  Random Forest model
     (Tailwind)                     (scikit-learn)         (+ MySQL log)
```

| Layer            | Technology                                |
| ---------------- | ----------------------------------------- |
| Frontend         | React.js + Vite, Tailwind CSS, Recharts   |
| Backend / API    | FastAPI (Python)                          |
| Machine Learning | scikit-learn — RandomForestClassifier     |
| Data processing  | Pandas, NumPy                             |
| Storage          | MySQL (e.g. the one bundled with XAMPP)   |

---

## Project layout

```
AI/
├─ backend/
│  ├─ app/
│  │  ├─ main.py            FastAPI app & routes
│  │  ├─ model_store.py     Train / load / hold the RF model + metrics
│  │  ├─ data.py            Real (Kaggle) dataset loader + synthetic fallback
│  │  ├─ features.py        Shared feature contract & BMI helper
│  │  ├─ recommendations.py Rule-based lifestyle guidance
│  │  ├─ schemas.py         Pydantic request/response models
│  │  └─ db.py              MySQL prediction logging
│  ├─ train.py              Standalone training script
│  ├─ requirements.txt
│  ├─ data/                 PCOS dataset (.csv, extends the Kaggle original)
│  └─ artifacts/            (generated) model + metrics + db
└─ frontend/
   ├─ src/
   │  ├─ pages/             Home, Assessment, Result, AdminLogin, AdminDashboard
   │  ├─ components/        Navbar, Footer, Disclaimer, RiskGauge
   │  ├─ api.js             Axios API client
   │  └─ App.jsx / main.jsx
   ├─ package.json
   └─ vite.config.js        (proxies /api → backend)
```

---

## Quick start — Docker Compose (recommended)

The simplest way to run everything is `docker compose`, which builds the app
(FastAPI + the built React frontend, served from one process) and starts a
MySQL container alongside it — no XAMPP install, no separate frontend/backend
terminals:

```bash
docker compose up --build
# open http://localhost:8000
```

This starts three containers:

- **mysql** — official `mysql:8.0` image, replacing XAMPP's MySQL for this
  setup; its data persists in a named Docker volume (`mysql_data`) across
  restarts. Root password is set via `MYSQL_ROOT_PASSWORD` in
  [docker-compose.yml](docker-compose.yml) (change it before any shared/
  non-local use).
- **app** — the existing single-service image (see [Dockerfile](Dockerfile)),
  pointed at the `mysql` container via `DB_HOST=mysql`.
- **phpmyadmin** — the actual phpMyAdmin XAMPP ships with, for browsing the
  MySQL database, at [http://localhost:8080](http://localhost:8080). Log in
  with Server `mysql` and the same user/password as the `app` service's
  `DB_*` env vars in `docker-compose.yml`.

Override the demo admin/doctor passwords by exporting `PCOS_ADMIN_PASS` /
`PCOS_DOCTOR_PASS` before running `docker compose up`, or editing
`docker-compose.yml` directly.

To stop everything: `docker compose down` (add `-v` to also wipe the MySQL
volume and start fresh next time).

> Prefer to develop with hot-reload instead? Use the manual setup below —
> it runs the frontend/backend as separate dev servers against either XAMPP's
> MySQL or the same `docker compose up mysql` container (just that one
> service, with `DB_HOST=127.0.0.1` since it's reached from outside Docker).

---

## Manual setup (hot-reload for active development)

### 1. Start MySQL (XAMPP)

The backend logs predictions/prescriptions and stores user accounts in
MySQL. The easiest way to get one locally is [XAMPP](https://www.apachefriends.org/):

1. Install XAMPP and open the **XAMPP Control Panel**.
2. Click **Start** next to **MySQL** (you don't need to start Apache — the
   Python backend serves the API itself).
3. That's it — on first run the backend automatically creates the
   `pcos_care` database and its tables against XAMPP's default MySQL
   credentials (host `127.0.0.1`, port `3306`, user `root`, no password).

Using a different MySQL host/user/password, or a non-XAMPP MySQL/MariaDB
server? Override it with env vars before starting the backend:

```bash
# Windows PowerShell
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "3306"
$env:DB_USER = "root"
$env:DB_PASSWORD = ""
$env:DB_NAME = "pcos_care"
```

### 2. Run the backend

Requires **Python 3.10+**.

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt

# (optional) train explicitly and see the metrics; the API also auto-trains
# on first launch if no model artifact exists.
python train.py

# start the API (http://127.0.0.1:8000, docs at /docs)
uvicorn app.main:app --reload
```

### 3. Run the frontend

Requires **Node.js 18+**.

```bash
cd frontend
npm install
npm run dev
# open http://localhost:5173
```

The Vite dev server proxies `/api/*` to `http://127.0.0.1:8000`, so no CORS
setup is needed in development.

---

## Roles & demo accounts

All roles share the same **/login** form (email + password):

| Role          | Demo email                     | Password       |
| ------------- | ------------------------------- | -------------- |
| Patient       | *(register your own at /register)* | —           |
| Doctor        | `doctor@pcos.ai`                | `doctor123`    |
| Counselor     | `ananya.counselor@pcos.ai` (+ `priya.counselor@pcos.ai`, `fatima.counselor@pcos.ai`) | `counselor123` |
| Admin         | `admin@pcos.ai`                 | `admin123`     |

Override via env vars: `PCOS_ADMIN_EMAIL`/`PCOS_ADMIN_PASS`,
`PCOS_DOCTOR_EMAIL`/`PCOS_DOCTOR_PASS`, `PCOS_COUNSELOR_PASS` (applies to all
three seeded counselors).

- **Patients** pick a doctor or counselor as their care provider (from their
  dashboard, or right from a High-risk result) — they default to the doctor
  until they choose someone else.
- **Counselors** see and can upload prescriptions only for patients who
  selected them.
- **Doctors** have the same unrestricted reach as admins: every patient's
  assessments, and the ability to upload a prescription for anyone —
  regardless of who that patient selected, and regardless of the doctor's own
  availability status. A doctor's prescription also supersedes (but doesn't
  delete) a counselor's earlier one for that patient.
- **Doctors/counselors** can toggle an availability switch so patients know
  who's currently reachable when choosing a provider.
- **Admin** (**/admin**) additionally sees model metrics: accuracy /
  precision / recall / F1 / ROC-AUC, the confusion matrix, feature
  importances, and live usage statistics across every patient.

---

## API

| Method | Endpoint                        | Description                                         |
| ------ | -------------------------------- | ---------------------------------------------------- |
| GET    | `/api/health`                    | Service health                                       |
| POST   | `/api/predict`                   | Run a risk assessment (optionally authenticated)     |
| POST   | `/api/auth/register`             | Patient self-registration                            |
| POST   | `/api/auth/login`                | Login for any role                                   |
| POST   | `/api/auth/forgot-password`      | Request a password reset link                        |
| POST   | `/api/auth/reset-password`       | Set a new password using a reset token               |
| GET    | `/api/auth/me`                   | Current user (auth)                                  |
| GET    | `/api/providers`                 | List doctors & counselors with availability          |
| PATCH  | `/api/provider/availability`     | Toggle own availability (doctor/counselor)           |
| POST   | `/api/patient/select-provider`   | Choose/clear preferred provider (patient)            |
| GET    | `/api/patient/history`           | The patient's own assessments (patient)              |
| GET    | `/api/doctor/assessments`        | Every assessment (doctor/admin); selected patients only (counselor) |
| POST   | `/api/doctor/prescriptions`      | Upload for any patient (doctor/admin); selected patients only (counselor) |
| GET    | `/api/admin/metrics`             | Model evaluation metrics (admin)                     |
| GET    | `/api/admin/stats`               | Aggregate prediction stats (admin)                   |
| POST   | `/api/admin/retrain`             | Retrain the model (admin)                            |

Interactive docs: **http://127.0.0.1:8000/docs**

---

## About the dataset & accuracy

The model trains on `PCOS_extended_dataset.csv` (`backend/data/`) — 2,000
records extending the original Kaggle *"Polycystic ovary syndrome (PCOS)"*
dataset by prasoonkottarathil (541 real patients across 10 hospitals in
Kerala, India). Neither file is fetched automatically (Kaggle requires a
login to download); see [app/data.py](backend/app/data.py) for the loader.

Two of the app's existing inputs — mood swings and family history — aren't
recorded in that dataset, so the assessment form still asks for them (the
rule-based recommendations still use the answers) but the ML model learns
no signal from them; their feature importance is correctly reported as 0.

> ⚠️ **Accuracy caveat:** the extended 2,000-row file appears to extend the
> original 541 real patients via synthetic oversampling (~89% of rows have
> a near-identical neighbor elsewhere in the set). A plain random 80/20
> split therefore leaks near-duplicate patients across train/test, which is
> almost certainly why accuracy reads ~98% — that number is inflated, not a
> trustworthy measure of real-world generalization. The split itself is
> still genuinely computed (not hard-coded); the input data just isn't
> free of leakage. For a leakage-free (and more realistic ~85% accuracy)
> evaluation, train on the original `PCOS_data_without_infertility.xlsx`
> (541 patients, all genuinely distinct) instead — swap `DATASET_PATH` in
> `app/data.py`.

If neither data file is present (e.g. a checkout without them),
`app/data.py` falls back to a fabricated synthetic dataset so the pipeline
still runs end to end, just without any clinical grounding.

---

## Deployment (free)

The app can run as a **single service**: FastAPI serves both the API and the
built React frontend, so there's one URL and no CORS to configure.

### Option A — Render (recommended, free)

1. Push this repo to GitHub.
2. On [render.com](https://render.com): **New → Blueprint**, select the repo
   (it auto-detects [`render.yaml`](render.yaml)).
3. Set `PCOS_ADMIN_PASS` and `PCOS_DOCTOR_PASS` when prompted, then **Apply**.
4. First build takes a few minutes (installs deps + trains the model). Your app
   is then live at `https://<name>.onrender.com`.

> Free-plan caveats: the service **spins down after ~15 min idle** (first
> request then cold-starts in ~30–50 s). The filesystem is also **ephemeral**,
> so uploaded prescriptions reset on each deploy/restart. Predictions and user
> accounts live in MySQL (see below) and aren't affected by this — but Render
> doesn't bundle MySQL, so you'll need `DB_HOST`/`DB_USER`/`DB_PASSWORD`/
> `DB_NAME` pointed at an external MySQL instance (e.g. PlanetScale, Railway,
> or any managed MySQL) rather than XAMPP, which is for local development only.

### Option B — Run the production image locally (Docker)

Use `docker compose` (see [Quick start](#quick-start--docker-compose-recommended)
above) — it builds this same image and also starts the MySQL container the
app needs:

```bash
docker compose up --build
# open http://localhost:8000
```

### Making uploads persist (still free)

The database already persists outside the app's filesystem (MySQL), so the
remaining ephemeral piece on free hosting is uploaded prescription files:

- **Uploaded files** → Supabase Storage or Cloudflare R2 (replace local disk
  writes in the prescription upload/download endpoints).
- **Sessions** → JWTs instead of the in-memory token store in `app/auth.py`.
- Host the backend on **Fly.io** with a small persistent volume if you'd rather
  keep local files for uploads.

### Split deployment (frontend and backend separate)

If you prefer the frontend on Vercel/Netlify and the backend elsewhere:

- Build the frontend with `VITE_API_URL=https://your-backend-url`.
- On the backend, set `ALLOWED_ORIGINS=https://your-frontend-url` (comma-separated
  for multiple origins).

## Future scope

Menstrual-cycle tracking, wearable integration, explainable-AI factor
breakdowns, a mobile app, multilingual support (including Kannada), and
integration with healthcare professionals.
