"""
Ultrasound image classifier for polycystic ovarian morphology (PCOM).

Trained on the Kaggle "PCOS ultrasound" dataset (folders `infected` /
`noninfected`). Images are converted to small grayscale arrays and fed
through a StandardScaler -> PCA -> SVM pipeline, which keeps the model a
few MB with no deep-learning runtime in the Docker image.

The trained model is committed under `backend/models/` (the dataset is not)
so the image does not need the dataset at build time. Retrain with:

    python train_ultrasound.py /path/to/Ultrasound
"""

from __future__ import annotations

import io
import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
from PIL import Image, ImageOps

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "ultrasound_model.joblib")
METRICS_PATH = os.path.join(MODEL_DIR, "ultrasound_metrics.json")

IMAGE_SIZE = 64
CLASSES = {"infected": 1, "noninfected": 0}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def image_to_features(img: Image.Image) -> np.ndarray:
    """Grayscale, equalise contrast, resize and flatten to [0, 1] floats."""
    img = ImageOps.exif_transpose(img).convert("L")
    img = ImageOps.equalize(img)
    img = img.resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.BILINEAR)
    return np.asarray(img, dtype=np.float32).ravel() / 255.0


def bytes_to_features(data: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(data)) as img:
        return image_to_features(img)


def load_dataset(root: str) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for folder, label in CLASSES.items():
        class_dir = os.path.join(root, folder)
        for fname in sorted(os.listdir(class_dir)):
            if os.path.splitext(fname)[1].lower() not in IMAGE_EXTS:
                continue
            try:
                with Image.open(os.path.join(class_dir, fname)) as img:
                    X.append(image_to_features(img))
                y.append(label)
            except OSError:
                continue  # skip unreadable files
    return np.stack(X), np.array(y)


def train_and_save(dataset_dir: str, seed: int = 42) -> dict:
    from sklearn.decomposition import PCA
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC

    X, y = load_dataset(dataset_dir)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    model = make_pipeline(
        StandardScaler(),
        PCA(n_components=150, random_state=seed),
        SVC(kernel="rbf", C=10, gamma="scale", probability=True,
            class_weight="balanced", random_state=seed),
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_images": int(len(y)),
        "n_infected": int(y.sum()),
        "n_noninfected": int(len(y) - y.sum()),
        "image_size": IMAGE_SIZE,
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred)), 4),
        "recall": round(float(recall_score(y_test, y_pred)), 4),
        "f1": round(float(f1_score(y_test, y_pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_proba)), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
    }

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH, compress=3)
    with open(METRICS_PATH, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    return metrics


class UltrasoundStore:
    def __init__(self) -> None:
        self.model = None
        self.metrics: dict | None = None

    def load(self) -> None:
        if os.path.exists(MODEL_PATH):
            self.model = joblib.load(MODEL_PATH)
        if os.path.exists(METRICS_PATH):
            with open(METRICS_PATH, encoding="utf-8") as fh:
                self.metrics = json.load(fh)

    @property
    def available(self) -> bool:
        return self.model is not None

    def predict_proba(self, data: bytes) -> float:
        """Probability that the ultrasound shows polycystic morphology."""
        if self.model is None:
            raise RuntimeError("Ultrasound model not loaded.")
        features = bytes_to_features(data).reshape(1, -1)
        return float(self.model.predict_proba(features)[0, 1])


ultrasound_store = UltrasoundStore()
