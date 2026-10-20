import threading
import copy
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import sqlite3

from src.realtime_feature_engine import RealTimeFeatureEngine
from src.feature_engineering import get_feature_columns
from src.persistence import (
    get_connection,
    transaction_exists,
    get_next_processing_seq,
    insert_transaction,
    insert_alert,
    update_stream_state,
    get_latest_processing_seq,
    TransactionContext,
)

# Global lock that serialises the *entire* scoring lifecycle
_GLOBAL_SCORE_LOCK = threading.Lock()

# Engine placeholder – will be set by the API at startup
_engine: RealTimeFeatureEngine = None

def set_engine(engine: RealTimeFeatureEngine) -> None:
    """Inject the shared RealTimeFeatureEngine instance (created in api).
    This ensures all requests share a single StateStore.
    """
    global _engine
    _engine = engine

class DuplicateTransactionError(Exception):
    """Raised when a streamed transaction with the same source_txn_id is seen twice."""
    pass

def _calc_features_without_mutation(txn: Dict[str, Any]) -> Dict[str, Any]:
    """Return the 27 feature values without mutating the live StateStore.
    The function deep‑copies the per‑user UserState, runs generate_features on the copy,
    and discards the copy. The original state remains untouched.
    """
    if _engine is None:
        raise RuntimeError("RealTimeFeatureEngine not initialised in scoring module")
    # Obtain the real user state and deep‑copy it
    real_state = _engine.store.get_state(txn["user_id"])  # type: ignore[index]
    state_copy = copy.deepcopy(real_state)
    # Create a temporary engine that uses the copied state – we can reuse the same
    # RealTimeFeatureEngine class but replace its store with a single‑user copy.
    temp_engine = RealTimeFeatureEngine()
    temp_engine.store._states = {txn["user_id"]: state_copy}  # type: ignore[attr-defined]
    # Generate features on the copy – this mutates only the copy
    features = temp_engine.process_transaction(txn)
    return features

class StreamExhaustedError(Exception):
    """Raised when no unseen test transaction remains."""


def score_transaction(txn: Optional[Dict[str, Any]] = None, *, is_stream: bool) -> Dict[str, Any]:
    """Core scoring routine used by manual scoring and deterministic replay.

    For stream calls, select the next row only after acquiring the lifecycle lock.

    The function follows the *exact* ordering required by the specification:
    duplicate check → non‑mutating feature calc → model inference → processing_seq
    allocation → atomic SQLite transaction (transaction, optional alert, optional
    stream cursor update) → commit → StateStore mutation → response generation.
    """
    with _GLOBAL_SCORE_LOCK:
        if is_stream and txn is None:
            # Select the stream row under the same lock as duplicate checking,
            # inference, commit, and in-memory state mutation.
            from src.persistence import get_stream_state
            from src.stream import get_replay_row, replay_length
            stream_state = get_stream_state()
            if int(stream_state["row_index"]) >= replay_length():
                raise StreamExhaustedError()
            txn = get_replay_row(int(stream_state["row_index"]))
            if txn is None:
                raise StreamExhaustedError()
        if txn is None:
            raise ValueError("Transaction is required for manual scoring")
        # ------------------------------------------------------------------
        # 1️⃣ Duplicate check (only for streamed rows that have a source_txn_id)
        source_txn_id = txn.get("source_txn_id")
        if is_stream:
            if source_txn_id is None:
                raise ValueError("Streamed transaction must contain source_txn_id")
            if transaction_exists(source_txn_id):
                raise DuplicateTransactionError(f"Transaction {source_txn_id} already processed")
        # ------------------------------------------------------------------
        # 2️⃣ Feature calculation without mutating live state
        features = _calc_features_without_mutation(txn)
        # ------------------------------------------------------------------
        # 3️⃣ Model inference – reuse the same model loaded in ``src.api``
        # Import lazily to avoid circular import with api where the model lives.
        from src.api import _model, DECISION_THRESHOLD, LOW_MAX, MEDIUM_MAX, HIGH_MIN
        expected_cols = get_feature_columns()
        # Ensure columns match (defensive – should always be true)
        if set(features.keys()) != set(expected_cols):
            raise RuntimeError("Feature set mismatch during scoring")
        ordered = [features[col] for col in expected_cols]
        ordered = [np.nan if v is None else v for v in ordered]
        df = pd.DataFrame([ordered], columns=expected_cols)
        prob = float(_model.predict_proba(df)[0][1])
        decision = "fraud" if prob >= DECISION_THRESHOLD else "legitimate"
        if prob <= LOW_MAX:
            risk_level = "LOW"
        elif prob <= MEDIUM_MAX:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"
        # ------------------------------------------------------------------
        # 4️⃣ Allocate processing_seq – must happen while the lock is held
        with TransactionContext() as conn:
            processing_seq = get_next_processing_seq(conn)
            # 5️⃣ Insert the transaction row
            txn_id = insert_transaction(
                conn,
                source_txn_id=source_txn_id,
                user_id=txn["user_id"],
                timestamp=txn["timestamp"],
                amount=txn["amount"],
                merchant_category=txn["merchant_category"],
                country=txn["country"],
                device_id=txn["device_id"],
                channel=txn["channel"],
                risk_score=prob,
                decision=decision,
                risk_level=risk_level,
                processing_seq=processing_seq,
                features=features,
            )
            # 6️⃣ Optional alert for HIGH risk
            if risk_level == "HIGH":
                insert_alert(
                    conn,
                    transaction_id=txn_id,
                    user_id=txn["user_id"],
                    timestamp=txn["timestamp"],
                    risk_score=prob,
                    risk_level=risk_level,
                )
            # 7️⃣ Stream cursor update (only for streamed transactions)
            if is_stream:
                # row_index is advanced by 1 – the caller will have already read the
                # current row, so we simply increment.
                from src.persistence import get_stream_state
                state = get_stream_state()
                new_row_index = state["row_index"] + 1
                update_stream_state(conn, new_row_index, processing_seq)
        # ------------------------------------------------------------------
        # 8️⃣ AFTER COMMIT – mutate the *live* StateStore
        # We reuse the real engine instance that was injected via set_engine()
        real_state = _engine.store.get_state(txn["user_id"])  # type: ignore[index]
        # The generate_features call returns a dict we do not need – state is updated.
        real_state.generate_features(txn)
        # ------------------------------------------------------------------
        # 9️⃣ Build response payload (identical to previous API format)
        response = {
            "risk_score": prob,
            "decision": decision,
            "risk_level": risk_level,
            "features": {col: features[col] for col in expected_cols},
        }
        if is_stream:
            response.pop("features", None)
            response.update({
                "transaction_id": txn_id,
                "source_txn_id": source_txn_id,
                "user_id": txn["user_id"],
                "timestamp": txn["timestamp"],
                "amount": txn["amount"],
                "merchant_category": txn["merchant_category"],
                "country": txn["country"],
                "channel": txn["channel"],
                "processing_seq": processing_seq,
            })
        return response
