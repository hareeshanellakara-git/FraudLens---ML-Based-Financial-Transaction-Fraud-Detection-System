import pandas as pd
import numpy as np
from typing import Dict, List

from .state_store import StateStore
from .feature_engineering import get_feature_columns, add_behavioral_features

class RealTimeFeatureEngine:
    """Process transactions one‑by‑one using an in‑memory :class:`StateStore`.

    The engine mirrors the semantics of :func:`src.feature_engineering.add_behavioral_features`
    but without recomputing the whole history for each transaction.  It is deliberately
    lightweight – it only requires the raw transaction fields that are present in the
    processed CSV files.
    """

    def __init__(self) -> None:
        self.store = StateStore()

    def process_transaction(self, txn: Dict) -> Dict:
        """Generate the 27 features for a single transaction dictionary.

        ``txn`` must contain the keys used by the batch pipeline:
        ``user_id, timestamp, amount, device_id, country, merchant_category, channel``.
        The returned mapping contains **all** feature column names in the order returned
        by :func:`get_feature_columns`.  ``None`` values are used for missing data – callers
        can replace them with ``np.nan`` if required.
        """
        user_id = txn["user_id"]
        state = self.store.get_state(user_id)
        features = state.generate_features(txn)
        # Ensure the result contains every column expected by the model.
        # Missing columns are filled with ``None`` (later converted to ``np.nan``).
        ordered: Dict = {col: features.get(col, None) for col in get_feature_columns()}
        return ordered

    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process an entire DataFrame in chronological order.

        The DataFrame must already be sorted by ``user_id`` and ``timestamp`` – this is the
        same ordering used by the batch implementation.  The method iterates row‑wise,
        feeding each transaction to :meth:`process_transaction` and collecting the results
        into a new DataFrame with the exact feature columns.
        """
        required_cols = [
            "user_id",
            "timestamp",
            "amount",
            "device_id",
            "country",
            "merchant_category",
            "channel",
        ]
        missing = set(required_cols) - set(df.columns)
        if missing:
            raise ValueError(f"Input DataFrame missing required columns: {missing}")

        # Ensure deterministic ordering – same as batch.
        df_sorted = df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)
        records: List[Dict] = []
        for _, row in df_sorted.iterrows():
            txn = row.to_dict()
            feats = self.process_transaction(txn)
            records.append(feats)
        result = pd.DataFrame(records)
        # Convert ``None`` to ``np.nan`` for consistency with batch output.
        result = result.replace({None: np.nan})
        return result
