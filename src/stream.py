"""Deterministic unseen-test replay for Stage 5C.

Replay order is:

    timestamp ASC, original CSV row index ASC (tie-breaker)

``stream_state.row_index`` is the 0-based position of the NEXT row in this
sorted sequence, not the physical file order. ``source_txn_id`` is always the
original ``transaction_id``. Labels are never used.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_TEST_CSV = _PROJECT_ROOT / "data" / "raw" / "test.csv"

_RAW_FEATURE_COLS = (
    "transaction_id",
    "user_id",
    "timestamp",
    "amount",
    "merchant_category",
    "country",
    "device_id",
    "channel",
)

_replay_rows: Optional[List[Dict[str, Any]]] = None


def _load_replay_rows() -> List[Dict[str, Any]]:
    """Load test.csv, stamp original row index, then sort deterministically."""
    df = pd.read_csv(_TEST_CSV)
    if "label" in df.columns:
        df = df.drop(columns=["label"])
    missing = [c for c in _RAW_FEATURE_COLS if c not in df.columns]
    if missing:
        raise RuntimeError(f"test.csv missing required columns: {missing}")

    df = df.reset_index(drop=True)
    df["_orig_csv_row_index"] = df.index.astype(int)
    df = df.sort_values(
        ["timestamp", "_orig_csv_row_index"],
        ascending=True,
        kind="mergesort",
    ).reset_index(drop=True)

    rows: List[Dict[str, Any]] = []
    for pos, rec in enumerate(df.to_dict(orient="records")):
        rows.append(
            {
                "replay_index": pos,
                "orig_csv_row_index": int(rec["_orig_csv_row_index"]),
                "source_txn_id": int(rec["transaction_id"]),
                "user_id": int(rec["user_id"]),
                "timestamp": int(rec["timestamp"]),
                "amount": float(rec["amount"]),
                "merchant_category": int(rec["merchant_category"]),
                "country": int(rec["country"]),
                "device_id": str(rec["device_id"]),
                "channel": int(rec["channel"]),
            }
        )
    return rows


def get_replay_rows() -> List[Dict[str, Any]]:
    """Return the cached deterministic replay sequence (identical after restart)."""
    global _replay_rows
    if _replay_rows is None:
        _replay_rows = _load_replay_rows()
    return _replay_rows


def replay_length() -> int:
    return len(get_replay_rows())


def get_replay_row(row_index: int) -> Optional[Dict[str, Any]]:
    """Return the scoring payload for the given sorted-stream position, or None."""
    rows = get_replay_rows()
    if row_index < 0 or row_index >= len(rows):
        return None
    src = rows[row_index]
    return {
        "source_txn_id": src["source_txn_id"],
        "user_id": src["user_id"],
        "timestamp": src["timestamp"],
        "amount": src["amount"],
        "merchant_category": src["merchant_category"],
        "country": src["country"],
        "device_id": src["device_id"],
        "channel": src["channel"],
    }
