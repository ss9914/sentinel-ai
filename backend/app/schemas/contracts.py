from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Severity = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
IncidentStatus = Literal["OPEN", "ACKNOWLEDGED", "RESOLVED"]


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogCreate(BaseModel):
    level: Severity
    service: str = Field(min_length=2, max_length=100)
    message: str = Field(min_length=1, max_length=5000)
    source: Optional[str] = Field(default=None, max_length=100)
    request_id: Optional[str] = Field(default=None, max_length=100)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    latency_ms: Optional[float] = Field(default=None, ge=0, le=3_600_000)
    timestamp: Optional[datetime] = None


class LogRead(LogCreate):
    id: int
    received_at: datetime
    anomaly_score: Optional[float]
    is_anomaly: bool
    detection_details: Optional[str]
    model_config = ConfigDict(from_attributes=True)


class IncidentUpdate(BaseModel):
    status: Optional[IncidentStatus] = None
    resolution_note: Optional[str] = Field(default=None, max_length=4000)


class IncidentRead(BaseModel):
    id: int; title: str; description: str; severity: str; status: str; service: str; anomaly_score: float; detected_at: datetime; resolved_at: Optional[datetime]; resolution_note: Optional[str]
    model_config = ConfigDict(from_attributes=True)


class AlertRead(BaseModel):
    id: int; incident_id: int; channel: str; title: str; message: str; severity: str; status: str; created_at: datetime; sent_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


class DashboardSummary(BaseModel):
    total_logs: int
    anomalies: int
    open_incidents: int
    alerts_24h: int
