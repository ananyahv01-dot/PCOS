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
     (Tailwind)                     (scikit-learn)         (+ SQLite log)
```

| Layer            | Technology                                |
| ---------------- | ----------------------------------------- |
| Frontend         | React.js + Vite, Tailwind CSS, Recharts   |
| Backend / API    | FastAPI (Python)                          |
| Machine Learning | scikit-learn — RandomForestClassifier     |
| Data processing  | Pandas, NumPy                             |
| Storage          | SQLite (swap for MongoDB/MySQL later)     |

---

## Project layout

```
AI/
├─ backend/
│  ├─ app/
│  │  ├─ main.py            FastAPI app & routes
│  │  ├─ model_store.py     Train / load / hold the RF model + metrics
│  │  ├─ data.py            Synthetic dataset generator
│  │  ├─ features.py        Shared feature contract & BMI helper
│  │  ├─ recommendations.py Rule-based lifestyle guidance
│  │  ├─ schemas.py         Pydantic request/response models
│  │  └─ db.py              SQLite prediction logging
│  ├─ train.py              Standalone training script
│  ├─ requirements.txt
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

## 1. Run the backend

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

## 2. Run the frontend

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

## Admin dashboard

- Visit **/admin** and log in with the demo credentials:
  - **username:** `admin`
  - **password:** `admin123`
- Override in production via env vars `PCOS_ADMIN_USER` / `PCOS_ADMIN_PASS`.
- The dashboard shows accuracy / precision / recall / F1 / ROC-AUC, the
  confusion matrix, feature importances, and live usage statistics.

---

## API

| Method | Endpoint              | Description                          |
| ------ | --------------------- | ------------------------------------ |
| GET    | `/api/health`         | Service health                       |
| POST   | `/api/predict`        | Run a risk assessment                |
| POST   | `/api/admin/login`    | Get a demo admin token               |
| GET    | `/api/admin/metrics`  | Model evaluation metrics (auth)      |
| GET    | `/api/admin/stats`    | Aggregate prediction stats (auth)    |
| POST   | `/api/admin/retrain`  | Retrain the model (auth)             |

Interactive docs: **http://127.0.0.1:8000/docs**

---

## About the dataset & accuracy

This project ships with a **synthetic dataset generator** (`app/data.py`) so the
full pipeline runs without any external data file. Metrics reported in the
dashboard come from a genuine 80/20 train/test split on that synthetic data —
they are **not** hard-coded. To use real data, replace `generate_dataset()` with
a loader for a validated clinical dataset (e.g. the public Kaggle *PCOS*
dataset) that returns a DataFrame with the same feature columns, then rerun
`python train.py`.

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
> request then cold-starts in ~30–50 s), and the filesystem is **ephemeral** —
> the SQLite DB and uploaded prescriptions reset on each deploy/restart.

### Option B — Run the production image locally (Docker)

```bash
docker build -t pcos-care-ai .
docker run -p 8000:8000 -e PORT=8000 pcos-care-ai
# open http://localhost:8000
```

### Making data persist (still free)

For real persistence instead of ephemeral SQLite/disk:

- **Database** → managed Postgres on [Neon](https://neon.tech) or
  [Supabase](https://supabase.com) (swap the `sqlite3` calls in `app/db.py`).
- **Uploaded files** → Supabase Storage or Cloudflare R2 (replace local disk
  writes in the prescription upload/download endpoints).
- **Sessions** → JWTs instead of the in-memory token store in `app/auth.py`.
- Host the backend on **Fly.io** with a small persistent volume if you'd rather
  keep SQLite + local files.

### Split deployment (frontend and backend separate)

If you prefer the frontend on Vercel/Netlify and the backend elsewhere:

- Build the frontend with `VITE_API_URL=https://your-backend-url`.
- On the backend, set `ALLOWED_ORIGINS=https://your-frontend-url` (comma-separated
  for multiple origins).

## Future scope

Menstrual-cycle tracking, wearable integration, explainable-AI factor
breakdowns, a mobile app, multilingual support (including Kannada), and
integration with healthcare professionals.
