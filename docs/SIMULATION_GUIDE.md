# Simulation Guide

## Architecture

The simulator is a standalone Python service (`simulator/`) that acts as the data heartbeat. It generates all event streams that the rest of the system consumes. It is completely independent — replaceable with real data sources without changing any downstream service.

The simulation ecosystem operates in two strict phases:
1. **Phase 1: Historical Pre-computation (Seed)** — Generates 30 days of complete data permanently into PostgreSQL.
2. **Phase 2: Live Demo Stream** — Generates live traffic and interactive anomalies via Redis Streams for the 4-minute presentation.

```
simulator/
├── main.py              # FastAPI app + Live Demo Stream (Phase 2)
├── config.py            # Time scale, rates, environmental parameters
├── generators/
│   ├── historical.py    # Generates the 30-day seed (Phase 1)
│   ├── anpr.py          # Live ANPR stream
│   ├── fastag.py        # Live FASTag stream
│   ├── cctv.py          # Live CCTV stream
│   └── scenarios.py     # Live injectable anomalies (Phase 2)
└── data/
    ├── vehicles_seed.json       # 50,000 VAHAN-compliant records
    └── checkpoints.json         # 12 checkpoint configs
```

**Port**: 8001  
**Phase 1 Output**: PostgreSQL (`journeys`, `ml_alerts`, `zone_risk_profiles`, etc.)
**Phase 2 Output**: Redis Streams (`stream:anpr`, `stream:fastag`, `stream:cctv`)  
**Phase 2 Control**: REST API for scenario injection and configuration

---

## Time Scale

| Config | Value | Meaning |
|--------|-------|---------|
| `TIME_SCALE=60` (default) | 1 real minute = 1 highway hour | Demo mode. 2 real minutes shows full peak→off-peak cycle |
| `TIME_SCALE=1` | Real-time | Extended testing. 1 minute = 1 minute |
| `TIME_SCALE=120` | Fast-forward | Rapid data generation for ML training |

Configurable via `POST /simulator/config` or `SIMULATOR_TIME_SCALE` env var.

All event timestamps use simulated time. Each tick of the simulator advances simulated clock by `TIME_SCALE` seconds per real second.

---

## Vehicle Pool Management

At startup, simulator loads `vehicles_seed.json` and creates an active vehicle pool:

1. **Entry pool**: Vehicles randomly drawn from seed DB and "placed" at entry checkpoints (CP-01 for MB, CP-12 for BM)
2. **Active journeys**: Each vehicle progresses through checkpoints with realistic timing
3. **Exit**: Vehicle leaves at exit checkpoint, returns to entry pool after cooldown
4. **Pool size**: Controlled by vehicles/hour rate setting
5. **Direction split**: ~50/50 MB/BM with slight variance

**Vehicle journey simulation**:
```
1. Pick vehicle from pool
2. Assign direction (MB or BM)
3. Assign vehicle class (from DB or override for evasion)
4. Calculate expected journey times per segment (base + random jitter ±15%)
5. Schedule ANPR event at each checkpoint along route
6. Schedule FASTag event at each Full Plaza (15–45s after ANPR)
7. Generate CCTV motion contributions
8. If evasion vehicle: skip selected checkpoints/FASTag events
```

---

## ANPR Generation Logic

**File**: `simulator/generators/anpr.py`

### Event Rate

| Period | Simulated Hours | Vehicles/Hour | Vehicles/Tick (at TIME_SCALE=60) |
|--------|----------------|---------------|----------------------------------|
| Peak morning | 07:00–10:00 | 1200–1800 | 20–30 per second |
| Off-peak day | 10:00–17:00 | 300–500 | 5–8 per second |
| Peak evening | 17:00–21:00 | 1200–1800 | 20–30 per second |
| Night | 21:00–07:00 | 200–400 | 3–7 per second |

### Confidence Score Distribution

| Condition | Confidence Range | Frequency |
|-----------|-----------------|-----------|
| Normal read | 0.94–0.97 | 93% of reads |
| Slight degradation (rain, dust) | 0.80–0.93 | 4% |
| Heavy degradation (night, fog) | 0.60–0.75 | 3% |

### OCR Error Injection (2–3% of all reads)

