from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

import numpy as np
from sklearn.ensemble import IsolationForest

from app.core.config import get_settings

LEVEL_VALUE = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
ERROR_WORDS = ("error", "failed", "failure", "exception", "timeout", "denied", "unavailable", "refused", "crash")


@dataclass
class Detection:
    is_anomaly: bool
    score: float
    details: str


class AnomalyDetector:
    """Per-service Isolation Forest with rolling rate and message features."""
    def __init__(self, minimum_samples: int | None = None, contamination: float | None = None):
        settings = get_settings()
        self.minimum_samples = minimum_samples or settings.anomaly_baseline_samples
        self.contamination = contamination or settings.anomaly_contamination
        self.baselines: dict[str, deque[list[float]]] = defaultdict(lambda: deque(maxlen=500))
        self.models: dict[str, IsolationForest] = {}
        self.recent: dict[str, deque[tuple[datetime, bool]]] = defaultdict(deque)

    def features(self, payload: dict) -> list[float]:
        now = datetime.now(timezone.utc)
        service = payload["service"]
        events = self.recent[service]
        cutoff = now - timedelta(minutes=5)
        while events and events[0][0] < cutoff:
            events.popleft()
        message = payload["message"].lower()
        error_ratio = sum(is_error for _, is_error in events) / max(len(events), 1)
        return [
            float(LEVEL_VALUE[payload["level"]]),
            min(len(payload["message"]), 1000) / 1000,
            min(sum(word in message for word in ERROR_WORDS), 4) / 4,
            min(payload.get("latency_ms") or 0, 60_000) / 60_000,
            min(len(events), 100) / 100,
            error_ratio,
            1.0 if payload.get("ip_address") else 0.0,
        ]

    def analyze(self, payload: dict) -> Detection:
        service = payload["service"]
        vector = self.features(payload)
        is_error = payload["level"] in {"ERROR", "CRITICAL"}
        self.recent[service].append((datetime.now(timezone.utc), is_error))
        baseline = self.baselines[service]
        if service not in self.models:
            baseline.append(vector)
            if len(baseline) < self.minimum_samples:
                return Detection(False, 0.0, f"baseline learning ({len(baseline)}/{self.minimum_samples} samples)")
            model = IsolationForest(n_estimators=150, contamination=self.contamination, random_state=42)
            model.fit(np.asarray(baseline))
            self.models[service] = model
            return Detection(False, 0.0, "baseline established")
        model = self.models[service]
        raw = float(model.decision_function(np.asarray([vector]))[0])
        anomaly = bool(model.predict(np.asarray([vector]))[0] == -1)
        # Higher score always means more anomalous; decision_function is inverted.
        score = max(0.0, min(1.0, 0.5 - raw))
        return Detection(anomaly, score, f"isolation_forest raw={raw:.4f}; five_minute_events={len(self.recent[service])}")


detector = AnomalyDetector()
