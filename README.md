# SentinelAI

SentinelAI is a real-time incident detection platform for application logs. It persists every event, learns normal service behavior with Isolation Forest, creates incidents for unusual activity, and pushes alerts to a React operations console without refreshes.

## Problem and features

Operational teams often discover service degradation only after customers report it. SentinelAI provides authenticated ingestion, PostgreSQL auditability, per-service anomaly baselines, incident lifecycle APIs, Redis-backed background processing, and WebSocket dashboard delivery.

## Architecture

`Log source → FastAPI → PostgreSQL + Redis queue → worker → feature extraction + Isolation Forest → incident + alert → Redis Pub/Sub → WebSocket → React`

The worker uses message/error signals, severity, latency, five-minute event volume, rolling error rate, and source presence. Each service learns independently. During the configurable baseline period it records normal observations; afterwards the Isolation Forest decision function is inverted and normalized so larger scores consistently mean more anomalous behavior. ERROR alone does not create an incident.

## Stack and structure

- FastAPI, SQLAlchemy, PostgreSQL, Redis, scikit-learn, JWT/Argon2
- React, Vite, Axios, React Router, native WebSocket
- Docker Compose, GitHub Actions, Alembic configuration

```
backend/app/{api,core,database,models,schemas,services,ml,workers}
backend/tests/                 API and detector tests
frontend/src/{components,pages,services}
scripts/generate_logs.py       configurable synthetic traffic
.github/workflows/ci.yml
```

## Run with Docker

1. Copy `.env.example` to `.env`, replace `POSTGRES_PASSWORD` and `JWT_SECRET_KEY`, and retain Docker host names (`postgres`, `redis`) in their URLs.
2. Run `docker compose up --build`.
3. Open [http://localhost:8080](http://localhost:8080), register an account, and log in.

The API is at `http://localhost:8000`; health is `/health`; interactive docs are `/docs`.

## Run without Docker

Create a PostgreSQL database and a Redis instance, then configure `DATABASE_URL` and `REDIS_URL` with `localhost` hosts in `.env`.

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
python -m app.workers.worker
```

In another terminal: `cd frontend && npm ci && npm run dev`.

## API and log flow

Register with `POST /api/v1/auth/register`, use the returned Bearer token for `POST /api/v1/logs`, and read paginated `/logs`, `/incidents`, and `/alerts`. Update resolution via `PATCH /api/v1/incidents/{id}`. The dashboard summary is `/dashboard/summary`; live alerts use the JWT-protected `/api/v1/ws/alerts?token=TOKEN` endpoint.

Example anomaly input: `{"level":"CRITICAL","service":"payments","message":"Database connection timeout","latency_ms":30000}`. Once a baseline exists and its behavior is anomalous, SentinelAI stores the score and detection evidence on the log, creates a HIGH/CRITICAL incident, persists a SENT dashboard alert, and broadcasts it.

For a live demo after registering, get the token from browser storage and run: `python scripts/generate_logs.py --token YOUR_TOKEN --spike`. Run it without `--spike` first to establish baseline traffic.

## Testing and delivery

Run `cd backend && pytest -q`; run `cd frontend && npm run build`. GitHub Actions performs both checks plus container builds. `.env` is ignored and production secrets are supplied only via environment variables. The service boundaries map directly to AWS ECS/Fargate (API/worker), RDS PostgreSQL, ElastiCache Redis, an ALB, and a static frontend hosted behind CloudFront; deployment configuration is intentionally not included.
