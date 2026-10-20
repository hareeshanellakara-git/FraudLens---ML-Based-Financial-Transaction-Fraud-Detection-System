import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Path to the SQLite DB file (stored in the project root for simplicity)
DB_PATH = Path(__file__).resolve().parents[1] / "fraudlens.db"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with foreign keys enabled.
    The connection uses ``detect_types=sqlite3.PARSE_DECLTYPES`` so that
    Python ``datetime`` objects would be handled correctly if ever needed.
    """
    conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all required tables if they do not exist and ensure the
    ``stream_state`` singleton row is present.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        # 1) transactions table
        # Create transactions table with features column
        cur.execute("""
          CREATE TABLE IF NOT EXISTS transactions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                source_txn_id    INTEGER UNIQUE,
                user_id          INTEGER NOT NULL,
                timestamp        INTEGER NOT NULL,
                amount           REAL NOT NULL,
                merchant_category INTEGER NOT NULL,
                country          INTEGER NOT NULL,
                device_id        TEXT NOT NULL,
                channel          INTEGER NOT NULL,
                risk_score       REAL NOT NULL,
                decision         TEXT NOT NULL,
                risk_level       TEXT NOT NULL,
                processing_seq   INTEGER NOT NULL UNIQUE,
                features         TEXT
            );
        """)
        # Ensure features column exists (no-op if already present)
        try:
            cur.execute("ALTER TABLE transactions ADD COLUMN features TEXT;")
        except Exception:
            pass
        # 2) alerts table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id  INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                user_id         INTEGER NOT NULL,
                timestamp       INTEGER NOT NULL,
                risk_score      REAL NOT NULL,
                risk_level      TEXT NOT NULL,
                UNIQUE(transaction_id)
            );
            """
        )
        # 3) stream_state singleton
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stream_state (
                id              INTEGER PRIMARY KEY CHECK (id = 1),
                row_index       INTEGER NOT NULL,
                cursor          INTEGER NOT NULL
            );
            """
        )
        # Ensure the single row exists (id = 1)
        cur.execute("INSERT OR IGNORE INTO stream_state (id, row_index, cursor) VALUES (1, 0, 0)")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_txn_processing_seq ON transactions(processing_seq)"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txn_user_id ON transactions(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_txn_risk_level ON transactions(risk_level)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts(user_id)")
        conn.commit()
    finally:
        conn.close()


def transaction_exists(source_txn_id: int) -> bool:
    """Return ``True`` if a streamed transaction with the given ``source_txn_id``
    already exists in the ``transactions`` table.
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT 1 FROM transactions WHERE source_txn_id = ?",
            (source_txn_id,)
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def get_next_processing_seq(conn: sqlite3.Connection) -> int:
    """Allocate the next ``processing_seq`` value. Caller must hold the global
    scoring lock before calling this function.
    """
    cur = conn.execute("SELECT IFNULL(MAX(processing_seq), 0) FROM transactions")
    max_seq = cur.fetchone()[0]
    return int(max_seq) + 1


