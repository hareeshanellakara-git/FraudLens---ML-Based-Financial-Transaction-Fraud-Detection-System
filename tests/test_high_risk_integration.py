import os, tempfile, json
import pytest
from src import persistence, scoring
from src.realtime_feature_engine import RealTimeFeatureEngine

@pytest.fixture(scope="function")
def temp_db():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "fraudlens_test.db")
        persistence.DB_PATH = os.path.abspath(db_path)
        persistence.init_db()
        yield db_path

def test_high_risk_prediction_flow(temp_db):
    # Initialise engine and inject into scoring module
    engine = RealTimeFeatureEngine()
    scoring._engine = engine

    # Prepare a payload that is likely to trigger HIGH risk (very large amount)
    payload = {
        "user_id": 1,
        "timestamp": 1700000000,
        "amount": 10_000_000.0,  # extremely large amount
        "merchant_category": 99,
        "country": 1,
        "device_id": "deviceX",
        "channel": 1,
    }

    # Run scoring until we get a HIGH risk (max 20 attempts)
    response = None
    for _ in range(20):
        response = scoring.score_transaction(txn=payload, is_stream=False)
        if response["risk_level"] == "HIGH":
            break
    assert response is not None, "Scoring did not return a response"
    assert response["risk_level"] == "HIGH", "Expected a HIGH risk prediction"

    # Verify that the transaction was persisted
    txn_id = response["transaction_id"]
    conn = sqlite3.connect(persistence.DB_PATH)
    cur = conn.execute("SELECT risk_level FROM transactions WHERE id = ?", (txn_id,))
    row = cur.fetchone()
    assert row is not None and row[0] == "HIGH"

    # Verify that an alert was automatically created
    cur = conn.execute("SELECT COUNT(*) FROM alerts WHERE transaction_id = ?", (txn_id,))
    alert_count = cur.fetchone()[0]
    assert alert_count == 1
    conn.close()
