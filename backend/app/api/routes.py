from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database.session import get_db
from app.models import Alert, ApplicationLog, Incident, User
from app.schemas.contracts import AlertRead, DashboardSummary, IncidentRead, IncidentUpdate, LogCreate, LogRead, Page, Token, UserCreate, UserLogin
from app.services.processing import process_log

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)


def process_log_in_background(log_id: int) -> None:
    """Run detection in the API service when no separate worker is deployed."""
    try:
        process_log(log_id)
    except Exception:
        logger.exception("Unable to process log %s", log_id)


@router.post("/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where((User.username == data.username) | (User.email == data.email))):
        raise HTTPException(409, "Username or email already registered")
    user = User(username=data.username, email=str(data.email), hashed_password=hash_password(data.password))
    db.add(user); db.commit(); db.refresh(user)
    return Token(access_token=create_access_token(str(user.id)))


@router.post("/auth/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username))
    if not user or not user.is_active or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password", headers={"WWW-Authenticate": "Bearer"})
    return Token(access_token=create_access_token(str(user.id)))


def page_response(query, model, page: int, page_size: int, db: Session) -> Page:
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return Page(items=[model.model_validate(item).model_dump() for item in items], total=total, page=page, page_size=page_size)


@router.post("/logs", response_model=LogRead, status_code=status.HTTP_201_CREATED)
def ingest_log(data: LogCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), _: User = Depends(current_user)):
    payload = data.model_dump(exclude={"timestamp"}, exclude_none=True)
    payload["level"] = data.level.upper()
    log = ApplicationLog(**payload, timestamp=data.timestamp or datetime.now(timezone.utc))
    db.add(log); db.commit(); db.refresh(log)
    background_tasks.add_task(process_log_in_background, log.id)
    return log


@router.get("/logs", response_model=Page)
def logs(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(current_user)):
    return page_response(select(ApplicationLog).order_by(ApplicationLog.timestamp.desc()), LogRead, page, page_size, db)


@router.get("/incidents", response_model=Page)
def incidents(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(current_user)):
    return page_response(select(Incident).order_by(Incident.detected_at.desc()), IncidentRead, page, page_size, db)


@router.patch("/incidents/{incident_id}", response_model=IncidentRead)
def update_incident(incident_id: int, data: IncidentUpdate, db: Session = Depends(get_db), _: User = Depends(current_user)):
    incident = db.get(Incident, incident_id)
    if not incident: raise HTTPException(404, "Incident not found")
    if data.status: incident.status = data.status
    if data.resolution_note is not None: incident.resolution_note = data.resolution_note
    if incident.status == "RESOLVED" and not incident.resolved_at: incident.resolved_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(incident); return incident


@router.get("/alerts", response_model=Page)
def alerts(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(current_user)):
    return page_response(select(Alert).order_by(Alert.created_at.desc()), AlertRead, page, page_size, db)


@router.get("/dashboard/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), _: User = Depends(current_user)):
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return DashboardSummary(total_logs=db.scalar(select(func.count()).select_from(ApplicationLog)) or 0, anomalies=db.scalar(select(func.count()).select_from(ApplicationLog).where(ApplicationLog.is_anomaly.is_(True))) or 0, open_incidents=db.scalar(select(func.count()).select_from(Incident).where(Incident.status != "RESOLVED")) or 0, alerts_24h=db.scalar(select(func.count()).select_from(Alert).where(Alert.created_at >= since)) or 0)
