
# RAAH — Smart Highway Monitoring & Compliance System

> AI co-pilot for Indian highway control rooms. Converts ANPR, FASTag, CCTV & government DB data into real-time enforcement intelligence, incident awareness, and commuter safety guidance.

**Hackathon**: AI for Bharat — Smart City / Smart Mobility / Smart Highways
**Corridor**: Mysore–Bangalore Expressway (NH-275), 120 km, both directions
**Nature**: Hackathon prototype. Simulated data, real schemas, real logic, real ML.

## The Problem

| Stat | Value |
|------|-------|
| Annual toll evasion loss | ₹15,000+ crore |
| Road deaths (2022) | 1.78 lakh |
| FASTag penetration | 97% |

The infrastructure and data exist. The intelligence layer connecting them does not. **RAAH is that layer.**

## Three-Layer Architecture

```
┌──────────────────────────────────────────────────────┐
│  Layer 1: HARD LOGIC (Law Compliance Engine)         │
│  Deterministic. Legal basis. AI never touches this.  │
│  Output: Legal event records, not predictions.       │
├──────────────────────────────────────────────────────┤
│  Layer 2: AI/ML (Intelligence Engine)                │
│  Patterns, probabilities, ambiguity.                 │
│  Output: Scored candidates. Never verdicts.          │
│  Human confirmation required for enforcement.        │
├──────────────────────────────────────────────────────┤
│  Layer 3: REINFORCEMENT (Feedback Engine)            │
│  Officer feedback → model retraining.                │
│  Hard logic immutable. ML improves over time.        │
└──────────────────────────────────────────────────────┘
```

## Features

| # | Feature | Layer | Purpose |
|---|---------|-------|---------|
| 1 | Toll Evasion Detection | L1+L2 | Non-payment, underpayment, misclassification, impossible journeys |
| 2 | Incident Detection | L2 | Zone anomaly detection from flow/motion patterns |
| 3 | Wildlife Intrusion | L2 | Non-vehicle motion in forest corridors |
| 4 | High Risk Zones | L2 | Nightly segment risk scoring with time-of-day curves |
| 5 | Commuter Intelligence | L1+L2 | Journey time, toll cost, risk warnings, departure recommendations |
| 6 | Route Monitoring | L1 | Live journey reconstruction — backbone for all features |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend API | Python 3.11 + FastAPI |
| ML Models | scikit-learn |
| Database | PostgreSQL 15 |
| Cache/State | Redis 7 (also Streams) |
| Authority Frontend | React 18 + Vite (PC-optimized) |
| Commuter Frontend | React 18 + Vite (mobile-optimized) |
| Maps | Leaflet.js + OpenStreetMap |
| Charts | Recharts |
| Real-time | Socket.IO |
| Containers | Docker Compose |

## Deployable Units

| Unit | Contains |
|------|----------|
| `simulator` | Standalone data generator, scenario injector |
| `backend` | Ingestion, Journey Engine, Hard Logic, Zone Aggregator, Alerts, Feedback, API |
| `ml_service` | Evasion Scorer, Zone Anomaly, Wildlife Detector, Risk Scorer |
| `authority-dashboard` | PC web app — map, alerts, evasion cases, analytics, feedback |
| `commuter-app` | Mobile-optimized web app — route query, journey tracker, warnings |
| `infra` | PostgreSQL + Redis via Docker Compose |

## Project Structure

