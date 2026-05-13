# RAAH — Real-time AI Highway Monitoring System

RAAH is a real-time AI-powered highway monitoring system for NH-275 (Mysore-Bangalore corridor). It combines sensor fusion, machine learning, and deterministic hard logic to detect toll evasion, zone anomalies, wildlife intrusion, and traffic incidents while incorporating human-in-the-loop oversight.

## Architecture

```
┌─────────────┐     Redis Streams     ┌─────────────────┐
│  Simulator  │ ─────────────────────► │     Backend     │
│   :8001     │  (anpr/fastag/cctv)  │     :8000       │
└─────────────┘                      │  (FastAPI + DB)  │
                                    └────────┬────────┘
                                             │
                                    ┌────────▼────────┐
                                    │  ML Service     │
                                    │    :8002       │
                                    └────────┬────────┘
                                             │
                              ┌──────────────┼──────────────┐
                              ▼              ▼              ▼
                    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
                    │  Auth Dashboard │ │  Commuter Portal│ │   PostgreSQL    │
                    │     :5173       │ │     :5174       │ │    + Redis      │
                    └─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Quick Start

1. **Start infrastructure**:
   ```bash
   docker-compose up -d
   ```

2. **Seed the database**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python db/seed.py
   ```

3. **Start services**:
   ```bash
   # Simulator
   cd simulator
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8001

   # Backend
   cd backend
   uvicorn main:app --reload --port 8000

   # ML Service
   cd ml_service
   uvicorn main:app --reload --port 8002
   ```

4. **Start dashboards** (in separate terminals):
   ```bash
   cd authority-dashboard
   npm install
   npm run dev

   cd commuter-portal
   npm install
   npm run dev
   ```

## Services

| Service | Port | Tech |
|---------|------|------|
| Simulator | 8001 | FastAPI + Redis |
| Backend | 8000 | FastAPI + SQLAlchemy + PostgreSQL |
| ML Service | 8002 | FastAPI + Redis |
| Auth Dashboard | 5173 | React + Leaflet + Socket.IO |
| Commuter Portal | 5174 | React |
| PostgreSQL | 5432 | Official Image |
| Redis | 6379 | Official Image |

## API Endpoints

### Authentication
- `POST /auth/login` — Login for authority/commuter

### Simulator
- `POST /scenario` — Inject scenario (high_risk_hour, incident, wildlife_crossing, etc.)
- `GET /status` — Simulator status
- `POST /config` — Update simulator config
- `POST /reset` — Reset simulator

### Backend
- `GET /api/v1/dashboard/stats` — Dashboard statistics
- `POST /api/v1/simulator/scenario` — Proxy to simulator
- `GET /api/v1/commuter/journey/{plate}/{direction}` — Journey tracking

### ML Service
- `POST /ml/score_alert` — Score an alert
- `GET /ml/health` — Health check
- `POST /ml/train/pipeline` — Trigger training

## Data Flow

1. **Simulator** generates ANPR, FASTag, and CCTV events every tick
2. **Backend** ingests events via Redis Streams
3. **Hard Logic** engine evaluates deterministic rules (evasion, wildlife corridor, reverse)
4. **ML Service** generates probabilistic scores for complex patterns
5. **Alert Engine** publishes alerts via Socket.IO to dashboards
6. **Human officers** review ML alerts and confirm/dismiss

## Checkpoints (NH-275)

| ID | Name | Km | Type |
|----|------|----|------|
| CP-01 | Mysore Entry | 0 | Monitor |
| CP-02 | Srirangapatna | 15 | Monitor |
| CP-03 | Nidaghatta Toll | 28 | Full Plaza |
| CP-04 | Cauvery Zone Entry | 40 | Wildlife Sensor |
| CP-05 | Cauvery Zone Exit | 55 | Wildlife Sensor |
| CP-06 | Maddur Toll | 58 | Full Plaza |
| CP-07 | Mandya Forest Entry | 62 | Wildlife Sensor |
| CP-08 | Mandya Forest Exit | 71 | Wildlife Sensor |
| CP-09 | Ramanagara | 82 | Monitor |
| CP-10 | Bidadi Toll | 95 | Full Plaza |
| CP-11 | Kengeri Toll | 114 | Full Plaza |
| CP-12 | Bangalore Entry | 120 | Monitor |

## Zones

| ID | Name | Km | Class | Access |
|----|------|----|-------|--------|
| ZONE-01 | Mysore Entry–Srirangapatna | 0-15 | ZN-RUR | ACC-CTRL |
| ZONE-02 | Srirangapatna–Nidaghatta | 15-28 | ZN-RUR | ACC-CTRL |
| ZONE-03 | Nidaghatta–Cauvery Entry | 28-40 | ZN-RUR | ACC-CTRL |
| ZONE-04 | Cauvery Wildlife Corridor | 40-55 | ZN-FOR | ACC-CTRL |
| ZONE-05 | Cauvery Exit–Maddur | 55-58 | ZN-RUR | ACC-CTRL |
| ZONE-06 | Maddur–Mandya Forest Entry | 58-62 | ZN-RUR | ACC-CTRL |
| ZONE-07 | Mandya Forest Corridor | 62-71 | ZN-FOR | ACC-CTRL |
| ZONE-08 | Mandya Exit–Ramanagara | 71-82 | ZN-RUR | ACC-CTRL |
| ZONE-09 | Ramanagara–Bidadi | 82-95 | ZN-RUR | ACC-CTRL |
| ZONE-10 | Bidadi–Kengeri | 95-114 | ZN-URB | ACC-CTRL |
| ZONE-11 | Kengeri–Bangalore Entry | 114-120 | ZN-URB | ACC-CTRL |

## ML Models

| Model | Type | Input | Output |
|-------|------|-------|--------|
| Evasion Classifier | Logistic Regression | Plazas charged, class mismatch, reverse | Evasion probability |
| Zone Anomaly | DBSCAN/Isolation Forest | Traffic stats, CCTV motion | Zone anomaly score |
| Wildlife Intrusion | Forest Classifier | Segment risk, motion tree, cluster pattern | Wildlife probability |
| Corridor Risk | Fusion | Evasion + Anomaly + Wildlife + Incident peak hour | Risk tier |