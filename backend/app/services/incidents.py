from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, ApplicationLog, Incident, IncidentLog
from app.services.broker import publish_alert


def severity_for(score: float, level: str) -> str:
    if level == "CRITICAL" or score >= 0.35: return "CRITICAL"
    if level == "ERROR" or score >= 0.22: return "HIGH"
    if score >= 0.12: return "MEDIUM"
    return "LOW"


def create_incident_and_alert(db: Session, log: ApplicationLog) -> Incident:
    severity = severity_for(log.anomaly_score or 0.0, log.level)
    incident = Incident(title=f"Unusual {log.service} behavior", description=f"{log.message} (log #{log.id})", severity=severity, service=log.service, anomaly_score=log.anomaly_score or 0.0)
    db.add(incident); db.flush()
    db.add(IncidentLog(incident_id=incident.id, log_id=log.id))
    alert = Alert(incident_id=incident.id, title=incident.title, message=incident.description, severity=severity, status="SENT", sent_at=datetime.now(timezone.utc))
    db.add(alert); db.commit(); db.refresh(incident); db.refresh(alert)
    publish_alert({"type": "alert", "id": alert.id, "incident_id": incident.id, "title": alert.title, "message": alert.message, "severity": alert.severity, "status": alert.status, "created_at": alert.created_at.isoformat()})
    return incident
