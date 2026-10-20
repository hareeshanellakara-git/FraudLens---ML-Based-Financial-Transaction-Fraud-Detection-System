import json
import pickle
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, validator

from src.realtime_feature_engine import RealTimeFeatureEngine
from src.feature_engineering import get_feature_columns

# Load model and threshold once at startup
MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "xgboost_fraud_model.pkl"
THRESHOLD_PATH = Path(__file__).resolve().parents[1] / "models" / "threshold.json"

try:
    import joblib
    _model = joblib.load(MODEL_PATH)
except Exception as e_joblib:
    try:
        with open(MODEL_PATH, "rb") as f:
            _model = pickle.load(f)
    except Exception as e_pickle:
        raise RuntimeError(
            f"Failed to load model from {MODEL_PATH}: joblib error {e_joblib}; "
            f"pickle error {e_pickle}"
        )

try:
    with open(THRESHOLD_PATH, "r", encoding="utf-8") as f:
        _threshold_cfg = json.load(f)
except Exception as e:
    raise RuntimeError(f"Failed to load threshold config from {THRESHOLD_PATH}: {e}")

# Extract decision threshold and risk policy
DECISION_THRESHOLD: float = _threshold_cfg.get("decision_threshold", 0.5)
RISK_POLICY: Dict[str, float] = _threshold_cfg.get("risk_policy", {})
LOW_MAX = RISK_POLICY.get("low_threshold_max", 0.35)
MEDIUM_MAX = RISK_POLICY.get("medium_threshold_max", 0.55)
HIGH_MIN = RISK_POLICY.get("high_threshold_min", 0.55)

app = FastAPI(title="FraudLens Real‑Time Scoring API")

engine = RealTimeFeatureEngine()

# Initialize FastAPI startup event for DB and engine setup
@app.on_event("startup")
def startup_event() -> None:
    """Initialize DB, inject engine, bootstrap train history, then rebuild live StateStore.

    Order is required:

        init_db → set_engine → per-user train bootstrap
        → replay persisted live transactions (processing_seq ASC)
        → stream_state remains the SQLite singleton (not rewritten)

    Replay mutates StateStore only. It does not score, write SQLite, create
    alerts, or advance the stream cursor. test.csv is not scored at startup.
    """
    from src.persistence import init_db, reconstruct_state_store
    init_db()
    from src.scoring import set_engine
    set_engine(engine)
    from src.bootstrap import bootstrap_state
    bootstrap_state(engine)
    reconstruct_state_store(engine)

# System status endpoint providing model info and DB health
@app.get("/system/status")
def system_status() -> Dict[str, Any]:
    """Return diagnostics about the model, thresholds, DB health, and latest processing_seq."""
    from src.persistence import get_latest_processing_seq, get_stream_state
    model_info = {
        "model_path": str(MODEL_PATH),
        "feature_count": len(get_feature_columns()),
        "decision_threshold": DECISION_THRESHOLD,
        "risk_policy": {
            "low_max": LOW_MAX,
            "medium_max": MEDIUM_MAX,
            "high_min": HIGH_MIN,
        },
    }
    try:
        latest_seq = get_latest_processing_seq()
        db_ok = True
    except Exception:
        latest_seq = -1
        db_ok = False
    stream_state = get_stream_state()
    return {
        "model": model_info,
        "db_ok": db_ok,
        "latest_processing_seq": latest_seq,
        "stream_state": stream_state,
    }

class TransactionRequest(BaseModel):
    user_id: int = Field(..., description="Unique identifier of the user/customer")
    timestamp: int = Field(..., description="Unix epoch time of the transaction (seconds)")
    amount: float = Field(..., gt=0, description="Transaction amount in USD")
    device_id: str = Field(..., min_length=1, description="Device identifier string")
    country: str = Field(..., min_length=2, max_length=2, description="ISO‑2 country code")
    merchant_category: int = Field(..., description="Merchant category code (integer)")
    channel: int = Field(..., description="Transaction channel identifier")

    @validator("timestamp")
    def non_negative_ts(cls, v):
        if v < 0:
            raise ValueError("timestamp must be non‑negative")
        return v

@app.get("/health")
def health_check() -> Dict[str, str]:
    """Simple health endpoint used by monitoring systems."""
    return {"status": "ok"}

@app.post("/score")
def score_transaction(request: TransactionRequest) -> Dict[str, Any]:
    """Score a manual transaction using the shared scoring service.

    The request body is validated by Pydantic. Scoring logic lives in
    ``src.scoring`` and guarantees that StateStore mutation occurs **only** after
    the SQLite transaction has successfully committed.
    """
    from src.scoring import score_transaction as shared_score, DuplicateTransactionError
    txn_dict: Dict[str, Any] = request.dict()
    try:
        result = shared_score(txn_dict, is_stream=False)
    except DuplicateTransactionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Scoring failed")
    return result


@app.post("/stream/next")
def stream_next() -> Dict[str, Any]:
    """Score one unseen row, or return ``{"status": "exhausted"}`` at EOF."""
    from src.scoring import score_transaction as shared_score, DuplicateTransactionError, StreamExhaustedError
    try:
        result = shared_score(is_stream=True)
    except StreamExhaustedError:
        return {"status": "exhausted", "message": "No more unseen test transactions"}
    except DuplicateTransactionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Scoring failed")
    result["status"] = "scored"
    return result


@app.get("/stream/status")
def stream_status() -> Dict[str, Any]:
    from src.persistence import get_stream_state
    from src.stream import replay_length

    state = get_stream_state()
    total = replay_length()
    remaining = max(total - int(state["row_index"]), 0)
    return {
        "row_index": int(state["row_index"]),
        "cursor": int(state["cursor"]),
        "total": total,
        "processed": int(state["row_index"]),
        "remaining": remaining,
        "exhausted": int(state["row_index"]) >= total,
    }


@app.get("/dashboard/overview")
def dashboard_overview() -> Dict[str, Any]:
    from src.persistence import dashboard_overview as _overview
    return _overview()


@app.get("/transactions")
def list_transactions(
    q: Optional[str] = Query(None),
    risk_level: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = Query(None),
    user_id: Optional[int] = Query(None),
    decision: Optional[Literal["fraud", "legitimate"]] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    from src.persistence import query_transactions
    return query_transactions(
        q=q,
        risk_level=risk_level,
        user_id=user_id,
        decision=decision,
        page=page,
        limit=limit,
    )


@app.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: int) -> Dict[str, Any]:
    from src.persistence import get_transaction_by_id
    row = get_transaction_by_id(transaction_id)
    if row is None:
        raise HTTPException(status_code=404, detail="transaction not found")
    return row


@app.get("/users")
def list_users(
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    from src.persistence import query_users
    return query_users(q=q, page=page, limit=limit)


@app.get("/users/{user_id}")
def get_user(user_id: int) -> Dict[str, Any]:
    from src.persistence import get_user_detail
    row = get_user_detail(user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return row


@app.get("/alerts")
def list_alerts(
    q: Optional[str] = Query(None),
    risk_level: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = Query(None),
    user_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    from src.persistence import query_alerts
    return query_alerts(
        risk_level=risk_level,
        q=q,
        user_id=user_id,
        page=page,
        limit=limit,
    )


@app.get("/alerts/{alert_id}")
def get_alert(alert_id: int) -> Dict[str, Any]:
    from src.persistence import get_alert_by_id
    row = get_alert_by_id(alert_id)
    if row is None:
        raise HTTPException(status_code=404, detail="alert not found")
    return row
