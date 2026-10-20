import os
import joblib
import pandas as pd

from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score
)

from src.feature_engineering import (
    add_behavioral_features,
    get_feature_columns
)

from src.ml_pipeline import (
    create_ml_pipeline,
    create_xgboost_pipeline
)


TRAIN_PATH = "data/processed/train.csv"
VALIDATION_PATH = "data/processed/validation.csv"

LOGISTIC_MODEL_PATH = "models/fraud_model.pkl"
XGBOOST_MODEL_PATH = "models/xgboost_fraud_model.pkl"


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


def calculate_metrics(y_true, probabilities, threshold=0.5):

    predictions = (
        probabilities >= threshold
    ).astype(int)

    return {
        "roc_auc": roc_auc_score(
            y_true,
            probabilities
        ),
        "pr_auc": average_precision_score(
            y_true,
            probabilities
        ),
        "precision": precision_score(
            y_true,
            predictions,
            zero_division=0
        ),
        "recall": recall_score(
            y_true,
            predictions,
            zero_division=0
        ),
        "f1": f1_score(
            y_true,
            predictions,
            zero_division=0
        ),
        "threshold": threshold
    }


def compare_models():

    df = load_data()

    df = add_behavioral_features(df)

    features = get_feature_columns()

    train_df = df[
        df["split"] == "train"
    ].copy()

    validation_df = df[
        df["split"] == "validation"
    ].copy()

    X_train = train_df[features]
    y_train = train_df["label"]

    X_validation = validation_df[features]
    y_validation = validation_df["label"]

    fraud_count = y_train.sum()
    legit_count = len(y_train) - fraud_count

    fraud_ratio = (
        legit_count / fraud_count
    )

    print("MODEL COMPARISON")
    print()

    print("FEATURE COUNT:", len(features))
    print("TRAIN TRANSACTIONS:", len(X_train))
    print("VALIDATION TRANSACTIONS:", len(X_validation))
    print("TRAIN FRAUD:", fraud_count)
    print("FRAUD RATIO:", fraud_ratio)
    print()

    logistic_model = joblib.load(
        LOGISTIC_MODEL_PATH
    )

    logistic_probability = (
        logistic_model.predict_proba(
            X_validation
        )[:, 1]
    )

    logistic_metrics = calculate_metrics(
        y_validation,
        logistic_probability
    )

    print("LOGISTIC REGRESSION")
    print(
        "ROC-AUC:",
        logistic_metrics["roc_auc"]
    )
    print(
        "PR-AUC:",
        logistic_metrics["pr_auc"]
    )
    print(
        "PRECISION:",
        logistic_metrics["precision"]
    )
    print(
        "RECALL:",
        logistic_metrics["recall"]
    )
    print(
        "F1:",
        logistic_metrics["f1"]
    )
    print()

    print("TRAINING XGBOOST...")

    xgboost_model = create_xgboost_pipeline(
        features,
        fraud_ratio
    )

    xgboost_model.fit(
        X_train,
        y_train
    )

    xgboost_probability = (
        xgboost_model.predict_proba(
            X_validation
        )[:, 1]
    )

    xgboost_metrics = calculate_metrics(
        y_validation,
        xgboost_probability
    )

    print()
    print("XGBOOST")
    print(
        "ROC-AUC:",
        xgboost_metrics["roc_auc"]
    )
    print(
        "PR-AUC:",
        xgboost_metrics["pr_auc"]
    )
    print(
        "PRECISION:",
        xgboost_metrics["precision"]
    )
    print(
        "RECALL:",
        xgboost_metrics["recall"]
    )
    print(
        "F1:",
        xgboost_metrics["f1"]
    )
    print()

    os.makedirs(
        "models",
        exist_ok=True
    )

    joblib.dump(
        xgboost_model,
        XGBOOST_MODEL_PATH
    )

    print(
        "XGBOOST MODEL SAVED:",
        XGBOOST_MODEL_PATH
    )
    print()

    print("MODEL COMPARISON COMPLETE")


if __name__ == "__main__":
    compare_models()