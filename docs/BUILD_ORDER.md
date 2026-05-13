# Build Order

> **Getting Started**: Read [INSTALL.md](../INSTALL.md) first for environment setup and 1-click install instructions.

Step-by-step execution order. Each step depends on the previous. Do not skip ahead.

## Phase 0: Infrastructure + Seed Data

```bash
# Start PostgreSQL and Redis (Docker recommended for these only)
docker compose up -d postgres redis

# Or install natively:
# PostgreSQL 15: sudo apt install postgresql-15
# Redis 7: sudo apt install redis-server
```

### 0.1 Create database and tables
- File: `backend/db/models.py` — define all SQLAlchemy models per DATABASE_SCHEMA.md
- File: `backend/db/session.py` — database connection factory
- File: `backend/db/seed.py` — table creation + seed runner
- Run: `python -m backend.db.seed` to create tables

### 0.2 Generate seed data & Map Assets
- File: `scripts/generate_seed_data.py` — generates `vehicles_seed.json`, `historical_incidents.json`, `checkpoints.json`
- File: `scripts/fetch_osm_data.py` — downloads NH-275 OpenStreetMap data via Overpass API and saves as `nh275-osm.geojson`.
- Run: `python scripts/generate_seed_data.py`
- Run: `python scripts/fetch_osm_data.py`
- Run: `python scripts/seed_db.py` to load seed data into PostgreSQL + initialize Redis keys

**Checkpoint**: `psql raah -c "SELECT count(*) FROM vehicles"` → 50,000

---

## Phase 1: Simulator

Build the simulator first. Everything downstream depends on it.

### 1.1 Core simulator
- File: `simulator/config.py` — time scale, rates, checkpoint config
- File: `simulator/main.py` — FastAPI app, startup lifecycle, tick loop
- File: `simulator/generators/anpr.py` — ANPR event generation per SIMULATION_GUIDE.md
- File: `simulator/generators/fastag.py` — FASTag generation with pairing logic
- File: `simulator/generators/cctv.py` — CCTV motion index generation

### 1.2 Scenarios
- File: `simulator/generators/scenarios.py` — all 5 injectable scenarios
- Expose: `POST /scenario`, `GET /status`, `POST /config`, `POST /reset`

**Checkpoint**: Start simulator, verify events appearing in Redis Streams:
```bash
redis-cli XLEN stream:anpr  # Should grow rapidly
redis-cli XLEN stream:fastag
redis-cli XLEN stream:cctv
```

---

## Phase 2: Backend Core

### 2.1 App skeleton
- File: `backend/main.py` — FastAPI app factory, lifespan handler for background tasks, Socket.IO mount
- File: `backend/config.py` — env var loading
- File: `backend/auth/jwt.py` — JWT creation/validation
- File: `backend/auth/routes.py` — POST `/auth/login`

### 2.2 Ingestion pipeline
- File: `backend/ingestion/consumer.py` — Redis Stream consumer (ANPR, FASTag, CCTV)
- File: `backend/ingestion/enrichment.py` — vehicle DB lookup for ANPR events
- File: `backend/ingestion/validators.py` — schema validation
- Start as background task in lifespan handler

**Checkpoint**: Start backend, verify enriched events flowing:
```bash
redis-cli XLEN stream:enriched  # Should grow
psql raah -c "SELECT count(*) FROM checkpoint_events"  # Should grow
```

### 2.3 Journey reconstruction
- File: `backend/journey/reconstruction.py` — enriched event consumer, journey object management
- File: `backend/journey/state.py` — Redis journey read/write helpers

**Checkpoint**: `redis-cli KEYS "journey:*"` → should show active journey keys

### 2.4 Hard logic engine
- File: `backend/hard_logic/rules.py` — rules E1–E5, R1–R3 per HARD_LOGIC_ENGINE.md
- File: `backend/hard_logic/engine.py` — rule executor, consumes journey updates
- File: `backend/hard_logic/legal_events.py` — legal event record builder

**Checkpoint**: Inject ghost_vehicle scenario → verify `legal_events` table has E4 records

### 2.5 Zone state aggregator
- File: `backend/zones/aggregator.py` — 30-second tick, zone state vector computation
- File: `backend/zones/baselines.py` — baseline read/write

**Checkpoint**: `redis-cli GET "zone_state:ZONE-06"` → should return JSON

### 2.6 Alert engine + WebSocket
- File: `backend/alerts/engine.py` — consume legal_events + ml_alerts streams, dedup, prioritize
- File: `backend/alerts/websocket.py` — Socket.IO server with /authority and /commuter namespaces