| Error Type | Example | Frequency |
|------------|---------|-----------|
| Transposition | `AB1234` → `AB1243` | 40% of errors |
| Missing character | `AB1234` → `AB123` | 35% of errors |
| Substitution | `AB1234` → `AB12O4` (0→O) | 25% of errors |

When OCR error injected: `raw_read` has the error, `plate_number` has the error too (simulating what the system sees). This tests downstream fuzzy matching.

### Vehicle Class Mismatch (4% of reads)

ANPR camera detects a different class than what's registered. Usually one tier off (e.g., LMV detected as Car). This feeds E3 rule testing.

### Night Bias

Between 21:00–05:00 simulated time: heavy vehicle ratio increases to 60% (trucks prefer night runs). This is a real pattern on NH-275.

---

## FASTag Generation Logic

**File**: `simulator/generators/fastag.py`

### Pairing Rule

For every ANPR event at a toll plaza (CP-03, CP-06, CP-10, CP-11):
- Generate paired FASTag event with same `vehicle_plate`
- FASTag timestamp = ANPR timestamp + random(15, 45) seconds
- `plaza_id` = same checkpoint
- `amount_charged` = toll rate for `vehicle_class_tagged`
- `transaction_status` = `success` (default)

Note: CP-01 (Mysore Entry) and CP-12 (Bangalore Entry) are full plazas for ANPR/CCTV but do NOT collect toll. FASTag is read for journey registration only at these checkpoints — no `amount_charged`. CP-02 and CP-09 are monitors (ANPR + CCTV only, no FASTag reader).

### Failure Injection

| Failure | Rate | `transaction_status` | Behavior |
|---------|------|---------------------|----------|
| Low balance | 1.0% | `low_balance` | Transaction recorded but flagged. NOT evasion |
| Failed | 0.5% | `failed` | Transaction attempt failed. NOT evasion |
| Blacklisted | 0.1% | `blacklisted` | Tag on blacklist. Flagged separately |

### Evasion Injection

Controlled by `EVASION_BASE_RATE` config (default 5% of journeys).

**Type 1 — No FASTag (Hard Logic E1)**:
- ANPR event generated at Full Plaza
- No FASTag event generated
- Rate: 40% of evasion pool

**Type 2 — Underpayment (Hard Logic E2/E3)**:
- FASTag event generated but with lower vehicle class
- e.g., Truck detected by ANPR, FASTag charged as Car (₹80 instead of ₹270)
- Rate: 30% of evasion pool

**Type 3 — Plaza Skip (ML detection)**:
- Vehicle gets ANPR + FASTag at CP-01 and CP-12
- Zero ANPR/FASTag events at intermediate plazas
- Journey time is plausible (takes bypass roads — slower)
- Rate: 30% of evasion pool
- **Hotspot bias**: 60% of plaza-skip evasions use CP-03 (Nidaghatta) or CP-06 (Maddur) as the skipped plaza, matching real-world bypass routes

---

## CCTV Motion Generation Logic

**File**: `simulator/generators/cctv.py`

### Emission Rate

One event per camera per 5-second window. With 60 cameras: **12 events/second** at `TIME_SCALE=1`.

At `TIME_SCALE=60`: events are batched. Each real second generates 60 simulated seconds worth of CCTV events = 720 events per real second. These are batched into Redis Stream in chunks.

### Motion Index Computation

For each camera, motion index is computed from:

1. **Base flow**: Number of active vehicle journeys currently in that camera's zone → mapped to 0.6–0.9
2. **Noise**: Random jitter ±0.05
3. **Scenario overlay**: If active scenario affects this camera's zone, override pattern applied

### Normal Signatures

| Zone State | Motion Pattern |
|------------|----------------|
| Normal highway flow | 0.6–0.9 steady with ±0.05 noise |
| Low traffic (night/off-peak) | 0.3–0.5 |
| Toll plaza normal | Oscillating 0.3–0.8 (stop-go pattern) |
| Forest corridor normal | 0.5–0.7 (fewer vehicles, steady) |

---

## Phase 2: Live Demo Scenarios

During the real-time pitch, the Live Stream runs normally (`WX-CLR`). The UI triggers these interactive anomalies via `POST /simulator/scenario`. All are **deterministic and repeatable** for demo reliability.

