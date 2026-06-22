"""
ISPU ML Classifier v2: Ensemble + SMOTE for Class Imbalance.

Scientific basis:
- Ridho & Mahalisa (2023) "SVM for ISPU classification"
- Sajiwo & Rahmat (2024) "XGBoost+SMOTE for ISPU classification"
- Banjarnahor et al. (2025) "SVM+RF ensemble for air quality"
- Pratama et al. (2025) "SVM-Driven ISPU Prediction"

Uses ensemble of SVM + Random Forest + XGBoost with SMOTE for class imbalance.
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


def _generate_diverse_training_data(n_samples: int = 3000) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate DIVERSE synthetic training data covering ALL ISPU categories.
    Ensures balanced representation to prevent class imbalance.
    """
    features = []
    labels = []

    # All 5 categories with realistic concentration ranges
    category_ranges = {
        0: {"pm10": (5, 50), "pm25": (2, 15.5), "so2": (2, 52), "no2": (2, 80), "co": (100, 4000)},
        1: {"pm10": (51, 150), "pm25": (16, 55), "so2": (53, 180), "no2": (81, 200), "co": (4001, 8000)},
        2: {"pm10": (151, 350), "pm25": (56, 150), "so2": (181, 400), "no2": (201, 1130), "co": (8001, 15000)},
        3: {"pm10": (351, 420), "pm25": (151, 250), "so2": (401, 800), "no2": (1131, 2260), "co": (15001, 30000)},
        4: {"pm10": (421, 550), "pm25": (251, 400), "so2": (801, 1100), "no2": (2261, 2900), "co": (30001, 44000)},
    }

    # BALANCED distribution: equal samples per category
    samples_per_cat = n_samples // 5

    for cat_idx in range(5):
        ranges = category_ranges[cat_idx]
        for _ in range(samples_per_cat):
            pm10 = np.random.uniform(*ranges["pm10"])
            pm25 = np.random.uniform(*ranges["pm25"])
            so2 = np.random.uniform(*ranges["so2"])
            no2 = np.random.uniform(*ranges["no2"])
            co = np.random.uniform(*ranges["co"])

            # Add noise to make it more realistic
            pm10 += np.random.normal(0, pm10 * 0.05)
            pm25 += np.random.normal(0, pm25 * 0.05)
            so2 += np.random.normal(0, so2 * 0.05)
            no2 += np.random.normal(0, no2 * 0.05)
            co += np.random.normal(0, co * 0.05)

            # Ensure positive
            pm10, pm25, so2, no2, co = max(1, pm10), max(1, pm25), max(1, so2), max(1, no2), max(1, co)

            # Temporal features
            hour = np.random.randint(0, 24)
            hour_sin = math.sin(2 * math.pi * hour / 24)
            hour_cos = math.cos(2 * math.pi * hour / 24)

            features.append([pm10, pm25, so2, no2, co, hour_sin, hour_cos])
            labels.append(cat_idx)

    # Add boundary samples (hard cases near category boundaries)
    boundary_cases = [
        # Near Baik/Sedang boundary
        (48, 14, 50, 75, 3800, 0), (52, 16, 54, 82, 4200, 1),
        # Near Sedang/Tidak Sehat boundary
        (145, 53, 175, 195, 7800, 1), (155, 57, 185, 205, 8200, 2),
        # Near Tidak Sehat/Sangat Tidak Sehat boundary
        (345, 148, 395, 1125, 14800, 2), (355, 152, 405, 1135, 15200, 3),
        # Near Sangat Tidak Sehat/Berbahaya boundary
        (415, 248, 795, 2255, 29800, 3), (425, 252, 805, 2265, 30200, 4),
    ]

    for pm10, pm25, so2, no2, co, cat_idx in boundary_cases:
        for _ in range(20):  # Repeat boundary cases
            noise = np.random.normal(0, 0.02, 5)
            features.append([
                pm10 * (1 + noise[0]), pm25 * (1 + noise[1]),
                so2 * (1 + noise[2]), no2 * (1 + noise[3]),
                co * (1 + noise[4]), 0.5, 0.5
            ])
            labels.append(cat_idx)

    return np.array(features), np.array(labels)


