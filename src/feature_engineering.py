import pandas as pd
import numpy as np


SHORT_WINDOW = 10000
MEDIUM_WINDOW = 50000
LONG_WINDOW = 175000


def add_behavioral_features(df):
    df = df.copy()

    df = df.sort_values(
        ["user_id", "timestamp"]
    ).reset_index(drop=True)

    g = df.groupby("user_id")

    df["prev_amount"] = g["amount"].shift(1)

    df["user_avg_amount"] = (
        g["amount"]
        .transform(lambda x: x.shift(1).expanding().mean())
    )

    df["user_median_amount"] = (
        g["amount"]
        .transform(lambda x: x.shift(1).expanding().median())
    )

    df["user_std_amount"] = (
        g["amount"]
        .transform(lambda x: x.shift(1).expanding().std())
    )

    df["user_transaction_count"] = g.cumcount()

    df["amount_diff"] = (
        df["amount"] - df["prev_amount"]
    )

    df["amount_ratio"] = (
        df["amount"] /
        df["prev_amount"].replace(0, np.nan)
    )

    df["amount_vs_avg"] = (
        df["amount"] /
        df["user_avg_amount"].replace(0, np.nan)
    )

    df["amount_zscore"] = (
        (df["amount"] - df["user_avg_amount"]) /
        df["user_std_amount"].replace(0, np.nan)
    )

    df["prev_device"] = g["device_id"].shift(1)
    df["prev_country"] = g["country"].shift(1)
    df["prev_merchant_category"] = (
        g["merchant_category"].shift(1)
    )

    df["device_changed"] = (
        (df["device_id"] != df["prev_device"]) &
        df["prev_device"].notna()
    ).astype(int)

    df["country_changed"] = (
        (df["country"] != df["prev_country"]) &
        df["prev_country"].notna()
    ).astype(int)

    df["merchant_changed"] = (
        (
            df["merchant_category"] !=
            df["prev_merchant_category"]
        ) &
        df["prev_merchant_category"].notna()
    ).astype(int)

    df["new_device"] = (
        ~df.groupby("user_id")["device_id"]
        .transform(lambda x: x.duplicated())
    ).astype(int)

    df["new_country"] = (
        ~df.groupby("user_id")["country"]
        .transform(lambda x: x.duplicated())
    ).astype(int)

    df["new_merchant_category"] = (
        ~df.groupby("user_id")["merchant_category"]
        .transform(lambda x: x.duplicated())
    ).astype(int)

    df["timestamp_gap"] = (
        g["timestamp"].diff()
    )

    df["transactions_last_short_window"] = 0
    df["transactions_last_medium_window"] = 0
    df["transactions_last_long_window"] = 0

    for user_id, group in df.groupby("user_id", sort=False):

        positions = group.index
        times = group["timestamp"].values

        short_left = 0
        medium_left = 0
        long_left = 0

        for i in range(len(group)):

            current_time = times[i]

            while (
                short_left < i and
                times[short_left] < current_time - SHORT_WINDOW
            ):
                short_left += 1

            while (
                medium_left < i and
                times[medium_left] < current_time - MEDIUM_WINDOW
            ):
                medium_left += 1

            while (
                long_left < i and
                times[long_left] < current_time - LONG_WINDOW
            ):
                long_left += 1

            df.loc[
                positions[i],
                "transactions_last_short_window"
            ] = i - short_left

            df.loc[
                positions[i],
                "transactions_last_medium_window"
            ] = i - medium_left

            df.loc[
                positions[i],
                "transactions_last_long_window"
            ] = i - long_left

    df["rapid_transaction"] = (
        (df["timestamp_gap"] <= SHORT_WINDOW) &
        (df["user_transaction_count"] > 0)
    ).astype(int)

    df["high_velocity_short"] = (
        df["transactions_last_short_window"] >= 2
    ).astype(int)

    df["high_velocity_medium"] = (
        df["transactions_last_medium_window"] >= 4
    ).astype(int)

    df["high_velocity_long"] = (
        df["transactions_last_long_window"] >= 8
    ).astype(int)

    df = df.replace(
        [np.inf, -np.inf],
        np.nan
    )

    return df


def get_feature_columns():
    return [
        "amount",
        "merchant_category",
        "country",
        "channel",

        "timestamp_gap",

        "prev_amount",
        "user_avg_amount",
        "user_median_amount",
        "user_std_amount",
        "user_transaction_count",

        "amount_diff",
        "amount_ratio",
        "amount_vs_avg",
        "amount_zscore",

        "device_changed",
        "country_changed",
        "merchant_changed",

        "new_device",
        "new_country",
        "new_merchant_category",

        "transactions_last_short_window",
        "transactions_last_medium_window",
        "transactions_last_long_window",

        "rapid_transaction",

        "high_velocity_short",
        "high_velocity_medium",
        "high_velocity_long"
    ]