### 2.7 Feedback service
- File: `backend/feedback/routes.py` — POST `/alerts/{id}/feedback`
- File: `backend/feedback/processor.py` — training label writer, sensor reliability updater

### 2.8 REST API routes
- File: `backend/api/routes.py` — all GET endpoints per API_CONTRACTS.md
- File: `backend/commuter/routes.py` — commuter endpoints
- File: `backend/commuter/estimator.py` — journey time estimation, toll calculation

**Checkpoint**: `curl http://localhost:8000/api/v1/dashboard/stats` → returns JSON with live data

---

## Phase 3: ML Service

### 3.1 Training pipeline
- File: `ml_service/training/data_prep.py` — extract features from journey/event data
- File: `ml_service/training/trainer.py` — train all 4 models, save to model_store/
- File: `scripts/train_models.py` — CLI entry point

Run initial training:
```bash
# Generate training data (run simulator in fast mode for ~2 min)
SIMULATOR_TIME_SCALE=120 python -m simulator.main &
sleep 120
# Train models
python scripts/train_models.py
```

### 3.2 Scoring service
- File: `ml_service/main.py` — FastAPI app, model loading, stream consumers
- File: `ml_service/models/evasion_scorer.py`
- File: `ml_service/models/zone_anomaly.py`
- File: `ml_service/models/wildlife_detector.py`
- File: `ml_service/models/risk_scorer.py`

**Checkpoint**: Inject evasion scenario → verify `ml_alerts` table has scored record

---

## Phase 4: Authority Dashboard

### 4.1 Project setup
```bash
cd authority-dashboard
npm create vite@latest ./ -- --template react
npm install socket.io-client leaflet react-leaflet recharts axios jwt-decode @turf/turf
npm install -D @types/leaflet @types/geojson
```

### 4.2 Build order
1. Auth context + login page
2. Layout shell (top nav + sidebar + main area)
3. Map component (Leaflet + OpenStreetMap GeoJSON layer + Turf.js spatial parsing)
4. Socket.IO connection hook
5. Live View tab (map + vehicle dots + zone overlays)
6. Alert feed sidebar (real-time alert cards)
7. Evasion Cases tab (table + evidence viewer)
8. Risk Heatmap tab (zone risk coloring + time slider)
9. Analytics tab (Recharts model metrics)
10. Simulator controls dropdown
11. Corridor view strip
12. Polish: animations, sounds, heartbeat indicator

**Checkpoint**: Open dashboard, see live map with vehicles, inject incident → see zone turn red

---

## Phase 5: Commuter Portal (Mobile Website)

### 5.1 Project setup
```bash
cd commuter-portal
npm create vite@latest ./ -- --template react
npm install socket.io-client leaflet react-leaflet axios jwt-decode
```

### 5.2 Build order
1. Auth + mobile layout shell
2. Route query form + results display
3. Active trip tracker (mini map + progress bar)
4. Risk warnings component
5. Socket.IO integration for live updates
6. Polish: dark theme, touch targets, animations

**Checkpoint**: Query route Mysore→Bangalore → see journey time, toll ₹320, risk warnings

---

## Phase 6: Integration + Demo Prep

1. Run full system end-to-end
2. Test all 5 demo scenarios
3. Test 4-minute demo flow
4. Fix timing issues (time scale tuning)
5. Record demo video as backup

---

## Dependency Lists

### simulator/requirements.txt
```
fastapi==0.111.0
uvicorn==0.30.1
redis==5.0.4
python-dotenv==1.0.1
```

### backend/requirements.txt
```
fastapi==0.111.0
uvicorn==0.30.1
redis==5.0.4
sqlalchemy==2.0.30
psycopg2-binary==2.9.9
python-socketio==5.11.2
python-jose[cryptography]==3.3.0
passlib==1.7.4
python-dotenv==1.0.1
pydantic==2.7.1
```

### ml_service/requirements.txt
```
fastapi==0.111.0
uvicorn==0.30.1
redis==5.0.4
sqlalchemy==2.0.30
psycopg2-binary==2.9.9
scikit-learn==1.5.0
joblib==1.4.2
numpy==1.26.4
pandas==2.2.2
shap==0.45.1
python-dotenv==1.0.1
```

### Frontend key dependencies (both apps)
```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.23.1",
    "socket.io-client": "^4.7.5",
    "leaflet": "^1.9.4",
    "react-leaflet": "^4.2.1",
    "recharts": "^2.12.7",
    "axios": "^1.7.2",
    "jwt-decode": "^4.0.0",
    "@turf/turf": "^6.5.0"
  }
}
```