def insert_transaction(
    conn: sqlite3.Connection,
    *,
    source_txn_id: Optional[int],
    user_id: int,
    timestamp: int,
    amount: float,
    merchant_category: int,
    country: int,
    device_id: str,
    channel: int,
    risk_score: float,
    decision: str,
    risk_level: str,
    processing_seq: int,
    features: Optional[dict] = None,
) -> int:
    """Insert a transaction row and return the internal ``id`` (SQLite rowid).
    ``source_txn_id`` may be ``None`` for manual transactions.
    ``features`` is an optional dict of engineered features, which will be
    JSON‑serialized into the ``features`` TEXT column.
    """
    # Serialize features dict to JSON string if provided
    features_json = json.dumps(features) if features is not None else None
    cur = conn.execute(
        """
        INSERT INTO transactions (
            source_txn_id, user_id, timestamp, amount,
            merchant_category, country, device_id, channel,
            risk_score, decision, risk_level, processing_seq, features
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            source_txn_id,
            user_id,
            timestamp,
            amount,
            merchant_category,
            country,
            device_id,
            channel,
            risk_score,
            decision,
            risk_level,
            processing_seq,
            features_json,
        ),
    )
    return cur.lastrowid



def insert_alert(
    conn: sqlite3.Connection,
    *,
    transaction_id: int,
    user_id: int,
    timestamp: int,
    risk_score: float,
    risk_level: str,
) -> None:
    conn.execute(
        """
        INSERT INTO alerts (
            transaction_id, user_id, timestamp, risk_score, risk_level
        ) VALUES (?,?,?,?,?)
        """,
        (transaction_id, user_id, timestamp, risk_score, risk_level),
    )


def update_stream_state(conn: sqlite3.Connection, new_row_index: int, new_cursor: int) -> None:
    """Atomically update the stream cursor and row index.

    ``new_row_index`` is the 0-based position of the NEXT row in the
    deterministic sorted replay sequence. ``new_cursor`` is the
    ``processing_seq`` of the last successfully streamed transaction.
    """
    conn.execute(
        """
        UPDATE stream_state
        SET row_index = ?, cursor = ?
        WHERE id = 1
        """,
        (new_row_index, new_cursor),
    )


def get_stream_state() -> Dict[str, int]:
    conn = get_connection()
    try:
        cur = conn.execute("SELECT row_index, cursor FROM stream_state WHERE id = 1")
        row = cur.fetchone()
        return {"row_index": row[0], "cursor": row[1]}
    finally:
        conn.close()


def get_latest_processing_seq() -> int:
    conn = get_connection()
    try:
        cur = conn.execute("SELECT IFNULL(MAX(processing_seq), 0) FROM transactions")
        return int(cur.fetchone()[0])
    finally:
        conn.close()


def fetch_transactions_for_replay() -> List[Dict[str, Any]]:
    """Return persisted live transactions in processing_seq order for StateStore rebuild."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            SELECT user_id, timestamp, amount, merchant_category, country, device_id, channel
            FROM transactions
            ORDER BY processing_seq ASC
            """
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def reconstruct_state_store(engine) -> None:
    """Replay persisted live transactions into StateStore only.

    Does not invoke the model, scoring service, alerts, or SQLite writes.
    Does not advance stream_state or processing_seq.
    """
    for txn in fetch_transactions_for_replay():
        payload = {
            "user_id": int(txn["user_id"]),
            "timestamp": int(txn["timestamp"]),
            "amount": float(txn["amount"]),
            "merchant_category": int(txn["merchant_category"]),
            "country": txn["country"],
            "device_id": str(txn["device_id"]),
            "channel": int(txn["channel"]),
        }
        engine.process_transaction(payload)


def _page_window(page: int, limit: int) -> Tuple[int, int]:
    return limit, (page - 1) * limit


def _txn_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "transaction_id": row["id"],
        "source_txn_id": row["source_txn_id"],
        "user_id": row["user_id"],
        "timestamp": row["timestamp"],
        "amount": row["amount"],
        "merchant_category": row["merchant_category"],
        "country": row["country"],
        "device_id": row["device_id"],
        "channel": row["channel"],
        "risk_score": row["risk_score"],
        "decision": row["decision"],
        "risk_level": row["risk_level"],
        "processing_seq": row["processing_seq"],
    }


def query_transactions(
    *,
    q: Optional[str] = None,
    risk_level: Optional[str] = None,
    user_id: Optional[int] = None,
    decision: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
) -> Dict[str, Any]:
    lim, off = _page_window(page, limit)
    clauses: List[str] = []
    params: List[Any] = []
    if q:
        like = f"%{q}%"
        clauses.append(
            "(CAST(id AS TEXT) LIKE ? OR CAST(source_txn_id AS TEXT) LIKE ? "
            "OR CAST(user_id AS TEXT) LIKE ? OR device_id LIKE ?)"
        )
        params.extend([like, like, like, like])
    if risk_level:
        clauses.append("risk_level = ?")
        params.append(risk_level)
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(int(user_id))
    if decision:
        clauses.append("decision = ?")
        params.append(decision)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM transactions {where}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT id, source_txn_id, user_id, timestamp, amount, merchant_category,
                   country, device_id, channel, risk_score, decision, risk_level, processing_seq
            FROM transactions
            {where}
            ORDER BY processing_seq DESC
            LIMIT ? OFFSET ?
            """,
            params + [lim, off],
        ).fetchall()
        return {
            "items": [_txn_dict(r) for r in rows],
            "total": int(total),
            "page": page,
            "limit": lim,
            "total_pages": (int(total) + lim - 1) // lim,
        }
    finally:
        conn.close()


