import json
import joblib
import pandas as pd

from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score
)

from src.feature_engineering import (
    add_behavioral_features,
    get_feature_columns
)


TRAIN_PATH = "data/processed/train.csv"
VALIDATION_PATH = "data/processed/validation.csv"

MODEL_PATH = "models/xgboost_fraud_model.pkl"
THRESHOLD_PATH = "models/threshold.json"
PREDICTIONS_PATH = "models/validation_predictions.csv"


def load_data():

    train_df = pd.read_csv(TRAIN_PATH)
    validation_df = pd.read_csv(VALIDATION_PATH)

    train_df["split"] = "train"
    validation_df["split"] = "validation"

    df = pd.concat(
        [train_df, validation_df],
        ignore_index=True
    )

    return df


def evaluate_model(model_path=MODEL_PATH):

    df = load_data()

    df = add_behavioral_features(df)

    features = get_feature_columns()

    validation_df = df[
        df["split"] == "validation"
    ].copy()

    X_validation = validation_df[features]
    y_validation = validation_df["label"]

    model = joblib.load(model_path)

    probabilities = model.predict_proba(
        X_validation
    )[:, 1]

    roc_auc = roc_auc_score(
        y_validation,
        probabilities
    )

    pr_auc = average_precision_score(
        y_validation,
        probabilities
    )

    best_threshold = 0.5
    best_f1 = 0
    best_precision = 0
    best_recall = 0

    for threshold in [
        x / 100
        for x in range(5, 95, 5)
    ]:

        predictions = (
            probabilities >= threshold
        ).astype(int)

        precision = precision_score(
            y_validation,
            predictions,
            zero_division=0
        )

        recall = recall_score(
            y_validation,
            predictions,
            zero_division=0
        )

        f1 = f1_score(
            y_validation,
            predictions,
            zero_division=0
        )

        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
            best_precision = precision
            best_recall = recall

    final_predictions = (
        probabilities >= best_threshold
    ).astype(int)

    matrix = confusion_matrix(
        y_validation,
        final_predictions
    )

    prediction_df = validation_df[
        [
            "transaction_id",
            "user_id",
            "timestamp",
            "label"
        ]
    ].copy()

    prediction_df["fraud_probability"] = probabilities
    prediction_df["prediction"] = final_predictions

    prediction_df.to_csv(
        PREDICTIONS_PATH,
        index=False
    )

    metrics = {
        "model_name": "xgboost_fraud_model",
        "description": "Tuned XGBoost (max_depth=4, reg_alpha=1.0, reg_lambda=3.0, learning_rate=0.03)",
        "features_count": len(features),
        "validation_samples": len(validation_df),
        "validation_fraud_samples": int(y_validation.sum()),
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
        "decision_threshold": float(best_threshold),
        "precision": float(best_precision),
        "recall": float(best_recall),
        "f1": float(best_f1),
        "true_negative": int(matrix[0][0]),
        "false_positive": int(matrix[0][1]),
        "false_negative": int(matrix[1][0]),
        "true_positive": int(matrix[1][1]),
        "risk_policy": {
            "low_threshold_max": 0.35,
            "medium_threshold_max": float(best_threshold),
            "high_threshold_min": float(best_threshold)
        }
    }

    with open(
        THRESHOLD_PATH,
        "w"
    ) as file:
        json.dump(
            metrics,
            file,
            indent=4
        )

    print("MODEL EVALUATION COMPLETE")
    print()

    print("VALIDATION TRANSACTIONS:", len(validation_df))
    print("VALIDATION FRAUD:", y_validation.sum())
    print()

    print("ROC-AUC:", roc_auc)
    print("PR-AUC:", pr_auc)
    print()

    print("BEST THRESHOLD:", best_threshold)
    print("PRECISION:", best_precision)
    print("RECALL:", best_recall)
    print("F1:", best_f1)
    print()

    print("CONFUSION MATRIX:")
    print(matrix)
    print()

    print("THRESHOLD SAVED:", THRESHOLD_PATH)
    print("PREDICTIONS SAVED:", PREDICTIONS_PATH)


if __name__ == "__main__":
    evaluate_model()