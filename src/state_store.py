import bisect
import collections
from collections import deque
from typing import Dict, List, Optional

SHORT_WINDOW = 10000
MEDIUM_WINDOW = 50000
LONG_WINDOW = 175000

class UserState:
    """In‑memory per‑user incremental statistics needed to reproduce the 27 batch features.

    The implementation follows the exact semantics of ``src.feature_engineering.add_behavioral_features``.
    It stores:
    * count of previous transactions (``user_transaction_count``)
    * running sum / sum‑of‑squares for mean & std (Welford's algorithm)
    * a sorted list of historical amounts for median computation
    * previous values for amount, timestamp, device, country and merchant_category
    * sets of seen identifiers for ``new_*`` flags
    * three deques containing timestamps of recent transactions for the sliding‑window counts
    """

    __slots__ = (
        "count",
        "sum_amount",
        "sum_sq_amount",
        "amounts_sorted",
        "prev_amount",
        "prev_timestamp",
        "prev_device",
        "prev_country",
        "prev_merchant",
        "seen_devices",
        "seen_countries",
        "seen_merchants",
        "short_window_ts",
        "medium_window_ts",
        "long_window_ts",
    )

    def __init__(self) -> None:
        self.count: int = 0  # number of *previous* transactions
        self.sum_amount: float = 0.0
        self.sum_sq_amount: float = 0.0
        self.amounts_sorted: List[float] = []
        self.prev_amount: Optional[float] = None
        self.prev_timestamp: Optional[int] = None
        self.prev_device: Optional[str] = None
        self.prev_country: Optional[str] = None
        self.prev_merchant: Optional[str] = None
        self.seen_devices: set = set()
        self.seen_countries: set = set()
        self.seen_merchants: set = set()
        self.short_window_ts: deque = deque()
        self.medium_window_ts: deque = deque()
        self.long_window_ts: deque = deque()

    # ----- helper statistical methods -----
    def _update_running_stats(self, amount: float) -> None:
        """Update sum, sum‑of‑squares and sorted list with a new *previous* amount.
        This is called **after** the features for the current transaction have been emitted,
        i.e. the amount becomes part of the history for the next transaction.
        """
        self.sum_amount += amount
        self.sum_sq_amount += amount * amount
        bisect.insort(self.amounts_sorted, amount)
        self.count += 1

    def _mean(self) -> Optional[float]:
        if self.count == 0:
            return None
        return self.sum_amount / self.count

    def _std(self) -> Optional[float]:
        if self.count < 2:
            return None
        # Sample standard deviation (ddof=1) to match pandas expanding().std()
        variance = (self.sum_sq_amount - (self.sum_amount ** 2) / self.count) / (self.count - 1)
        return variance ** 0.5 if variance >= 0 else None

    def _median(self) -> Optional[float]:
        if self.count == 0:
            return None
        mid = self.count // 2
        if self.count % 2 == 1:
            return float(self.amounts_sorted[mid])
        else:
            return (self.amounts_sorted[mid - 1] + self.amounts_sorted[mid]) / 2.0

    # ----- sliding window handling -----
    def _prune_deques(self, current_ts: int) -> None:
        while self.short_window_ts and self.short_window_ts[0] < current_ts - SHORT_WINDOW:
            self.short_window_ts.popleft()
        while self.medium_window_ts and self.medium_window_ts[0] < current_ts - MEDIUM_WINDOW:
            self.medium_window_ts.popleft()
        while self.long_window_ts and self.long_window_ts[0] < current_ts - LONG_WINDOW:
            self.long_window_ts.popleft()

    # ----- public API -----
    def generate_features(self, txn: Dict) -> Dict:
        """Compute the 27 features for *txn* using the stored state.

        The returned dictionary contains **all** feature column names defined in
        ``feature_engineering.get_feature_columns()``. Missing‑value semantics (``np.nan``)
        are reproduced by using ``None`` which callers can convert to ``np.nan`` if desired.
        """
        # Extract raw fields
        amount = txn["amount"]
        device = txn["device_id"]
        country = txn["country"]
        merchant = txn["merchant_category"]
        timestamp = txn["timestamp"]
        channel = txn.get("channel")  # channel is already a feature, but not needed for state

        # Prepare feature dict with raw values
        features: Dict = {
            "amount": amount,
            "merchant_category": merchant,
            "country": country,
            "channel": channel,
        }

        # timestamp_gap
        if self.prev_timestamp is None:
            features["timestamp_gap"] = None
        else:
            features["timestamp_gap"] = timestamp - self.prev_timestamp

        # prev_amount
        features["prev_amount"] = self.prev_amount

        # user statistics based on *previous* transactions only
        mean = self._mean()
        median = self._median()
        std = self._std()
        features["user_avg_amount"] = mean
        features["user_median_amount"] = median
        features["user_std_amount"] = std
        features["user_transaction_count"] = self.count

        # amount derived features
        if self.prev_amount is None:
            features["amount_diff"] = None
            features["amount_ratio"] = None
        else:
            diff = amount - self.prev_amount
            features["amount_diff"] = diff
            features["amount_ratio"] = amount / self.prev_amount if self.prev_amount != 0 else None

        # amount_vs_avg and amount_zscore use historical mean/std (not including current)
        if mean is None or mean == 0:
            features["amount_vs_avg"] = None
        else:
            features["amount_vs_avg"] = amount / mean
        if mean is None or std is None or std == 0:
            features["amount_zscore"] = None
        else:
            features["amount_zscore"] = (amount - mean) / std

        # change flags compared to *previous* identifiers
        features["device_changed"] = int(self.prev_device is not None and device != self.prev_device)
        features["country_changed"] = int(self.prev_country is not None and country != self.prev_country)
        features["merchant_changed"] = int(self.prev_merchant is not None and merchant != self.prev_merchant)

        # new_* flags – first occurrence of the identifier for this user
        features["new_device"] = int(device not in self.seen_devices)
        features["new_country"] = int(country not in self.seen_countries)
        features["new_merchant_category"] = int(merchant not in self.seen_merchants)

        # sliding‑window transaction counts (excluding current transaction)
        self._prune_deques(timestamp)
        features["transactions_last_short_window"] = len(self.short_window_ts)
        features["transactions_last_medium_window"] = len(self.medium_window_ts)
        features["transactions_last_long_window"] = len(self.long_window_ts)

        # rapid_transaction
        rapid = (
            (features["timestamp_gap"] is not None and features["timestamp_gap"] <= SHORT_WINDOW)
            and (self.count > 0)
        )
        features["rapid_transaction"] = int(rapid)

        # velocity spikes
        features["high_velocity_short"] = int(features["transactions_last_short_window"] >= 2)
        features["high_velocity_medium"] = int(features["transactions_last_medium_window"] >= 4)
        features["high_velocity_long"] = int(features["transactions_last_long_window"] >= 8)

        # ---- Update state for the *next* transaction ----
        self.short_window_ts.append(timestamp)
        self.medium_window_ts.append(timestamp)
        self.long_window_ts.append(timestamp)

        self.seen_devices.add(device)
        self.seen_countries.add(country)
        self.seen_merchants.add(merchant)

        self.prev_amount = amount
        self.prev_timestamp = timestamp
        self.prev_device = device
        self.prev_country = country
        self.prev_merchant = merchant

        self._update_running_stats(amount)

        return features

class StateStore:
    """Container managing ``UserState`` objects for every active user.

    The store is deliberately lightweight – a plain ``dict`` keyed by ``user_id``.
    """

    def __init__(self) -> None:
        self._states: Dict[int, UserState] = {}

    def get_state(self, user_id: int) -> UserState:
        if user_id not in self._states:
            self._states[user_id] = UserState()
        return self._states[user_id]

    def clear(self) -> None:
        """Reset the entire store – useful for tests."""
        self._states.clear()
