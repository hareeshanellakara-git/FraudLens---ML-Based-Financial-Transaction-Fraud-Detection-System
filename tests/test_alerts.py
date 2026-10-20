import os, tempfile, json
import sqlite3

# Import the modules we need
from src import persistence, scoring

def test_high_risk_alert_creation():
    # Create a temporary directory and DB file
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'fraudlens_test.db')
        # Monkey‑patch the DB_PATH used by persistence
        persistence.DB_PATH = os.path.abspath(db_path)
        # Initialise the database schema
        persistence.init_db()

        # Prepare a synthetic high‑risk transaction payload
        txn = {
            "user_id": 1,
            "timestamp": 1700000000,
            "amount": 10000.0,
            "merchant_category": 99,
            "country": 1,
            "device_id": "device123",
            "channel": 1,
        }
        # Compute dummy features (the real engine would be needed for real values,
        # but for this test we only need to store something that can be JSON‑serialised).
        dummy_features = {f"f{i}": i for i in range(27)}

        # Directly insert the transaction with HIGH risk metadata
        with persistence.TransactionContext() as conn:
            # Allocate a processing_seq manually
            processing_seq = persistence.get_next_processing_seq(conn)
            txn_id = persistence.insert_transaction(
                conn,
                source_txn_id=None,
                user_id=txn["user_id"],
                timestamp=txn["timestamp"],
                amount=txn["amount"],
                merchant_category=txn["merchant_category"],
                country=txn["country"],
                device_id=txn["device_id"],
                channel=txn["channel"],
                risk_score=0.95,
                decision="fraud",
                risk_level="HIGH",
                processing_seq=processing_seq,
                features=dummy_features,
            )
            # Insert the corresponding alert
            persistence.insert_alert(
                conn,
                transaction_id=txn_id,
                user_id=txn["user_id"],
                timestamp=txn["timestamp"],
                risk_score=0.95,
                risk_level="HIGH",
            )

        # Verify that the alert was persisted
        conn = sqlite3.connect(persistence.DB_PATH)
        cur = conn.execute("SELECT COUNT(*) FROM alerts WHERE risk_level='HIGH'")
        count = cur.fetchone()[0]
        conn.close()
        assert count == 1

        # Verify that the features column contains the JSON we supplied
        conn = sqlite3.connect(persistence.DB_PATH)
        cur = conn.execute("SELECT features FROM transactions WHERE id=?", (txn_id,))
        stored = cur.fetchone()[0]
        conn.close()
        assert json.loads(stored) == dummy_features
