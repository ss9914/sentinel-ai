import json

from app.database.session import SessionLocal
from app.ml.detector import detector
from app.models import ApplicationLog
from app.services.incidents import create_incident_and_alert


def process_log(log_id: int) -> bool:
    with SessionLocal() as db:
        log = db.get(ApplicationLog, log_id)
        if log is None: return False
        result = detector.analyze({"level": log.level, "service": log.service, "message": log.message, "latency_ms": log.latency_ms, "ip_address": log.ip_address})
        log.anomaly_score = result.score
        log.is_anomaly = result.is_anomaly
        log.detection_details = result.details
        db.commit()
        if result.is_anomaly:
            create_incident_and_alert(db, log)
        return result.is_anomaly