### Scenario 1: Incident

**Trigger**: `{scenario: "incident", params: {zone_id: "ZONE-06", duration_minutes: 10}}`

**What happens**:
1. Stop generating exit ANPR events from the affected zone (vehicles enter but don't exit)
2. CCTV motion index at zone cameras: progressive drop `0.7 → 0.5 → 0.3 → 0.1` over 3–4 simulated minutes
3. Upstream checkpoint: vehicle density increases (vehicles arriving but not leaving)
4. After `duration_minutes`: motion spikes to 0.9 (clearance), then normalizes. Exit ANPR events resume.

**Expected downstream effects**:
- Zone Anomaly Detector flags `vehicle_throughput_deviation` and `flow_continuity_score` drop
- Incident classified as `partial_blockage` or `full_blockage`
- Alert pushed to authority dashboard
- Zone overlay turns amber → red on map

### Scenario 2: Evasion

**Trigger**: `{scenario: "evasion"}`

**What happens**:
1. Generate a specific vehicle with known plate (e.g., `KA09EV0001`)
2. ANPR at CP-01 (entry) at time T
3. ANPR at CP-12 (exit) at time T + 2400s (40 min)
4. Zero events at any intermediate checkpoint — no ANPR, no FASTag
5. Journey time 2400s is plausible for bypass route (not triggering E5)
6. But ALL 4 toll plazas skipped — this is the ML signal

**Expected downstream effects**:
- Journey Reconstruction shows `checkpoint_completeness = 0.17` (2/12)
- `payment_detection_ratio = 0.0` (0/4 toll plazas)
- Evasion Scorer outputs ~0.91 probability
- Evidence bundle generated with ₹320 estimated loss (Car × ₹80 × 4 missed toll plazas)

### Scenario 3: Wildlife

**Trigger**: `{scenario: "wildlife", params: {zone_id: "ZONE-04"}}`

Only valid for ZONE-04 or ZONE-07.

**What happens**:
1. Stop generating ANPR events in zone for 60 simulated seconds (traffic gap)
2. During gap: CCTV cameras in zone show motion pulse 0.12–0.18 for 10 seconds
3. After gap: resume vehicle generation, but vehicles entering zone have 20% longer inter-checkpoint times (speed reduction)
4. Speed reduction persists for 3–4 simulated minutes then normalizes

**Expected downstream effects**:
- Wildlife Detector fires: gap detected (Step 1), motion pulse detected (Step 2), speed reduction detected (Step 3)
- Confidence: ~0.85 (all 3 signals)
- Alert to authority dashboard with forest department notification

### Scenario 4: Ghost Vehicle

**Trigger**: `{scenario: "ghost_vehicle"}`

**What happens**:
1. Generate ANPR reads at CP-01, CP-03, CP-06 for a plate NOT in vehicles DB (e.g., `XX99ZZ0000`)
2. Confidence scores normal (0.94+)
3. No FASTag events at any plaza

**Expected downstream effects**:
- Ingestion enrichment sets `vehicle_db_match = false`
- Hard Logic E4 fires immediately on first read: "unregistered vehicle"
- Hard Logic E1 fires at each Full Plaza: "no FASTag"
- Multiple legal events generated

### Scenario 5: High Risk Hour

**Trigger**: `{scenario: "high_risk_hour", params: {duration_minutes: 5}}`

**What happens**:
1. Increase evasion injection rate from 5% to 15%
2. Increase random incident-like motion drops (1–2 zones get brief dips)
3. More vehicles with OCR errors
4. More class mismatches

**Expected downstream effects**:
- Alert feed fills faster
- Zone states fluctuate more
- Demonstrates system under load

---

## Phase 1: 30-Day Historical Pre-computation (Seed)

**Script**: `scripts/seed_db.py --historical-days 30` (runs during setup, before UI starts)

**Purpose**: Permanently load 30 days of data into PostgreSQL so the Authority Dashboard's Analytics and Map tabs render instantly without waiting for runtime processing.

### Environmental Contexts

The historical generator applies professional meteorological codes to daily segments:
- **`WX-CLR`** (Clear): 75% days. Baseline flow.
- **`WX-RA`** (Rain): 20% days. Flow continuity drops, speeds drop 15%. Incident rate +30%.
- **`WX-FG`** (Fog): 5% days. Speeds drop 40%, CCTV variance increases.

### ML "Hidden Correlations" (Generated for Training)

To make the ML models useful, Phase 1 injects deliberate patterns:
1. **PUC + Evasion Correlation**: `DIESEL` heavy vehicles (Truck/MAV) with expired `puc_upto` have a mathematically forced +25% probability of toll evasion in the simulation. The Evasion Scorer must discover this.
2. **Weather + Incident Correlation**: Minor accidents are 3x more likely during `WX-RA`. The Zone Anomaly Detector must learn not to confuse normal rain-slowdowns with accidents.
3. **Lighting + Wildlife**: `ILL-NIGHT-UNLIT` + `ZN-FOR` zones have a 4x higher probability of generating wildlife motion pulses.

### Vehicle Seed (`vehicles_seed.json`)

Generation rules (VAHAN-compliant):

```python
# 50,000 vehicles
# State distribution: KA=70%, TN=15%, AP=10%, Other=5%
# Class distribution: Car=50%, LMV=20%, Bus=10%, Truck=10%, MAV=5%, 2W=5%
# Fuel Type: Petrol=60%, Diesel=30%, EV=5%, CNG=5% (Diesel weighted heavily to Trucks)
# Maker/Model: Contextual based on class
# Status: active=97%, expired=2%, suspended=1%
# Plate format: {STATE}{DISTRICT:2d}{SERIES:2alpha}{NUMBER:4d}
# PUC/Fitness/Insurance expiry: 80% valid, 15% expiring within 60 days, 5% expired
# Permit status: valid=85%, expired=10%, not_required=5% (private vehicles)
# Exemptions: ~2% of vehicles (1,000 of 50,000) are exempt
#   - emergency: 0.5%
#   - government: 0.5%
#   - diplomatic: 0.3%
#   - military: 0.5%
#   - permit_exempt: 0.2%
```

### Checkpoint Config (`checkpoints.json`)

Static file matching the checkpoint table in DATA_PIPELINE.md. Includes `sensor_reliability` field for each checkpoint (simulated value, always >0.95, default 0.98).

### Historical Data Generation

Phase 1 completely skips Redis and computes the 30 days of data directly into PostgreSQL:

```python
# 1. Generate 30 days of journeys (approx 200,000 journeys)
# 2. Inject incidents according to WX and Zone correlations
# 3. Mathematically evaluate ML Evasion Scores for all journeys
# 4. Generate ml_alerts and officer feedback (alert_feedback)
# 5. Compute the final zone_risk_profiles for all 11 zones
```
```

### Checkpoint Config (`checkpoints.json`)

Static file matching the checkpoint table in DATA_PIPELINE.md. Loaded into both PostgreSQL `checkpoints` table and simulator memory.

---

## Demo Mode API Reference

All endpoints on simulator service (port 8001). Also proxied through backend at `POST /api/v1/simulator/*`.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/scenario` | Inject scenario |
| `GET` | `/status` | Current simulator state |
| `POST` | `/config` | Update time scale, rates |
| `POST` | `/reset` | Clear active scenarios |
| `GET` | `/health` | Health check |

See API_CONTRACTS.md for full request/response schemas.

---

## Consistency Guarantees

| Guarantee | Implementation |
|-----------|---------------|
| Event ordering | Each stream uses auto-generated Redis Stream IDs (time-based). Events for same vehicle are always in chronological order |
| ANPR-FASTag pairing | FASTag event always generated AFTER corresponding ANPR event with 15–45s delay. Same Redis Stream batch |
| Vehicle continuity | A vehicle's journey is generated as a complete plan upfront. Individual events are scheduled and emitted at correct simulated times |
| Checkpoint validity | Vehicles always progress in correct geographic order for their direction. No out-of-order checkpoints in normal flow |
| Scenario isolation | Active scenarios only affect their target zone's generators. Other zones continue normally |
| Repeatability | Scenarios use deterministic sequences. Same scenario trigger → same vehicle plates, same timestamps (relative to trigger time), same event pattern |