def get_transaction_by_id(transaction_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT id, source_txn_id, user_id, timestamp, amount, merchant_category,
                   country, device_id, channel, risk_score, decision, risk_level, processing_seq
            FROM transactions WHERE id = ?
            """,
            (transaction_id,),
        ).fetchone()
        if row is None:
            return None
        result = _txn_dict(row)
        alert = conn.execute(
            "SELECT alert_id, transaction_id, user_id, timestamp, risk_score, risk_level "
            "FROM alerts WHERE transaction_id = ?", (transaction_id,)
        ).fetchone()
        result["alert"] = dict(alert) if alert else None
        return result
    finally:
        conn.close()


def dashboard_overview(recent_limit: int = 10) -> Dict[str, Any]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        analyzed = int(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0])
        flagged = int(
            conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE decision = 'fraud'"
            ).fetchone()[0]
        )
        high_risk = int(
            conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE risk_level = 'HIGH'"
            ).fetchone()[0]
        )
        avg_row = conn.execute("SELECT AVG(risk_score) FROM transactions").fetchone()[0]
        dist_rows = conn.execute(
            "SELECT risk_level, COUNT(*) AS n FROM transactions GROUP BY risk_level"
        ).fetchall()
        dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for r in dist_rows:
            if r["risk_level"] in dist:
                dist[r["risk_level"]] = int(r["n"])
        recent = conn.execute(
            """
            SELECT id, source_txn_id, user_id, timestamp, amount, merchant_category,
                   country, device_id, channel, risk_score, decision, risk_level, processing_seq
            FROM transactions
            ORDER BY processing_seq DESC
            LIMIT ?
            """,
            (recent_limit,),
        ).fetchall()
        return {
            "transactions_analyzed": analyzed,
            "flagged_transactions": flagged,
            "high_risk": high_risk,
            "average_risk_score": float(avg_row) if avg_row is not None else 0.0,
            "risk_distribution": dist,
            "behavioral_signal_summary": {
                "available": False,
                "reason": "Behavioral features are not persisted with transactions.",
                "signals": {},
            },
            "recent_transactions": [_txn_dict(r) for r in recent],
            "stream_state": get_stream_state(),
        }
    finally:
        conn.close()


def query_users(
    *,
    q: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
) -> Dict[str, Any]:
    lim, off = _page_window(page, limit)
    clauses: List[str] = []
    params: List[Any] = []
    if q:
        clauses.append("CAST(user_id AS TEXT) LIKE ?")
        params.append(f"%{q}%")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    inner = f"""
        SELECT user_id,
               COUNT(*) AS transaction_count,
               AVG(amount) AS average_amount,
               (SELECT risk_score FROM transactions t2 WHERE t2.user_id = transactions.user_id ORDER BY processing_seq DESC LIMIT 1) AS latest_risk_score,
               MAX(timestamp) AS latest_timestamp,
               SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_count,
               COUNT(DISTINCT device_id) AS known_devices,
               COUNT(DISTINCT country) AS known_countries,
               MAX(processing_seq) AS last_processing_seq
        FROM transactions
        {where}
        GROUP BY user_id
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM ({inner})", params
        ).fetchone()[0]
        rows = conn.execute(
            f"""
            {inner}
        ORDER BY last_processing_seq DESC
            LIMIT ? OFFSET ?
            """,
            params + [lim, off],
        ).fetchall()
        items = []
        for r in rows:
            items.append(
                {
                    "user_id": r["user_id"],
                    "transaction_count": int(r["transaction_count"]),
                    "average_amount": float(r["average_amount"]) if r["average_amount"] is not None else 0.0,
                    "latest_risk_score": float(r["latest_risk_score"]) if r["latest_risk_score"] is not None else 0.0,
                    "latest_timestamp": int(r["latest_timestamp"]),
                    "high_risk_count": int(r["high_risk_count"] or 0),
                    "known_device_count": int(r["known_devices"]),
                    "known_country_count": int(r["known_countries"]),
                }
            )
        return {"items": items, "total": int(total), "page": page, "limit": lim, "total_pages": (int(total) + lim - 1) // lim}
    finally:
        conn.close()


def get_user_detail(user_id: int, recent_limit: int = 20) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT user_id,
                   COUNT(*) AS transaction_count,
                   AVG(amount) AS average_amount,
                   (SELECT risk_score FROM transactions t2 WHERE t2.user_id = transactions.user_id ORDER BY processing_seq DESC LIMIT 1) AS latest_risk_score,
                   MAX(timestamp) AS latest_timestamp,
                   SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_count,
                   COUNT(DISTINCT device_id) AS known_devices,
                   COUNT(DISTINCT country) AS known_countries,
                   MAX(processing_seq) AS last_processing_seq
            FROM transactions
            WHERE user_id = ?
            GROUP BY user_id
            """,
            (int(user_id),),
        ).fetchone()
        if row is None:
            return None
        match = {
            "user_id": row["user_id"],
            "transaction_count": int(row["transaction_count"]),
            "average_amount": float(row["average_amount"]) if row["average_amount"] is not None else 0.0,
            "latest_risk_score": float(row["latest_risk_score"]) if row["latest_risk_score"] is not None else 0.0,
            "latest_timestamp": int(row["latest_timestamp"]),
            "high_risk_count": int(row["high_risk_count"] or 0),
            "known_device_count": int(row["known_devices"]),
            "known_country_count": int(row["known_countries"]),
        }
    finally:
        conn.close()
    recent = query_transactions(user_id=int(user_id), limit=recent_limit, page=1)
    match["recent_transactions"] = recent["items"]
    return match


def query_alerts(
    *,
    q: Optional[str] = None,
    risk_level: Optional[str] = None,
    user_id: Optional[int] = None,
    page: int = 1,
    limit: int = 50,
) -> Dict[str, Any]:
    lim, off = _page_window(page, limit)
    clauses: List[str] = []
    params: List[Any] = []
    if q:
        like = f"%{q}%"
        clauses.append(
            "(CAST(alert_id AS TEXT) LIKE ? OR CAST(transaction_id AS TEXT) LIKE ? "
            "OR CAST(user_id AS TEXT) LIKE ?)"
        )
        params.extend([like, like, like])
    if risk_level:
        clauses.append("risk_level = ?")
        params.append(risk_level)
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(int(user_id))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM alerts {where}", params).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT alert_id, transaction_id, user_id, timestamp, risk_score, risk_level
            FROM alerts
            {where}
            ORDER BY alert_id DESC
            LIMIT ? OFFSET ?
            """,
            params + [lim, off],
        ).fetchall()
        items = [
            {
                "alert_id": r["alert_id"],
                "transaction_id": r["transaction_id"],
                "user_id": r["user_id"],
                "timestamp": r["timestamp"],
                "risk_score": r["risk_score"],
                "risk_level": r["risk_level"],
            }
            for r in rows
        ]
        return {"items": items, "total": int(total), "page": page, "limit": lim, "total_pages": (int(total) + lim - 1) // lim}
    finally:
        conn.close()


def get_alert_by_id(alert_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT alert_id, transaction_id, user_id, timestamp, risk_score, risk_level
            FROM alerts WHERE alert_id = ?
            """,
            (alert_id,),
        ).fetchone()
        if row is None:
            return None
        result = {
            "alert_id": row["alert_id"],
            "transaction_id": row["transaction_id"],
            "user_id": row["user_id"],
            "timestamp": row["timestamp"],
            "risk_score": row["risk_score"],
            "risk_level": row["risk_level"],
        }
        txn = conn.execute(
            "SELECT id, source_txn_id, user_id, timestamp, amount, merchant_category, country, device_id, channel, risk_score, decision, risk_level, processing_seq FROM transactions WHERE id = ?",
            (row["transaction_id"],),
        ).fetchone()
        result["transaction"] = _txn_dict(txn) if txn else None
        return result
    finally:
        conn.close()


class TransactionContext:
    """Simple context manager for a SQLite transaction.
    It commits on normal exit and rolls back on exception.
    """
    def __init__(self):
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> sqlite3.Connection:
        self.conn = get_connection()
        self.conn.execute("BEGIN")
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self.conn is None:
            return False
        if exc_type is None:
            self.conn.execute("COMMIT")
        else:
            self.conn.execute("ROLLBACK")
        self.conn.close()
        # Do not suppress exceptions
        return False
