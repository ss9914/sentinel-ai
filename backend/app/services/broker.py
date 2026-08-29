import json
from typing import Any

from app.database.redis_client import get_redis

LOG_QUEUE = "sentinelai:logs"
ALERT_CHANNEL = "sentinelai:alerts"


def enqueue_log(log_id: int) -> None:
    get_redis().rpush(LOG_QUEUE, str(log_id))


def publish_alert(alert: dict[str, Any]) -> None:
    get_redis().publish(ALERT_CHANNEL, json.dumps(alert, default=str))
