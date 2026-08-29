"""Continuously send realistic normal and incident-like application logs."""
import argparse
import random
import time
from datetime import datetime, timezone

import requests

SERVICES = ["api-gateway", "payments", "orders", "auth", "inventory"]
NORMAL = ["Request completed", "Cache hit", "Order synchronized", "Session refreshed", "Health check passed"]
INCIDENTS = ["Database connection timeout after 30000ms", "Authentication failures exceeded threshold", "Upstream payment service unavailable", "Unhandled exception while processing order"]


def payload(spike: bool) -> dict:
    abnormal = spike or random.random() < 0.06
    level = random.choice(["ERROR", "CRITICAL"]) if abnormal else random.choices(["INFO", "WARNING"], [0.88, 0.12])[0]
    return {"timestamp": datetime.now(timezone.utc).isoformat(), "level": level, "service": random.choice(SERVICES), "source": "synthetic-generator", "message": random.choice(INCIDENTS if abnormal else NORMAL), "latency_ms": random.randint(5000, 45000) if abnormal else random.randint(10, 450), "ip_address": f"10.0.0.{random.randint(1, 254)}"}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--url", default="http://localhost:8000/api/v1"); parser.add_argument("--token", required=True); parser.add_argument("--interval", type=float, default=0.5); parser.add_argument("--spike", action="store_true")
    args = parser.parse_args(); headers = {"Authorization": f"Bearer {args.token}"}
    while True:
        response = requests.post(f"{args.url}/logs", json=payload(args.spike), headers=headers, timeout=5)
        print(response.status_code, response.text[:120]); time.sleep(args.interval)


if __name__ == "__main__": main()
