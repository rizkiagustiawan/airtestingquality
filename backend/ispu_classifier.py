"""
ISPU ML Classifier: Real Data Training with Synthetic Fallback.

Scientific basis:
- Ridho & Mahalisa (2023) "Analisis Klasifikasi Dataset ISPU di Masa Pandemi menggunakan SVM"
- Sajiwo & Rahmat (2024) "Klasifikasi ISPU Menggunakan XGBoost dengan SMOTE"

Uses scikit-learn SVC with RBF kernel.
Trains on REAL data from history_store.db when available.
Falls back to synthetic data based on ISPU breakpoints when no real data exists.
"""

import math
from datetime import datetime, timezone

import numpy as np

from ispu_calculator import get_overall_ispu
from real_data_loader import has_sufficient_real_data, load_ispu_training_data

ISPU_CATEGORIES = [
    {"label": "Baik", "min": 0, "max": 50, "color": "#00e400"},
    {"label": "Sedang", "min": 51, "max": 100, "color": "#0080ff"},
    {"label": "Tidak Sehat", "min": 101, "max": 200, "color": "#ffff00"},
    {"label": "Sangat Tidak Sehat", "min": 201, "max": 300, "color": "#ff0000"},
    {"label": "Berbahaya", "min": 301, "max": 500, "color": "#000000"},
]


def _get_category_idx(ispu_value: int) -> int:
    if ispu_value <= 50:
        return 0
    elif ispu_value <= 100:
        return 1
    elif ispu_value <= 200:
        return 2
    elif ispu_value <= 300:
        return 3
    else:
        return 4


def _generate_synthetic_training_data(n_samples: int = 2000) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic training data based on ISPU breakpoints.
    Used as FALLBACK when no real data is available.
    """
    features = []
    labels = []

    category_ranges = {
        0: {"pm10": (10, 50), "pm25": (3, 15.5), "so2": (5, 52), "no2": (5, 80), "co": (200, 4000)},
        1: {"pm10": (51, 150), "pm25": (16, 55), "so2": (53, 180), "no2": (81, 200), "co": (4001, 8000)},
        2: {"pm10": (151, 350), "pm25": (56, 150), "so2": (181, 400), "no2": (201, 1130), "co": (8001, 15000)},
        3: {"pm10": (351, 420), "pm25": (151, 250), "so2": (401, 800), "no2": (1131, 2260), "co": (15001, 30000)},
        4: {"pm10": (421, 550), "pm25": (251, 400), "so2": (801, 1100), "no2": (2261, 2900), "co": (30001, 44000)},
    }
    category_probs = [0.30, 0.30, 0.25, 0.10, 0.05]

    for _ in range(n_samples):
        cat_idx = np.random.choice(5, p=category_probs)
        ranges = category_ranges[cat_idx]

        pm10 = np.random.uniform(*ranges["pm10"])
        pm25 = np.random.uniform(*ranges["pm25"])
        so2 = np.random.uniform(*ranges["so2"])
        no2 = np.random.uniform(*ranges["no2"])
        co = np.random.uniform(*ranges["co"])

        hour = np.random.randint(0, 24)
        hour_sin = math.sin(2 * math.pi * hour / 24)
        hour_cos = math.cos(2 * math.pi * hour / 24)

        features.append([pm10, pm25, so2, no2, co, hour_sin, hour_cos])
        labels.append(cat_idx)

    return np.array(features), np.array(labels)


class ISPUClassifier:
    """
    SVM-based ISPU classifier.

    Data source priority:
    1. REAL data from history_store.db (when available)
    2. Synthetic fallback based on ISPU breakpoints
    """

    def __init__(self):
        self._model = None
        self._scaler = None
        self._trained = False
        self._category_names = [c["label"] for c in ISPU_CATEGORIES]
        self._train_accuracy = 0.0
        self._data_source = "unknown"
        self._n_samples = 0

    def _ensure_trained(self):
        if self._trained:
            return

        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import SVC
        from sklearn.model_selection import cross_val_score

        # Try loading real data first
        X, y = None, None
        if has_sufficient_real_data(min_records=100):
            X, y, _ = load_ispu_training_data(days=90)
            if len(X) >= 50 and len(np.unique(y)) >= 2:
                self._data_source = "real_database"
                self._n_samples = len(X)

        # Fallback to synthetic
        if X is None or len(X) < 50:
            X, y = _generate_synthetic_training_data(2000)
            self._data_source = "synthetic_breakpoints"
            self._n_samples = len(X)

        # Scale features
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)

        # Train SVM with RBF kernel
        self._model = SVC(
            kernel="rbf",
            C=10.0,
            gamma="scale",
            probability=True,
            random_state=42,
        )
        self._model.fit(X_scaled, y)

        # Cross-validation accuracy
        cv_folds = min(5, min(np.bincount(y)))
        if cv_folds >= 2:
            cv_scores = cross_val_score(
                self._model, X_scaled, y, cv=cv_folds, scoring="accuracy"
            )
            self._train_accuracy = float(np.mean(cv_scores))
        else:
            self._train_accuracy = float(
                np.mean(self._model.predict(X_scaled) == y)
            )

        self._trained = True

    def predict(self, pm10: float, pm25: float, so2: float, no2: float, co: float) -> dict:
        self._ensure_trained()

        now = datetime.now(timezone.utc)
        hour_sin = math.sin(2 * math.pi * now.hour / 24)
        hour_cos = math.cos(2 * math.pi * now.hour / 24)

        features = np.array([[pm10, pm25, so2, no2, co, hour_sin, hour_cos]])
        features_scaled = self._scaler.transform(features)

        predicted_idx = int(self._model.predict(features_scaled)[0])
        proba = self._model.predict_proba(features_scaled)[0]

        # Map probabilities to all 5 categories
        # Model may have been trained on subset of classes
        model_classes = list(self._model.classes_)
        probabilities = {}
        for i in range(5):
            if i in model_classes:
                idx = model_classes.index(i)
                probabilities[self._category_names[i]] = round(float(proba[idx]), 3)
            else:
                probabilities[self._category_names[i]] = 0.0

        confidence = probabilities.get(self._category_names[predicted_idx], 0.0)

        # Breakpoint-based ISPU (ground truth)
        bp_result = get_overall_ispu({
            "pm10": pm10, "pm25": pm25, "so2": so2, "no2": no2, "co": co
        })

        bp_category_idx = _get_category_idx(bp_result["value"] or 0)
        ml_bp_agree = predicted_idx == bp_category_idx

        return {
            "ml_category": self._category_names[predicted_idx],
            "ml_confidence": round(confidence, 3),
            "ml_probabilities": probabilities,
            "ml_train_accuracy": round(self._train_accuracy, 3),
            "ml_data_source": self._data_source,
            "ml_n_training_samples": self._n_samples,
            "ispu_breakpoint": bp_result,
            "ml_bp_agreement": ml_bp_agree,
            "method": "SVM_RBF_sklearn",
            "scientific_basis": "Ridho & Mahalisa (2023) - SVM with RBF kernel",
        }


_classifier = ISPUClassifier()


def classify_ispu(pm10: float, pm25: float, so2: float, no2: float, co: float) -> dict:
    return _classifier.predict(pm10, pm25, so2, no2, co)


def classify_from_measurements(measurements: dict) -> dict:
    return classify_ispu(
        pm10=measurements.get("pm10", 0),
        pm25=measurements.get("pm25", 0),
        so2=measurements.get("so2", 0),
        no2=measurements.get("no2", 0),
        co=measurements.get("co", 0),
    )
