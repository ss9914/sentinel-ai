import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.security import decode_access_token
from app.database.session import Base, engine
from app.models import Alert, ApplicationLog, Incident, IncidentLog, User  # register metadata
from app.database.redis_client import get_redis
from app.services.broker import ALERT_CHANNEL


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()
app = FastAPI(title="SentinelAI", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/health")
def health():
    try: get_redis().ping(); redis_status = "healthy"
    except Exception: redis_status = "unavailable"
    return {"status": "healthy", "redis": redis_status}


@app.websocket("/api/v1/ws/alerts")
async def alerts_socket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    try:
        if not token or not decode_access_token(token).get("sub"):
            await websocket.close(code=1008)
            return
    except Exception:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    pubsub = get_redis().pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(ALERT_CHANNEL)
    try:
        while True:
            message = await asyncio.to_thread(pubsub.get_message, timeout=1.0)
            if message: await websocket.send_json(json.loads(message["data"]))
            await asyncio.sleep(0.05)
    except WebSocketDisconnect: pass
    finally:
        pubsub.close()
