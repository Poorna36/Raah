# Architecture

## Deployable Units

| Unit | Port | Tech | Role |
|------|------|------|------|
| `simulator` | 8001 | Python | Generates all event streams |
| `backend` | 8000 | FastAPI | Ingestion, logic, alerts, API |
| `ml_service` | 8002 | Python + scikit-learn | Scoring, training, risk analysis |
| `authority-dashboard` | 5173 | React + Vite | PC web — officer control room |
| `commuter-app` | 5174 | React + Vite | Mobile web — commuter interface |
| `postgres` | 5432 | PostgreSQL 15 | Persistent storage |
| `redis` | 6379 | Redis 7 | State, streams, cache |

## Data Flow

```
Simulator (8001)
    │ Redis Streams (stream:anpr, stream:fastag, stream:cctv)
    ▼
Ingestion Consumer (backend)
    │ 1. Validate event schema
    │ 2. Enrich ANPR with vehicle DB lookup
    │ 3. Write raw event → PostgreSQL (checkpoint_events/fastag_events/cctv_events)
    │ 4. Emit enriched event → Redis Stream (stream:enriched)
    ▼
Journey Reconstruction (backend)
    │ 1. Read enriched events
    │ 2. Upsert journey object → Redis (journey:{plate}:{direction})
    │ 3. Write journey snapshot → PostgreSQL (journeys table)
    │ 4. Emit journey update → Redis Stream (stream:journey_updates)
    ▼
┌───────────────────────┬──────────────────────────┐
│ Hard Logic Engine     │ Zone State Aggregator     │
│ (backend)             │ (backend, 30s tick)       │
│                       │                           │
│ Reads: journey update │ Reads: recent events      │
│ Runs: rules E1–E5,    │ Computes: zone vectors    │
│       R1–R3           │ Writes: Redis zone_state   │
│ Writes: legal_events  │ Writes: PostgreSQL zone    │
│         → PostgreSQL  │         baselines          │
│ Emits: stream:legal   │ Emits: stream:zone_states  │
└───────────┬───────────┴────────────┬─────────────┘
            │                        │
            │                        ▼
            │              ML Scoring Service (8002)
            │                │ Reads: journey updates +
            │                │        zone state vectors
            │                │ Runs: evasion scorer,
            │                │       zone anomaly detector,
            │                │       wildlife detector
            │                │ Writes: ml_alerts → PostgreSQL
            │                │ Emits: stream:ml_alerts
            │                ▼
            └──────► Alert Engine (backend) ◄───────┘
                        │ 1. Consume legal events + ML alerts
                        │ 2. Deduplicate (same vehicle+rule+10min window)
                        │ 3. Priority sort (legal > high-conf ML > low-conf ML)
                        │ 4. Update Redis (active_alerts:{zone_id} cache)
                        │ 5. Emit via Socket.IO
                        ▼
              ┌─────────┴──────────┐
              ▼                    ▼
   Authority Dashboard      Commuter App
   (Socket.IO namespace:     (Socket.IO namespace:
    /authority)               /commuter)
              │
              ▼
       Officer Feedback
              │
              ▼
       Feedback Service (backend)
              │ 1. Write feedback → PostgreSQL (alert_feedback)
              │ 2. Update training dataset labels
              │ 3. Update sensor_reliability in Redis
              │ 4. Signal ml_service for recalibration
              ▼
       ML Service Nightly Retrain
              │ Reads labeled data → retrains models
              │ Writes new model artifacts → model_store/
              │ Updates model_metrics → PostgreSQL
```

## Intermediate Data Persistence

Every pipeline stage persists its output before emitting downstream. If any downstream service crashes, data is recoverable.

| Stage | Persists To | Format | Recovery |
|-------|-------------|--------|----------|
| Simulator → events | Redis Streams | JSON | Consumer groups track position |
| Ingestion → raw events | PostgreSQL | checkpoint_events, fastag_events, cctv_events | Replay from stream position |
| Ingestion → enriched events | Redis Stream (stream:enriched) | JSON | Consumer group offset |
| Journey Reconstruction → journey state | Redis (journey:{plate}:{dir}) | JSON, TTL 24h | Rebuild from PostgreSQL journeys |
| Journey Reconstruction → snapshot | PostgreSQL (journeys) | Row per journey | Permanent |
| Hard Logic → violations | PostgreSQL (legal_events) | Row per violation | Permanent |
| Zone Aggregator → zone state | Redis (zone_state:{id}) | JSON, TTL 60s | Recompute from recent events |
| Zone Aggregator → baselines | PostgreSQL (zone_baselines) | Row per zone/slot | Permanent |
| ML Service → alerts | PostgreSQL (ml_alerts) | Row per alert | Permanent |
| Alert Engine → active alerts | Redis (active_alerts:{zone_id}) | JSON array | Rebuild from PostgreSQL |
| Feedback → labels | PostgreSQL (alert_feedback) | Row per feedback | Permanent |
| Risk Scorer → profiles | PostgreSQL (zone_risk_profiles) | Row per zone | Permanent |

