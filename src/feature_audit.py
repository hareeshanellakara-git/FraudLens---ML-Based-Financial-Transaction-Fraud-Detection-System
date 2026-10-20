import joblib
import pandas as pd

from src.feature_engineering import (
    add_behavioral_features,
    get_feature_columns
)


TRAIN_PATH = "data/processed/train.csv"
VALIDATION_PATH = "data/processed/validation.csv"
MODEL_PATH = "models/xgboost_fraud_model.pkl"


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


def audit_features():

    df = load_data()

    df = add_behavioral_features(df)

    features = get_feature_columns()

    validation_df = df[
        df["split"] == "validation"
    ].copy()

    print("FEATURE SIGNAL AUDIT")
    print()

    print("VALIDATION SHAPE:", validation_df.shape)
    print("FEATURE COUNT:", len(features))
    print()

    print("=" * 70)
    print("NUMERIC FEATURE SIGNAL")
    print("=" * 70)

    numeric_features = validation_df[
        features
    ].select_dtypes(
        include=["number"]
    ).columns

    results = []

    for feature in numeric_features:

        legit_mean = validation_df.loc[
            validation_df["label"] == 0,
            feature
        ].mean()

        fraud_mean = validation_df.loc[
            validation_df["label"] == 1,
            feature
        ].mean()

        difference = fraud_mean - legit_mean

        results.append([
            feature,
            legit_mean,
            fraud_mean,
            difference
        ])

    numeric_results = pd.DataFrame(
        results,
        columns=[
            "feature",
            "legit_mean",
            "fraud_mean",
            "difference"
        ]
    )

    numeric_results["abs_difference"] = (
        numeric_results["difference"].abs()
    )

    numeric_results = numeric_results.sort_values(
        "abs_difference",
        ascending=False
    )

    print(
        numeric_results[
            [
                "feature",
                "legit_mean",
                "fraud_mean",
                "difference"
            ]
        ].to_string(index=False)
    )

    print()
    print("=" * 70)
    print("BINARY FEATURE FRAUD RATES")
    print("=" * 70)

    binary_features = []

    for feature in features:

        values = validation_df[
            feature
        ].dropna().unique()

        if set(values).issubset({0, 1}):

            binary_features.append(feature)

    binary_results = []

    for feature in binary_features:

        for value in [0, 1]:

            subset = validation_df[
                validation_df[feature] == value
            ]

            if len(subset) == 0:
                continue

            fraud_rate = subset["label"].mean()

            binary_results.append([
                feature,
                value,
                len(subset),
                fraud_rate
            ])

    binary_results = pd.DataFrame(
        binary_results,
        columns=[
            "feature",
            "value",
            "transactions",
            "fraud_rate"
        ]
    )

    binary_results = binary_results.sort_values(
        "fraud_rate",
        ascending=False
    )

    print(
        binary_results.to_string(index=False)
    )

    print()
    print("=" * 70)
    print("CATEGORICAL FEATURE FRAUD RATES")
    print("=" * 70)

    categorical_features = [
        "merchant_category",
        "country",
        "channel"
    ]

    for feature in categorical_features:

        print()
        print("FEATURE:", feature)

        category_results = (
            validation_df
            .groupby(feature)["label"]
            .agg(
                transactions="count",
                frauds="sum",
                fraud_rate="mean"
            )
            .sort_values(
                "fraud_rate",
                ascending=False
            )
        )

        print(
            category_results.head(15).to_string()
        )

    print()
    print("=" * 70)
    print("XGBOOST FEATURE IMPORTANCE")
    print("=" * 70)

    model = joblib.load(
        MODEL_PATH
    )

    preprocessor = model.named_steps[
        "preprocessor"
    ]

    xgboost_model = model.named_steps[
        "model"
    ]

    transformed_features = (
        preprocessor.get_feature_names_out()
    )

    importance = xgboost_model.feature_importances_

    importance_results = pd.DataFrame({
        "feature": transformed_features,
        "importance": importance
    })

    importance_results = importance_results.sort_values(
        "importance",
        ascending=False
    )

    print(
        importance_results.head(25).to_string(
            index=False
        )
    )

    print()
    print("FEATURE SIGNAL AUDIT COMPLETE")


if __name__ == "__main__":
    audit_features()