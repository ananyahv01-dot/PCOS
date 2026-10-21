"""
Train the ultrasound PCOM classifier.

Usage:
    python train_ultrasound.py /path/to/Ultrasound

The directory must contain `infected/` and `noninfected/` image folders.
Writes models/ultrasound_model.joblib and models/ultrasound_metrics.json.
"""

import json
import sys

from app.ultrasound import train_and_save

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(json.dumps(train_and_save(sys.argv[1]), indent=2))
