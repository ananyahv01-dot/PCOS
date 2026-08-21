# syntax=docker/dockerfile:1

# ------------------------------------------------------------------ #
# Stage 1 — build the React (Vite) frontend into static files
# ------------------------------------------------------------------ #
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
# Only copy package.json (the lockfile is .dockerignore'd because it may pin a
# private registry that isn't reachable from inside the build).
COPY frontend/package.json ./
# Force the public npm registry so the build never inherits a private one.
RUN npm install --registry=https://registry.npmjs.org/ --no-audit --no-fund
COPY frontend/ ./
# Same-origin deploy: the API is served from the same host, so relative
# /api URLs work. (For a split deploy, pass VITE_API_URL at build time.)
RUN npm run build

# ------------------------------------------------------------------ #
# Stage 2 — Python backend (also serves the built frontend)
# ------------------------------------------------------------------ #
FROM python:3.12-slim
WORKDIR /app

# System deps kept minimal; scikit-learn/numpy ship manylinux wheels.
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend source
COPY backend/ ./

# Built frontend from stage 1
COPY --from=frontend /app/frontend/dist ./frontend_dist
ENV FRONTEND_DIST=/app/frontend_dist

# Train the model at build time so it is baked into the image (no cold-start
# training on first request).
RUN python -c "from app.model_store import train_and_save; train_and_save()"

# Render/most PaaS provide $PORT; default to 8000 locally.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
