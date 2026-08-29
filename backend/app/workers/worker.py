import logging

from app.database.redis_client import get_redis
from app.services.broker import LOG_QUEUE
from app.services.processing import process_log

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinelai.worker")


def run() -> None:
    redis = get_redis()
    logger.info("SentinelAI worker listening on %s", LOG_QUEUE)
    while True:
        item = redis.blpop(LOG_QUEUE, timeout=5)
        if item is None: continue
        try: process_log(int(item[1]))
        except Exception: logger.exception("Unable to process queued log %s", item[1])


if __name__ == "__main__": run()
