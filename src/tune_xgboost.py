import os
import math
import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    confusion_matrix
)
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from src.feature_engineering import (
    add_behavioral_features,
    get_feature_columns
)
from src.ml_pipeline import create_preprocessor


TRAIN_PATH = "data/processed/train.csv"
VALIDATION_PATH = "data/processed/validation.csv"
BEST_MODEL_PATH = "models/xgboost_fraud_model.pkl"


def load_data():
    train_df = pd.read_csv(TRAIN_PATH)
    validation_df = pd.read_csv(VALIDATION_PATH)

    train_df["split"] = "train"
    validation_df["split"] = "validation"

    df = pd.concat([train_df, validation_df], ignore_index=True)
    return df


def evaluate_predictions(y_true, probabilities):
    roc_auc = roc_auc_score(y_true, probabilities)
    pr_auc = average_precision_score(y_true, probabilities)

    best_threshold = 0.5
    best_f1 = 0.0
    best_precision = 0.0
    best_recall = 0.0
    best_cm = None

    for t in [x / 100 for x in range(5, 95, 5)]:
        preds = (probabilities >= t).astype(int)
        prec = precision_score(y_true, preds, zero_division=0)
        rec = recall_score(y_true, preds, zero_division=0)
        f1 = f1_score(y_true, preds, zero_division=0)

        if f1 > best_f1:
            best_f1 = f1
            best_threshold = t
            best_precision = prec
            best_recall = rec
            best_cm = confusion_matrix(y_true, preds)

    # In case no threshold produced F1 > 0, fallback to 0.5
    if best_cm is None:
        preds = (probabilities >= 0.5).astype(int)
        best_precision = precision_score(y_true, preds, zero_division=0)
        best_recall = recall_score(y_true, preds, zero_division=0)
        best_f1 = f1_score(y_true, preds, zero_division=0)
        best_cm = confusion_matrix(y_true, preds)

    return {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "best_threshold": best_threshold,
        "precision": best_precision,
        "recall": best_recall,
        "f1": best_f1,
        "confusion_matrix": best_cm
    }


def run_tuning():
    print("=" * 75)
    print("STAGE 2: CONTROLLED XGBOOST EXPERIMENTATION & TUNING")
    print("=" * 75)

    print("\n1. Loading and engineering features...")
    df = load_data()
    df = add_behavioral_features(df)
    features = get_feature_columns()

    train_df = df[df["split"] == "train"].copy()
    val_df = df[df["split"] == "validation"].copy()

    X_train = train_df[features]
    y_train = train_df["label"]
    X_val = val_df[features]
    y_val = val_df["label"]

    fraud_count = y_train.sum()
    legit_count = len(y_train) - fraud_count
    full_ratio = legit_count / fraud_count
    sqrt_ratio = math.sqrt(full_ratio)

    print(f"Features: {len(features)}")
    print(f"Train samples: {len(X_train)} (Fraud: {fraud_count}, Legit: {legit_count}, Ratio: {full_ratio:.2f})")
    print(f"Validation samples: {len(X_val)} (Fraud: {y_val.sum()})")

    # Define controlled experiment matrix
    experiments = [
        {
            "name": "Exp 1: Baseline Candidate (Depth=6, ScaleWeight=Full)",
            "params": {
                "n_estimators": 300,
                "max_depth": 6,
                "learning_rate": 0.05,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "scale_pos_weight": full_ratio,
                "reg_alpha": 0.0,
                "reg_lambda": 1.0,
            }
        },
        {
            "name": "Exp 2: Shallow Trees / Low Complexity (Depth=3, ScaleWeight=Full)",
            "params": {
                "n_estimators": 200,
                "max_depth": 3,
                "learning_rate": 0.05,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "scale_pos_weight": full_ratio,
                "reg_alpha": 0.0,
                "reg_lambda": 1.0,
            }
        },
        {
            "name": "Exp 3: Moderate Depth + Regularization (Depth=4, L2=3.0, ScaleWeight=Full)",
            "params": {
                "n_estimators": 250,
                "max_depth": 4,
                "learning_rate": 0.03,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "scale_pos_weight": full_ratio,
                "reg_alpha": 1.0,
                "reg_lambda": 3.0,
            }
        },
        {
            "name": "Exp 4: Dampened Class Weight (Depth=4, ScaleWeight=SqrtRatio=7.72)",
            "params": {
                "n_estimators": 250,
                "max_depth": 4,
                "learning_rate": 0.04,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "scale_pos_weight": sqrt_ratio,
                "reg_alpha": 0.5,
                "reg_lambda": 2.0,
            }
        },
        {
            "name": "Exp 5: Unweighted Trees + Pure Logloss (Depth=4, ScaleWeight=1.0)",
            "params": {
                "n_estimators": 250,
                "max_depth": 4,
                "learning_rate": 0.05,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "scale_pos_weight": 1.0,
                "reg_alpha": 0.5,
                "reg_lambda": 2.0,
            }
        }
    ]

    results = []
    trained_pipelines = {}

    for exp in experiments:
        name = exp["name"]
        params = exp["params"]
        print(f"\nEvaluating: {name}...")

        preprocessor = create_preprocessor(features)
        model = XGBClassifier(
            **params,
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            random_state=42,
            n_jobs=-1
        )

        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("model", model)
        ])

        pipeline.fit(X_train, y_train)
        probs = pipeline.predict_proba(X_val)[:, 1]

        metrics = evaluate_predictions(y_val, probs)
        trained_pipelines[name] = (pipeline, metrics, probs)

        print(f"  -> ROC-AUC: {metrics['roc_auc']:.6f} | PR-AUC: {metrics['pr_auc']:.6f}")
        print(f"  -> Best Threshold: {metrics['best_threshold']:.2f} | Precision: {metrics['precision']:.4f} | Recall: {metrics['recall']:.4f} | F1: {metrics['f1']:.4f}")

        results.append({
            "Experiment": name,
            "ROC-AUC": metrics["roc_auc"],
            "PR-AUC": metrics["pr_auc"],
            "Threshold": metrics["best_threshold"],
            "Precision": metrics["precision"],
            "Recall": metrics["recall"],
            "F1": metrics["f1"]
        })

    summary_df = pd.DataFrame(results)
    print("\n" + "=" * 75)
    print("EXPERIMENT COMPARISON SUMMARY")
    print("=" * 75)
    print(summary_df.to_string(index=False))

    # Select best model: prioritize PR-AUC and ROC-AUC among models meeting operational recall (>=10%)
    operational_candidates = summary_df[summary_df["Recall"] >= 0.10]
    if not operational_candidates.empty:
        best_row = operational_candidates.sort_values(by=["PR-AUC", "ROC-AUC"], ascending=False).iloc[0]
    else:
        best_row = summary_df.sort_values(by=["F1", "PR-AUC"], ascending=False).iloc[0]
    best_name = best_row["Experiment"]
    print(f"\n--> Selected Operational Model: {best_name}")

    best_pipeline, best_metrics, best_probs = trained_pipelines[best_name]

    os.makedirs("models", exist_ok=True)
    joblib.dump(best_pipeline, BEST_MODEL_PATH)
    print(f"Saved best candidate model to {BEST_MODEL_PATH}")

    return summary_df, best_name, best_metrics, best_probs


if __name__ == "__main__":
    run_tuning()