```
RAAH/
├── docker-compose.yml
├── .env.example
├── docs/
│   ├── LEGAL_FRAMEWORK.md
│   ├── ARCHITECTURE.md
│   ├── DATA_PIPELINE.md
│   ├── ML_MODELS.md
│   ├── API_CONTRACTS.md
│   ├── DATABASE_SCHEMA.md
│   ├── HARD_LOGIC_ENGINE.md
│   ├── DASHBOARD_SPEC.md
│   ├── SIMULATION_GUIDE.md
│   └── COMPLIANCE_AND_ETHICS.md
├── simulator/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── config.py
│   ├── generators/
│   │   ├── anpr.py
│   │   ├── fastag.py
│   │   ├── cctv.py
│   │   └── scenarios.py
│   └── data/
│       ├── vehicles_seed.json
│       ├── checkpoints.json
│       └── historical_incidents.json
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── config.py
│   ├── db/
│   │   ├── models.py
│   │   ├── session.py
│   │   └── seed.py
│   ├── ingestion/
│   │   ├── consumer.py
│   │   ├── enrichment.py
│   │   └── validators.py
│   ├── journey/
│   │   ├── reconstruction.py
│   │   └── state.py
│   ├── hard_logic/
│   │   ├── engine.py
│   │   ├── rules.py
│   │   └── legal_events.py
│   ├── zones/
│   │   ├── aggregator.py
│   │   └── baselines.py
│   ├── alerts/
│   │   ├── engine.py
│   │   └── websocket.py
│   ├── feedback/
│   │   ├── routes.py
│   │   └── processor.py
│   ├── commuter/
│   │   ├── routes.py
│   │   └── estimator.py
│   ├── auth/
│   │   ├── jwt.py
│   │   └── routes.py
│   └── api/
│       └── routes.py
├── ml_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── models/
│   │   ├── evasion_scorer.py
│   │   ├── zone_anomaly.py
│   │   ├── wildlife_detector.py
│   │   └── risk_scorer.py
│   ├── training/
│   │   ├── trainer.py
│   │   └── data_prep.py
│   └── model_store/
├── authority-dashboard/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/
│       ├── hooks/
│       ├── context/
│       ├── components/
│       │   ├── map/
│       │   ├── alerts/
│       │   ├── evasion/
│       │   └── analytics/
│       ├── pages/
│       │   ├── LiveView.jsx
│       │   ├── RiskHeatmap.jsx
│       │   ├── EvasionCases.jsx
│       │   └── Analytics.jsx
│       └── styles/
├── commuter-app/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/
│       ├── hooks/
│       ├── components/
│       │   ├── RouteQuery.jsx
│       │   ├── JourneyTracker.jsx
│       │   ├── RiskWarnings.jsx
│       │   └── TollEstimate.jsx
│       ├── pages/
│       │   ├── Home.jsx
│       │   ├── Journey.jsx
│       │   └── ActiveTrip.jsx
│       └── styles/
└── scripts/
    ├── seed_db.py
    ├── train_models.py
    └── demo_reset.py
```

## Quick Start

```bash
# 1. Clone and configure
git clone <repo-url> && cd RAAH
cp .env.example .env

# 2. Start infrastructure (Docker for PostgreSQL + Redis only)
docker compose up -d postgres redis

# 3. Install Python dependencies
pip install -r backend/requirements.txt
pip install -r simulator/requirements.txt
pip install -r ml_service/requirements.txt

# 4. Seed database
python scripts/seed_db.py

# 5. Train initial ML models
python scripts/train_models.py

# 6. Start services (separate terminals)
cd backend && uvicorn main:asgi_app --port 8000 --reload
cd simulator && uvicorn main:app --port 8001 --reload
cd ml_service && uvicorn main:app --port 8002 --reload
cd authority-dashboard && npm install && npm run dev -- --port 5173
cd commuter-app && npm install && npm run dev -- --port 5174

# 7. Access
# Authority Dashboard: http://localhost:5173
# Commuter App:        http://localhost:5174
# API Docs:            http://localhost:8000/docs
```

**Demo credentials:** `authority / raah2024` | `commuter / raah2024`

## Team

| Role | Name |
|------|------|
| Lead | TBD |
| Backend | TBD |
| ML | TBD |
| Frontend | TBD |

## Docs Index

| Document | Purpose |
|----------|---------|
| [LEGAL_FRAMEWORK.md](docs/LEGAL_FRAMEWORK.md) | **Complete statutory basis** — all 7 laws, sections, rules governing system |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Services, data flow, design decisions, Docker setup |
| [BUILD_ORDER.md](docs/BUILD_ORDER.md) | Step-by-step execution guide for developers |
| [DATA_PIPELINE.md](docs/DATA_PIPELINE.md) | Simulator, schemas, ingestion, journey engine |
| [ML_MODELS.md](docs/ML_MODELS.md) | All 4 models, training, evaluation, feedback loop |
| [API_CONTRACTS.md](docs/API_CONTRACTS.md) | Every endpoint, WebSocket events, request/response schemas |
| [DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | PostgreSQL tables, Redis keys, seed data |
| [MAP_VISUALIZATION.md](docs/MAP_VISUALIZATION.md) | Map modes (Live/Historical), interactive GIS architecture |
| [HARD_LOGIC_ENGINE.md](docs/HARD_LOGIC_ENGINE.md) | Rules E1–E5, EX, R1–R3, legal citations, 2× penalty logic |
| [DASHBOARD_SPEC.md](docs/DASHBOARD_SPEC.md) | Authority + Commuter UI specs, About System modal |
| [SIMULATION_GUIDE.md](docs/SIMULATION_GUIDE.md) | Simulator architecture, scenarios, demo mode |
| [COMPLIANCE_AND_ETHICS.md](docs/COMPLIANCE_AND_ETHICS.md) | DPDP Act alignment, human-in-loop, evidence admissibility |

---

**Known Issue**: Speed limit for buses is inconsistently documented across files (80 km/h vs 90 km/h). This will be resolved during implementation based on actual highway regulations.

---

**RAAH** — Real-time AI Highway Monitoring System