## Redis Streams Architecture

```
stream:anpr           → consumer group: ingestion
stream:fastag         → consumer group: ingestion
stream:cctv           → consumer group: ingestion
stream:enriched       → consumer group: journey_engine
stream:journey_updates→ consumer groups: hard_logic, ml_service
stream:zone_states    → consumer group: ml_service
stream:legal_events   → consumer group: alert_engine
stream:ml_alerts      → consumer group: alert_engine
```

Each consumer group uses `XREADGROUP` with auto-acknowledgment after processing + persistence. If a consumer restarts, it resumes from last acknowledged position.

## Redis Key Structures (Live State)

*Note: Keys are partitioned by `highway_id`. For the demo, `NH-275` is the active partition.*

| Key Pattern | Value | TTL | Purpose |
|-------------|-------|-----|---------|
| `journey:{highway_id}:{plate}:{direction}` | Journey JSON object | 24h | Live journey tracking |
| `zone_state:{highway_id}:{zone_id}` | Zone state vector JSON | 60s | Current zone metrics for ML |
| `zone_baseline:{highway_id}:{zone_id}:{slot}:{day}` | Baseline stats JSON | 7d | Rolling averages |
| `sensor_reliability:{checkpoint_id}` | Float 0–1 | None | Sensor trust score |
| `active_alerts:{zone_id}` | Alert list JSON | 1h | Current alerts per zone |

## PostgreSQL vs Redis Decision

| Use PostgreSQL for | Use Redis for |
|--------------------|---------------|
| All permanent event records | Live journey objects (mutable, high-frequency updates) |
| Legal event records (audit trail) | Zone state vectors (60s TTL, consumed by ML in real-time) |
| ML alert records | Event streaming (Redis Streams) |
| Feedback labels | Sensor reliability scores (frequently read cache) |
| Historical baselines | Active alerts cache |
| Model metrics | Baselines cache (7d rolling, backed by PostgreSQL) |

**Rule: If it's evidence or audit → PostgreSQL. If it's live state or streaming → Redis. If both → Redis is cache, PostgreSQL is source of truth.**

## Socket.IO Architecture

**Server**: Runs inside backend process (`backend/alerts/websocket.py`).

**Namespaces**:

| Namespace | Client | Events Emitted | Events Received |
|-----------|--------|----------------|-----------------|
| `/authority` | Authority Dashboard | `legal_alert`, `ml_alert`, `zone_update`, `journey_update`, `wildlife_alert`, `model_metrics` | `feedback_submit`, `subscribe_zone` |
| `/commuter` | Commuter App | `route_alert`, `journey_progress`, `zone_warning` | `track_journey`, `query_route` |

**Connection flow**:
1. Client connects with JWT in `auth` query param
2. Server validates JWT, checks role
3. Authority clients auto-join room `authority:all`
4. Commuter clients join room `commuter:{plate}` when tracking

## Layer Separation Enforcement

| Rule | Enforcement |
|------|-------------|
| Hard logic never calls ML | `hard_logic/` module has zero imports from `ml_service/` |
| ML never produces verdicts | ML output schema has `candidate_status` field, never `verdict` |
| ML requires human confirmation | `ml_alerts` table has `officer_action` column, default `pending_review` |
| Feedback never modifies hard logic | Feedback processor only writes to `alert_feedback` and signals ML retrain |
| Legal events are immutable | `legal_events` table: no UPDATE/DELETE permissions for app user |

## Service Communication Matrix

| From → To | Method | Data |
|-----------|--------|------|
| Simulator → Ingestion | Redis Streams | Raw events |
| Ingestion → Journey Engine | Redis Stream (enriched) | Enriched events |
| Journey Engine → Hard Logic | Redis Stream (journey_updates) | Journey state |
| Journey Engine → ML Service | Redis Stream (journey_updates) | Journey state |
| Zone Aggregator → ML Service | Redis Stream (zone_states) | Zone vectors |
| Hard Logic → Alert Engine | Redis Stream (legal_events) | Legal records |
| ML Service → Alert Engine | Redis Stream (ml_alerts) | Scored alerts |
| Alert Engine → Dashboards | Socket.IO | Real-time alerts |
| Dashboard → Feedback Service | REST API (POST) | Officer feedback |
| Feedback Service → ML Service | Redis pub/sub (`channel:retrain_signal`) | Retrain trigger |

## Startup Order

```bash
# docker-compose.yml depends_on chain:
postgres → redis → backend → simulator → ml_service → authority-dashboard → commuter-app
```

1. PostgreSQL starts, runs migrations
2. Redis starts
3. Backend starts: runs DB seed check, starts ingestion consumers, zone aggregator tick, alert engine, Socket.IO server
4. Simulator starts: begins emitting events
5. ML Service starts: loads models from model_store/, starts consuming journey_updates and zone_states
6. Frontends start: connect to backend Socket.IO and REST API

## Backend Background Task Architecture

The backend runs multiple background consumers/tickers inside one FastAPI process using the `lifespan` context manager.

