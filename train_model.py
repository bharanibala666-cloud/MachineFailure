"""
train_model.py
==============
Trains the physics-informed XGBoost model used by the web app.

Steps:
  1. Same 80/20 stratified split and XGBoost settings as the original model
  2. Pick the decision threshold with 5-fold cross-validation on the
     TRAINING set only (the test set is never used for tuning)
  3. Evaluate the original raw-feature model and the physics model on the test set
  4. Save the physics model and update config/model_config.json

Run:  python train_model.py
"""
import json
import os
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from services.feature_engineering import (
    PHYSICS_NUMERIC_FEATURES,
    RAW_FEATURES,
    build_physics_pipeline,
)

warnings.filterwarnings("ignore", category=UserWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "dataset", "ai4i2020.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "predictive_maintenance_xgboost_physics.pkl")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "model_config.json")
RESULTS_PATH = os.path.join(BASE_DIR, "results", "physics_vs_baseline.csv")

TARGET = "Machine failure"
XGB_PARAMS = dict(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    random_state=42,
    eval_metric="logloss",
)


def build_baseline_pipeline():
    """The original model: scaled raw sensors + one-hot Type -> XGBoost."""
    preprocessor = ColumnTransformer(transformers=[
        ("num", StandardScaler(), RAW_FEATURES[1:]),
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["Type"]),
    ])
    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", XGBClassifier(**XGB_PARAMS)),
    ])


def choose_threshold(pipeline, X_train, y_train):
    """Threshold that maximises F1 on out-of-fold training predictions."""
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    oof = cross_val_predict(pipeline, X_train, y_train, cv=cv, method="predict_proba")[:, 1]
    candidates = np.round(np.arange(0.10, 0.91, 0.05), 2)
    scores = [f1_score(y_train, oof >= t) for t in candidates]
    return float(candidates[int(np.argmax(scores))])


def evaluate(pipeline, X_test, y_test, threshold):
    proba = pipeline.predict_proba(X_test)[:, 1]
    pred = (proba >= threshold).astype(int)
    return {
        "accuracy": round(accuracy_score(y_test, pred) * 100, 2),
        "precision": round(precision_score(y_test, pred, zero_division=0) * 100, 2),
        "recall": round(recall_score(y_test, pred, zero_division=0) * 100, 2),
        "f1_score": round(f1_score(y_test, pred, zero_division=0) * 100, 2),
        "roc_auc": round(roc_auc_score(y_test, proba) * 100, 2),
        "missed_failures": int(((pred == 0) & (y_test == 1)).sum()),
        "false_alarms": int(((pred == 1) & (y_test == 0)).sum()),
    }


def feature_importance(pipeline):
    """Readable feature importances (%) from the trained physics pipeline."""
    names = PHYSICS_NUMERIC_FEATURES + [
        f"Type {c}" for c in pipeline.named_steps["preprocessor"]
        .named_transformers_["cat"].categories_[0]
    ]
    pretty = {
        "Tool wear [min]": "Tool Wear",
        "Rotational speed [rpm]": "Rotational Speed",
    }
    importances = pipeline.named_steps["classifier"].feature_importances_
    rows = [
        {"feature": pretty.get(n, n), "importance": round(float(v) * 100, 2)}
        for n, v in zip(names, importances)
    ]
    return sorted(rows, key=lambda r: r["importance"], reverse=True)


def main():
    df = pd.read_csv(DATASET_PATH)
    X, y = df[RAW_FEATURES], df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"Train: {len(X_train):,} rows | Test: {len(X_test):,} rows | "
          f"Failure rate: {y.mean() * 100:.2f}%")

    # Original model (raw features, default 0.5 threshold)
    baseline = build_baseline_pipeline().fit(X_train, y_train)
    baseline_metrics = evaluate(baseline, X_test, y_test, threshold=0.5)

    # Physics-informed model
    physics = build_physics_pipeline(XGBClassifier(**XGB_PARAMS))
    threshold = choose_threshold(physics, X_train, y_train)
    physics.fit(X_train, y_train)
    physics_metrics = evaluate(physics, X_test, y_test, threshold)

    print(f"\nDecision threshold (chosen by 5-fold CV on training set): {threshold}")
    print(f"\n{'Metric':<18}{'Original (raw)':>16}{'Physics':>12}")
    for key in baseline_metrics:
        print(f"{key:<18}{baseline_metrics[key]:>16}{physics_metrics[key]:>12}")

    # Save model
    joblib.dump(physics, MODEL_PATH)
    print(f"\nModel saved -> {MODEL_PATH}")

    # Save comparison table
    pd.DataFrame([
        {"Model": "XGBoost (raw features)", **baseline_metrics},
        {"Model": "XGBoost (physics features)", **physics_metrics},
    ]).to_csv(RESULTS_PATH, index=False)
    print(f"Comparison saved -> {RESULTS_PATH}")

    # Update app config
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    config["model"] = {
        "name": "Physics-Informed XGBoost",
        "version": "2.0",
        "type": "predictive_maintenance_xgboost_physics",
        "file": os.path.basename(MODEL_PATH),
        "description": "XGBoost on physics features: Power, Temperature Difference, Strain",
        "threshold": threshold,
    }
    config["metrics"] = {k: physics_metrics[k] for k in
                         ("accuracy", "precision", "recall", "f1_score")}
    config["baseline_metrics"] = {k: baseline_metrics[k] for k in
                                  ("accuracy", "precision", "recall", "f1_score")}
    config["feature_importance"] = feature_importance(physics)

    # Keep the earlier notebook models, refresh both XGBoost entries
    comparison = [m for m in config.get("comparison_models", [])
                  if m["name"] not in ("XGBoost", "Physics XGBoost")]
    comparison.append({"name": "XGBoost", "accuracy": baseline_metrics["accuracy"],
                       "f1_score": baseline_metrics["f1_score"]})
    comparison.append({"name": "Physics XGBoost", "accuracy": physics_metrics["accuracy"],
                       "f1_score": physics_metrics["f1_score"]})
    config["comparison_models"] = comparison
    config["dataset"]["engineered_features"] = [
        "Power [W] = Torque x RPM x 2pi/60",
        "Temp diff [K] = Process temp - Air temp",
        "Strain [min*Nm] = Tool wear x Torque",
    ]

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"Config updated -> {CONFIG_PATH}")


if __name__ == "__main__":
    main()
