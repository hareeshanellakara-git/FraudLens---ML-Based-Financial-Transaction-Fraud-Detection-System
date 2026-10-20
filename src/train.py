import os
import joblib
import pandas as pd

from src.feature_engineering import (
    add_behavioral_features,
    get_feature_columns
)

from src.ml_pipeline import create_ml_pipeline


TRAIN_PATH = "data/processed/train.csv"
VALIDATION_PATH = "data/processed/validation.csv"
MODEL_PATH = "models/fraud_model.pkl"


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


def train_model():

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

    pipeline = create_ml_pipeline(features)

    pipeline.fit(
        X_train,
        y_train
    )

    train_probability = pipeline.predict_proba(
        X_train
    )[:, 1]

    validation_probability = pipeline.predict_proba(
        X_validation
    )[:, 1]

    os.makedirs(
        "models",
        exist_ok=True
    )

    joblib.dump(
        pipeline,
        MODEL_PATH
    )

    print("MODEL TRAINING COMPLETE")
    print()

    print("FEATURE COUNT:", len(features))
    print("FEATURES:")
    print(features)
    print()

    print("TRAIN TRANSACTIONS:", len(X_train))
    print("VALIDATION TRANSACTIONS:", len(X_validation))
    print()

    print("TRAIN FRAUD:", y_train.sum())
    print("VALIDATION FRAUD:", y_validation.sum())
    print()

    print(
        "TRAIN PROBABILITY RANGE:",
        train_probability.min(),
        "->",
        train_probability.max()
    )

    print(
        "VALIDATION PROBABILITY RANGE:",
        validation_probability.min(),
        "->",
        validation_probability.max()
    )

    print()

    print("MODEL SAVED:", MODEL_PATH)


if __name__ == "__main__":
    train_model()