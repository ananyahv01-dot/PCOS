"""
Standalone training entry point.

Run from the `backend` directory:
    python train.py

This trains the Random Forest on the (synthetic) dataset, evaluates it on a
held-out test split and writes the model + metrics into ./artifacts/.
"""

from __future__ import annotations

import json

from app.model_store import train_and_save


def main() -> None:
    print("Training Random Forest PCOS classifier ...")
    metrics = train_and_save()
    print("\nDone. Evaluation on held-out test set:")
    for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        print(f"  {key:10s}: {metrics[key]:.4f}")
    print("\n  confusion_matrix:", metrics["confusion_matrix"])
    print("\n  Top features:")
    for item in metrics["feature_importance"][:5]:
        print(f"    {item['label']:35s} {item['importance']:.4f}")
    print("\nArtifacts written to ./artifacts/  (metrics.json shown below)\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
