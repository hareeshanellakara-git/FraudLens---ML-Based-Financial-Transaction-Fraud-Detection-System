import pandas as pd
from pathlib import Path
from typing import Dict


def bootstrap_state(engine) -> None:
    """Bootstrap per‑user StateStore with historical training rows that precede the first test transaction for each user.

    This function:
    1. Reads ``data/raw/test.csv`` to compute the earliest test ``timestamp`` per ``user_id``.
    2. Reads ``data/raw/train.csv`` and, for each row where ``timestamp`` is less than the user's earliest test timestamp, feeds the row to the engine's StateStore via ``generate_features``.
    3. No DB persistence or model inference occurs – the purpose is solely to build the initial behavioral state.
    """
    project_root = Path(__file__).resolve().parents[1]
    test_path = project_root / "data" / "raw" / "test.csv"
    train_path = project_root / "data" / "raw" / "train.csv"

    # Load test timestamps per user
    test_df = pd.read_csv(test_path, usecols=["user_id", "timestamp"])
    earliest_test = test_df.groupby("user_id")['timestamp'].min().to_dict()

    # Process training rows
    # Only keep columns needed for StateStore generation
    train_cols = [
        "user_id",
        "timestamp",
        "amount",
        "merchant_category",
        "country",
        "device_id",
        "channel",
    ]
    for chunk in pd.read_csv(train_path, usecols=train_cols, chunksize=50000):
        # Filter rows that are earlier than the user's earliest test timestamp
        mask = chunk.apply(
            lambda row: row["timestamp"] < earliest_test.get(row["user_id"], float('inf')),
            axis=1,
        )
        early_rows = chunk[mask]
        for _, row in early_rows.iterrows():
            txn = {
                "user_id": int(row["user_id"]),
                "timestamp": int(row["timestamp"]),
                "amount": float(row["amount"]),
                "merchant_category": int(row["merchant_category"]),
                "country": int(row["country"]),
                "device_id": str(row["device_id"]),
                "channel": int(row["channel"]),
            }
            # Directly update the live StateStore (this mutates state as intended for bootstrap)
            engine.store.get_state(txn["user_id"]).generate_features(txn)