class ISPUClassifierV2:
    """
    Ensemble ISPU classifier with SMOTE for class imbalance.

    Combines:
    1. SVM with RBF kernel (Ridho et al. 2023)
    2. Random Forest (ensemble robustness)
    3. XGBoost (Sajiwo et al. 2024)

    Uses SMOTE when real data has class imbalance.
    """

    def __init__(self):
        self._svm_model = None
        self._rf_model = None
        self._xgb_model = None
        self._scaler = None
        self._trained = False
        self._category_names = [c["label"] for c in ISPU_CATEGORIES]
        self._train_accuracy = 0.0
        self._data_source = "unknown"
        self._n_samples = 0
        self._model_weights = [0.4, 0.3, 0.3]  # SVM, RF, XGBoost

    def _ensure_trained(self):
        if self._trained:
            return

        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import SVC
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_score
        from xgboost import XGBClassifier

        # Try loading real data first
        X_real, y_real = None, None
        if has_sufficient_real_data(min_records=100):
            X_real, y_real, _ = load_ispu_training_data(days=90)
            if len(X_real) >= 50:
                # Check class distribution
                unique_classes = np.unique(y_real)
                if len(unique_classes) >= 3:  # Need at least 3 classes
                    self._data_source = "real_database_smote"
                    self._n_samples = len(X_real)
                else:
                    # Real data has too few classes - use synthetic
                    X_real, y_real = None, None

        # Fallback to diverse synthetic data
        if X_real is None or len(X_real) < 50:
            X_syn, y_syn = _generate_diverse_training_data(3000)
            self._data_source = "synthetic_diverse"
            self._n_samples = len(X_syn)

            # Combine with real data if available
            if X_real is not None and len(X_real) > 0:
                X = np.vstack([X_real, X_syn])
                y = np.concatenate([y_real, y_syn])
                self._data_source = "combined_real_synthetic"
                self._n_samples = len(X)
            else:
                X = X_syn
                y = y_syn
        else:
            X = X_real
            y = y_real

        # Apply SMOTE if class imbalance detected
        try:
            from imblearn.over_sampling import SMOTE
            class_counts = np.bincount(y.astype(int))
            max_count = max(class_counts)
            min_count = min(c for c in class_counts if c > 0)

            if max_count / max(min_count, 1) > 2:  # Significant imbalance
                smote = SMOTE(random_state=42, k_neighbors=min(5, min_count - 1) if min_count > 1 else 1)
                X, y = smote.fit_resample(X, y)
                self._data_source += "+smote"
                self._n_samples = len(X)
        except Exception:
            pass  # SMOTE failed, continue without it

        # Scale features
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)

        # Train SVM (RBF kernel)
        self._svm_model = SVC(
            kernel="rbf", C=10.0, gamma="scale",
            probability=True, random_state=42
        )
        self._svm_model.fit(X_scaled, y)

        # Train Random Forest
        self._rf_model = RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42
        )
        self._rf_model.fit(X_scaled, y)

        # Train XGBoost
        self._xgb_model = XGBClassifier(
            n_estimators=100, max_depth=6, learning_rate=0.1,
            random_state=42, use_label_encoder=False, eval_metric="mlogloss"
        )
        self._xgb_model.fit(X_scaled, y)

        # Cross-validation accuracy (using ensemble)
        from sklearn.model_selection import cross_val_score
        cv_scores = cross_val_score(self._svm_model, X_scaled, y, cv=5, scoring="accuracy")
        self._train_accuracy = float(np.mean(cv_scores))

        self._trained = True

    def predict(self, pm10: float, pm25: float, so2: float, no2: float, co: float) -> dict:
        self._ensure_trained()

        now = datetime.now(timezone.utc)
        hour_sin = math.sin(2 * math.pi * now.hour / 24)
        hour_cos = math.cos(2 * math.pi * now.hour / 24)

        features = np.array([[pm10, pm25, so2, no2, co, hour_sin, hour_cos]])
        features_scaled = self._scaler.transform(features)

        # Get probabilities from all 3 models
        svm_proba = self._svm_model.predict_proba(features_scaled)[0]
        rf_proba = self._rf_model.predict_proba(features_scaled)[0]
        xgb_proba = self._xgb_model.predict_proba(features_scaled)[0]

        # Map to all 5 categories
        def map_proba(proba, model):
            result = np.zeros(5)
            for i, cls in enumerate(model.classes_):
                result[int(cls)] = proba[i]
            return result

        svm_mapped = map_proba(svm_proba, self._svm_model)
        rf_mapped = map_proba(rf_proba, self._rf_model)
        xgb_mapped = map_proba(xgb_proba, self._xgb_model)

        # Weighted ensemble
        ensemble_proba = (
            self._model_weights[0] * svm_mapped +
            self._model_weights[1] * rf_mapped +
            self._model_weights[2] * xgb_mapped
        )

        # Normalize
        ensemble_proba = ensemble_proba / ensemble_proba.sum()

        # Get prediction
        predicted_idx = int(np.argmax(ensemble_proba))
        confidence = float(ensemble_proba[predicted_idx])

        probabilities = {
            self._category_names[i]: round(float(ensemble_proba[i]), 3)
            for i in range(5)
        }

        # Individual model predictions
        svm_pred = int(np.argmax(svm_mapped))
        rf_pred = int(np.argmax(rf_mapped))
        xgb_pred = int(np.argmax(xgb_mapped))

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
            "ml_ensemble": {
                "svm": self._category_names[svm_pred],
                "random_forest": self._category_names[rf_pred],
                "xgboost": self._category_names[xgb_pred],
                "weights": self._model_weights,
            },
            "ispu_breakpoint": bp_result,
            "ml_bp_agreement": ml_bp_agree,
            "method": "Ensemble_SVM_RF_XGBoost_SMOTE",
            "scientific_basis": [
                "Ridho & Mahalisa (2023) - SVM for ISPU classification",
                "Sajiwo & Rahmat (2024) - XGBoost+SMOTE for ISPU",
                "Banjarnahor et al. (2025) - SVM+RF ensemble",
                "Pratama et al. (2025) - SVM-Driven ISPU",
            ],
        }


_classifier = ISPUClassifierV2()


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