```python
# backend/main.py
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
import socketio

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: launch all background tasks
    tasks = [
        asyncio.create_task(run_ingestion_consumer()),      # Reads stream:anpr/fastag/cctv
        asyncio.create_task(run_journey_consumer()),         # Reads stream:enriched
        asyncio.create_task(run_hard_logic_consumer()),      # Reads stream:journey_updates
        asyncio.create_task(run_alert_engine_consumer()),    # Reads stream:legal_events + stream:ml_alerts
        asyncio.create_task(run_zone_aggregator_tick()),     # 30-second tick loop
        asyncio.create_task(run_journey_timeout_checker()),  # 60-second tick loop
    ]
    yield
    # Shutdown: cancel all tasks
    for task in tasks:
        task.cancel()

app = FastAPI(lifespan=lifespan)
asgi_app = socketio.ASGIApp(sio, other_app=app)

# Each consumer is an async loop:
async def run_ingestion_consumer():
    while True:
        events = await redis.xreadgroup('ingestion', 'consumer-1', {'stream:anpr': '>', 'stream:fastag': '>', 'stream:cctv': '>'}, count=100, block=1000)
        for stream, messages in events:
            for msg_id, data in messages:
                await process_event(stream, data)
                await redis.xack(stream, 'ingestion', msg_id)

async def run_zone_aggregator_tick():
    while True:
        await compute_all_zone_states()
        await asyncio.sleep(30)
```

**Key pattern**: Each consumer uses `XREADGROUP` with `block=1000` (1 second) so it yields control back to the event loop regularly. Zone aggregator and timeout checker use `asyncio.sleep()` between ticks.

## Redis Consumer Group Initialization

Consumer groups must be created before consumers can use `XREADGROUP`. Do this at backend/ml_service startup:

```python
# backend/main.py (inside lifespan, before creating tasks)
async def init_consumer_groups(redis):
    groups = [
        ('stream:anpr', 'ingestion'),
        ('stream:fastag', 'ingestion'),
        ('stream:cctv', 'ingestion'),
        ('stream:enriched', 'journey_engine'),
        ('stream:journey_updates', 'hard_logic'),
        ('stream:journey_updates', 'ml_service'),
        ('stream:zone_states', 'ml_service'),
        ('stream:legal_events', 'alert_engine'),
        ('stream:ml_alerts', 'alert_engine'),
    ]
    for stream, group in groups:
        try:
            await redis.xgroup_create(stream, group, id='0', mkstream=True)
        except Exception:
            pass  # Group already exists
```

## Checkpoint Coordinates (for Leaflet map)

Approximate lat/lng for NH-275 corridor checkpoints:

| CP ID | Location | KM | Lat | Lng |
|-------|----------|-----|-----|-----|
| CP-01 | Mysore Entry | 0 | 12.2958 | 76.6394 |
| CP-02 | Srirangapatna | 15 | 12.4181 | 76.6997 |
| CP-03 | Nidaghatta Toll | 28 | 12.5048 | 76.8236 |
| CP-04 | Cauvery Zone Entry | 40 | 12.4020 | 76.9500 |
| CP-05 | Cauvery Zone Exit | 55 | 12.4800 | 77.0500 |
| CP-06 | Maddur Toll | 58 | 12.5832 | 77.0452 |
| CP-07 | Mandya Forest Entry | 62 | 12.6100 | 77.0800 |
| CP-08 | Mandya Forest Exit | 71 | 12.6500 | 77.1500 |
| CP-09 | Ramanagara | 82 | 12.7227 | 77.2816 |
| CP-10 | Bidadi Toll | 95 | 12.7938 | 77.3869 |
| CP-11 | Kengeri Toll | 114 | 12.9024 | 77.4827 |
| CP-12 | Bangalore Entry | 120 | 12.9716 | 77.5946 |

**Map center**: `[12.63, 77.05]`, zoom level `10`.

**Highway polyline**: Connect checkpoint coordinates in order. For a more accurate route, use OpenStreetMap Nominatim or hardcode a simplified GeoJSON path through the waypoints.

## Docker Compose (Infrastructure Only)

Docker is used for PostgreSQL and Redis only. Python and React services run directly for faster iteration.

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: raah
      POSTGRES_USER: raah
      POSTGRES_PASSWORD: raah2024
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-LINE", "pg_isready -U raah"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 5

volumes:
  pgdata:
```

**Running services directly** (recommended during development):
```bash
# Terminal 1: Infrastructure
docker compose up -d postgres redis

# Terminal 2: Backend
cd backend && pip install -r requirements.txt && uvicorn main:asgi_app --host 0.0.0.0 --port 8000 --reload

# Terminal 3: Simulator
cd simulator && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 4: ML Service
cd ml_service && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8002 --reload

# Terminal 5: Authority Dashboard
cd authority-dashboard && npm install && npm run dev -- --port 5173

# Terminal 6: Commuter App
cd commuter-app && npm install && npm run dev -- --port 5174
```
