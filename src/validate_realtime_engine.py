import pandas as pd
import numpy as np
from src.feature_engineering import add_behavioral_features, get_feature_columns
from src.realtime_feature_engine import RealTimeFeatureEngine


def compare_features(batch_df: pd.DataFrame, real_df: pd.DataFrame) -> None:
    """Compare batch vs real‑time features with numeric tolerance.

    Prints a concise report of mismatches. Uses ``np.isclose`` for floating‑point
    columns to avoid differences due to rounding errors.
    """
    cols = get_feature_columns()
    mismatches = []
    for idx, (b_row, r_row) in enumerate(
        zip(batch_df[cols].itertuples(index=False), real_df[cols].itertuples(index=False))
    ):
        for col, b_val, r_val in zip(cols, b_row, r_row):
            # Treat NaN as equal
            if pd.isna(b_val) and pd.isna(r_val):
                continue
            # Numeric tolerance
            if isinstance(b_val, (int, float, np.number)) and isinstance(r_val, (int, float, np.number)):
                if not np.isclose(b_val, r_val, rtol=1e-12, atol=1e-12, equal_nan=True):
                    mismatches.append((idx, col, b_val, r_val))
                    break
            else:
                if b_val != r_val:
                    mismatches.append((idx, col, b_val, r_val))
                    break
    total = len(batch_df)
    if not mismatches:
        print(f"All {total} transactions matched on all 27 features.")
    else:
        print(f"Found {len(mismatches)} mismatched transactions out of {total}.")
        for idx, col, b, r in mismatches[:10]:
            print(f"Row {idx}, column {col}: batch={b}, realtime={r}")


def edge_case_tests():
    engine = RealTimeFeatureEngine()
    # 1. First transaction
    txn1 = {
        "user_id": 1,
        "timestamp": 1000,
        "amount": 10.0,
        "device_id": "devA",
        "country": "US",
        "merchant_category": 5,
        "channel": 0,
    }
    f1 = engine.process_transaction(txn1)
    # 2. Second transaction same user
    txn2 = {
        "user_id": 1,
        "timestamp": 1500,
        "amount": 20.0,
        "device_id": "devA",
        "country": "US",
        "merchant_category": 5,
        "channel": 0,
    }
    f2 = engine.process_transaction(txn2)
    # 3. New device for same user
    txn3 = {
        "user_id": 1,
        "timestamp": 2000,
        "amount": 30.0,
        "device_id": "devB",
        "country": "US",
        "merchant_category": 5,
        "channel": 0,
    }
    f3 = engine.process_transaction(txn3)
    # 4. Out-of-order timestamp (processed as‑is; we note behavior)
    txn4 = {
        "user_id": 1,
        "timestamp": 1200,
        "amount": 40.0,
        "device_id": "devC",
        "country": "CA",
        "merchant_category": 6,
        "channel": 1,
    }
    f4 = engine.process_transaction(txn4)
    print("Edge-case feature snapshots (first 4 txns):")
    for i, f in enumerate([f1, f2, f3, f4], 1):
        print(f"Txn {i}: {f}")


if __name__ == "__main__":
    # Load a small slice of the training data for batch vs realtime comparison
    df = pd.read_csv("C:/FraudLens/data/processed/train.csv", nrows=500)
    batch_features = add_behavioral_features(df.copy())
    engine = RealTimeFeatureEngine()
    realtime_features = engine.process_dataframe(df.copy())
    compare_features(batch_features, realtime_features)
    edge_case_tests()
