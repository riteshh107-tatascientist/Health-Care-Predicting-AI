"""Educational diabetes-risk models trained on the real Pima Indians Diabetes dataset.

Dataset: National Institute of Diabetes and Digestive and Kidney Diseases (NIDDK), distributed
via the UCI Machine Learning Repository. 768 female patients of Pima Indian heritage, aged 21+.

Leakage control: every preprocessing step (zero-to-missing, median imputation, scaling) lives
inside a Pipeline that is fitted only on training folds. The held-out test set is touched once,
for the final report. Model selection uses cross-validation on the training split only.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, brier_score_loss, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import config

FEATURES = ["Pregnancies", "Glucose", "BloodPressure", "SkinThickness", "Insulin",
            "BMI", "DiabetesPedigreeFunction", "Age"]
TARGET = "Outcome"
COLUMNS = FEATURES + [TARGET]
ZERO_IS_MISSING = ["Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI"]
MODEL_NAMES = ("Logistic Regression", "Random Forest")
RANDOM_STATE = 42
TEST_SIZE = 0.2
THRESHOLD = 0.5


class ZeroToNaN(BaseEstimator, TransformerMixin):
    """Physiologically impossible zeros (e.g. BMI = 0) mean 'not recorded'; mark them missing."""

    def __init__(self, column_indices=()):
        self.column_indices = tuple(column_indices)

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = np.array(X, dtype=float, copy=True)
        for idx in self.column_indices:
            X[X[:, idx] == 0, idx] = np.nan
        return X


ZERO_IDX = [FEATURES.index(c) for c in ZERO_IS_MISSING]


def build_pipeline(name: str) -> Pipeline:
    if name == "Logistic Regression":
        estimator = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE)
    elif name == "Random Forest":
        estimator = RandomForestClassifier(n_estimators=300, min_samples_leaf=3, class_weight="balanced",
                                           random_state=RANDOM_STATE, n_jobs=1)
    else:
        raise ValueError(f"Unknown model: {name}")
    return Pipeline([
        ("zero_to_nan", ZeroToNaN(ZERO_IDX)),
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", estimator),
    ])


def load_dataset(path: Path | str | None = None) -> pd.DataFrame:
    path = Path(path or config.DATASET_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at {path}. Expected data/diabetes.csv.")
    raw = pd.read_csv(path)
    if not set(COLUMNS).issubset(raw.columns):
        raw = pd.read_csv(path, header=None, names=COLUMNS)  # the UCI file has no header row
    df = raw[COLUMNS].apply(pd.to_numeric, errors="coerce")
    if df.isna().any().any():
        raise ValueError("Dataset contains non-numeric or missing values.")
    if not set(df[TARGET].unique()).issubset({0, 1}):
        raise ValueError("Outcome column must contain only 0 and 1.")
    return df.reset_index(drop=True)


def dataset_summary(df: pd.DataFrame) -> dict:
    return {
        "rows": int(len(df)),
        "positive_cases": int((df[TARGET] == 1).sum()),
        "negative_cases": int((df[TARGET] == 0).sum()),
        "positive_rate": float(df[TARGET].mean()),
        "zero_values_treated_as_missing": {c: int((df[c] == 0).sum()) for c in ZERO_IS_MISSING},
    }


def _importance(pipe: Pipeline, name: str) -> dict[str, float]:
    model = pipe.named_steps["model"]
    if name == "Random Forest":
        values = model.feature_importances_
    else:
        values = np.abs(model.coef_[0])
        values = values / values.sum()
    return {f: float(v) for f, v in zip(FEATURES, values)}


def train_and_evaluate(df: pd.DataFrame | None = None) -> dict:
    df = load_dataset() if df is None else df
    X = df[FEATURES].to_numpy(dtype=float)
    y = df[TARGET].to_numpy(dtype=int)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    cv_results, test_results, fitted, importances = {}, {}, {}, {}
    for name in MODEL_NAMES:
        pipe = build_pipeline(name)
        scores = cross_validate(pipe, X_tr, y_tr, cv=cv,
                                scoring={"roc_auc": "roc_auc", "f1": "f1", "recall": "recall"})
        cv_results[name] = {
            "roc_auc_mean": float(scores["test_roc_auc"].mean()),
            "roc_auc_std": float(scores["test_roc_auc"].std()),
            "f1_mean": float(scores["test_f1"].mean()),
            "recall_mean": float(scores["test_recall"].mean()),
        }
        pipe.fit(X_tr, y_tr)
        proba = pipe.predict_proba(X_te)[:, 1]
        pred = (proba >= THRESHOLD).astype(int)
        fpr, tpr, _ = roc_curve(y_te, proba)
        test_results[name] = {
            "accuracy": float(accuracy_score(y_te, pred)),
            "precision": float(precision_score(y_te, pred, zero_division=0)),
            "recall": float(recall_score(y_te, pred, zero_division=0)),
            "f1": float(f1_score(y_te, pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_te, proba)),
            "brier": float(brier_score_loss(y_te, proba)),
            "confusion": confusion_matrix(y_te, pred, labels=[0, 1]).tolist(),
            "fpr": fpr.tolist(),
            "tpr": tpr.tolist(),
        }
        fitted[name] = pipe
        importances[name] = _importance(pipe, name)

    baseline = DummyClassifier(strategy="most_frequent").fit(X_tr, y_tr)
    best = max(MODEL_NAMES, key=lambda n: cv_results[n]["roc_auc_mean"])
    return {
        "dataset": dataset_summary(df),
        "split": {"train_rows": int(len(y_tr)), "test_rows": int(len(y_te)), "test_size": TEST_SIZE,
                  "stratified": True, "random_state": RANDOM_STATE},
        "cv": cv_results,
        "test": test_results,
        "baseline_accuracy": float(accuracy_score(y_te, baseline.predict(X_te))),
        "best_model": best,
        "importance": importances,
        "models": fitted,
    }


def predict_probability(pipe: Pipeline, values: dict) -> float:
    row = np.array([[float(values[f]) for f in FEATURES]], dtype=float)
    return float(pipe.predict_proba(row)[0, 1])


def save_artifacts(result: dict, folder: Path | None = None) -> dict:
    """Persist the best fitted pipeline and metrics (JSON) for reproducibility."""
    import joblib

    folder = Path(folder or config.MODEL_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    model_path = folder / "best_model.joblib"
    metrics_path = folder / "metrics.json"
    joblib.dump(result["models"][result["best_model"]], model_path)
    serializable = {k: v for k, v in result.items() if k not in ("models",)}
    metrics_path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    return {"model": str(model_path), "metrics": str(metrics_path)}


if __name__ == "__main__":
    outcome = train_and_evaluate()
    paths = save_artifacts(outcome)
    print(json.dumps({k: v for k, v in outcome.items() if k != "models"}, indent=2))
    print("Saved:", paths)
