# Data Pipeline

## Overview

```
Simulator → Redis Streams → Ingestion → Enrichment → Journey Engine → Hard Logic / ML
```

Every stage persists intermediate output before emitting downstream. See ARCHITECTURE.md intermediate data persistence table for full mapping.

---

## Source 1: ANPR Events

**Stream**: `stream:anpr`

```json
{
  "event_id": "uuid",
  "checkpoint_id": "CP-01",
  "camera_id": "CAM-001",
  "plate_number": "KA09AB1234",
  "timestamp": "2024-01-15T09:30:00Z",
  "confidence_score": 0.96,
  "vehicle_class_detected": "Car",
  "lane_id": "L1",
  "image_ref": "mock://anpr/2024/01/15/uuid.jpg",
  "direction": "MB",
  "raw_read": "KA09AB1234"
}
```

**Enums**: `vehicle_class_detected` — `2W, LMV, Car, Bus, Truck, MAV`  
**Enums**: `direction` — `MB` (Mysore→Bangalore), `BM` (Bangalore→Mysore)

**Simulation parameters**:

| Parameter | Peak (7–10am, 5–9pm) | Off-peak |
|-----------|----------------------|----------|
| Vehicles/hour | 1200–1800 | 300–500 |
| Confidence normal | 0.94–0.97 | 0.94–0.97 |
| Confidence degraded | 0.60–0.75 | 0.60–0.75 |
| OCR error rate | 2–3% | 2–3% |
| Class mismatch rate | 4% | 4% |
| Heavy vehicle ratio | Higher at night | Normal |

**OCR error types**: transposition (`AB→BA`), missing character (`1234→123`), substitution (`0→O`, `1→I`).

**Evasion injection**: Evasion vehicles have zero ANPR events at skipped checkpoints. They simply don't appear.

---

## Source 2: FASTag Transactions

**Stream**: `stream:fastag`

```json
{
  "transaction_id": "uuid",
  "tag_id": "FTAG-340290001234",
  "vehicle_plate": "KA09AB1234",
  "plaza_id": "CP-03",
  "timestamp": "2024-01-15T09:30:25Z",
  "amount_charged": 80.0,
  "vehicle_class_tagged": "Car",
  "transaction_status": "success",
  "bank_id": "ICICI"
}
```

**Enums**: `transaction_status` — `success, failed, blacklisted, low_balance`

**Pairing rule**: Every Full Plaza ANPR event generates a paired FASTag event within **15–45 seconds** (configurable jitter).

**Toll rates (per plaza)**:

| Vehicle Class | Rate (₹) |
|---------------|-----------|
| Car/LMV | 80 |
| LCV | 130 |
| Bus/Truck | 270 |
| MAV | 415 |

**Evasion types injected by simulator**:

| Type | Trigger | Detection Layer |
|------|---------|-----------------|
| E1: No FASTag | ANPR at Full Plaza, no FASTag within 90s | Hard Logic |
| E2: Underpayment | FASTag class < ANPR-detected class | Hard Logic |
| E3: Plaza skip | FASTag at CP-01 and CP-12 only, no intermediate | ML |

**Legitimate failures**: 1.5% of transactions have `low_balance` or `failed` status — not evasion, handled separately.

---

## Source 3: CCTV Motion Index

**Stream**: `stream:cctv`

```json
{
  "event_id": "uuid",
  "camera_id": "CAM-019",
  "checkpoint_id": "CP-04",
  "segment_id": "SEG-KM40-KM42",
  "timestamp": "2024-01-15T09:30:00Z",
  "motion_index": 0.72,
  "zone_type": "forest_corridor",
  "frame_window_seconds": 5
}
```

**Enums**: `zone_type` — `highway, toll_plaza, forest_corridor`

**Motion signatures**:

| Scenario | Motion Index Pattern |
|----------|---------------------|
| Normal highway flow | 0.6–0.9 steady |
| Incident forming | 0.5 → 0.3 → 0.1 over 3–4 min |
| Incident cleared | Sharp spike then return to normal |
| Wildlife intrusion | 0.08–0.25 pulse during vehicle gap, forest zone only |
| Toll plaza normal | Oscillating 0.3–0.8 |

**Emission rate**: One event per camera per 5 seconds.

---

## Source 4: Vehicle Database

**Not streamed.** Static dataset loaded into PostgreSQL `vehicles` table at seed time.

```json
{
  "plate_number": "KA09AB1234",
  "registered_class": "Car",
  "registration_state": "KA",
  "registration_status": "active",
  "owner_type": "private",
  "registration_date": "2020-03-15",
  "fitness_expiry": "2025-03-15",
  "insurance_expiry": "2025-06-30"
}
```

**Seed**: 50,000 records. Distribution: 97% active, 2% expired, 1% suspended.

**Usage**: Ingestion service enriches every ANPR event with vehicle DB lookup. Fields added: `registered_class`, `registration_status`, `owner_type`, `fitness_expiry`, `insurance_expiry`.

---

## Source 5: Historical Incident Database

**Not streamed.** Pre-seeded into PostgreSQL `historical_incidents` table.

```json
{
  "incident_id": "uuid",
  "segment_id": "SEG-KM56-KM58",
  "km_marker": 57.3,
  "incident_type": "accident",
  "severity": "major",
  "timestamp": "2023-08-14T14:22:00Z",
  "vehicles_involved": 3,
  "response_time_minutes": 18,
  "resolution_time_minutes": 95
}
```

**Enums**: `incident_type` — `accident, breakdown, obstruction, wildlife, weather`  
**Enums**: `severity` — `minor, major, fatal`

**Seed**: 18 months of synthetic data calibrated against MoRTH accident frequency for NH-275. Higher density at Maddur (KM 58) and Ramanagara (KM 82).

---

## Ingestion Pipeline

**File**: `backend/ingestion/consumer.py`

```
Input: Redis Streams (stream:anpr, stream:fastag, stream:cctv)
Output: PostgreSQL (raw events) + Redis Stream (stream:enriched)
```

**Processing steps for each event type**:

### ANPR Event Processing
1. Read from `stream:anpr` via `XREADGROUP`
2. Validate schema (reject malformed, log to error table)
3. Normalize plate format: strip spaces, uppercase, remove special chars
4. Lookup `vehicles` table by `plate_number`
5. If found: attach `registered_class`, `registration_status`, `fitness_expiry`, `insurance_expiry`
6. If not found: set `vehicle_db_match = false` (will trigger rule E4 downstream)
7. Write to PostgreSQL `checkpoint_events` table
8. Emit enriched event to `stream:enriched` with type `anpr`
9. `XACK` the stream message

### FASTag Event Processing
1. Read from `stream:fastag` via `XREADGROUP`
2. Validate schema
3. Write to PostgreSQL `fastag_events` table
4. Emit to `stream:enriched` with type `fastag`
5. `XACK`

### CCTV Event Processing
1. Read from `stream:cctv` via `XREADGROUP`
2. Validate schema
3. Write to PostgreSQL `cctv_events` table
4. Emit to `stream:enriched` with type `cctv`
5. `XACK`

**Enriched event format** (added wrapper):
```json
{
  "source_type": "anpr",
  "event": { "...original event fields..." },
  "enrichment": {
    "vehicle_db_match": true,
    "registered_class": "Car",
    "registration_status": "active",
    "fitness_expiry": "2025-03-15",
    "insurance_expiry": "2025-06-30",
    "permit_status": "valid",
    "permit_expiry": "2025-12-31",
    "is_exempt": false,
    "exemption_type": null,
    "exemption_reference": null
  },
  "ingested_at": "2024-01-15T09:30:01Z"
}
```

**Enrichment process for ANPR events**:
1. Lookup vehicle in PostgreSQL `vehicles` table by `plate_number`
2. If match found: add `registered_class`, `registration_status`, `fitness_expiry`, `insurance_expiry`, `permit_status`, `permit_expiry`
3. Lookup exemption in PostgreSQL `vehicle_exemptions` table by `plate_number` where `is_active = true` and current date between `valid_from` and `valid_until`
4. If exemption found: set `is_exempt = true`, add `exemption_type`, `exemption_reference`
5. If no vehicle match: set `vehicle_db_match = false`, all enrichment fields null

---

## Journey Reconstruction Engine

**File**: `backend/journey/reconstruction.py`

```
Input: Redis Stream (stream:enriched)
Output: Redis (journey:{plate}:{direction}) + PostgreSQL (journeys) + Redis Stream (stream:journey_updates)
```

### Journey Object Structure (Redis)

```json
{
  "plate": "KA09AB1234",
  "direction": "MB",
  "vehicle_class_anpr": "Car",
  "vehicle_class_registered": "Car",
  "vehicle_class_fastag": "Car",
  "entry_checkpoint": "CP-01",
  "entry_time": "2024-01-15T09:00:00Z",
  "last_checkpoint": "CP-06",
  "last_seen": "2024-01-15T09:45:00Z",
  "checkpoints_visited": [
    {"cp": "CP-01", "time": "2024-01-15T09:00:00Z", "type": "anpr"},
    {"cp": "CP-01", "time": "2024-01-15T09:00:22Z", "type": "fastag"},
    {"cp": "CP-03", "time": "2024-01-15T09:20:00Z", "type": "anpr"},
    {"cp": "CP-03", "time": "2024-01-15T09:20:30Z", "type": "fastag"},
    {"cp": "CP-06", "time": "2024-01-15T09:45:00Z", "type": "anpr"},
    {"cp": "CP-06", "time": "2024-01-15T09:45:35Z", "type": "fastag"}
  ],
  "expected_checkpoints": ["CP-01","CP-02","CP-03","CP-04","CP-05","CP-06","CP-07","CP-08","CP-09","CP-10","CP-11","CP-12"],
  "status": "active",
  "journey_start": "2024-01-15T09:00:00Z",
  "updated_at": "2024-01-15T09:45:35Z"
}
```

### Processing Logic

1. Read enriched event from `stream:enriched`
2. Extract `plate_number` and `direction`
3. Check Redis for existing journey: `GET journey:{plate}:{direction}`
4. **If no journey exists**: Create new journey object, set entry checkpoint, write to Redis (TTL 24h)
5. **If journey exists**: Append checkpoint event, update `last_checkpoint`, `last_seen`, `updated_at`
6. **On every update**: Write journey snapshot to PostgreSQL `journeys` table (upsert by plate+direction+journey_start)
7. **Emit journey update** to `stream:journey_updates`
8. **Timeout detection**: Background task runs every 60s, scans active journeys. If `last_seen` > 3× expected total journey time → set `status = timeout`, emit update.

### Expected Checkpoint Sequences

| Direction | Full Sequence |
|-----------|---------------|
| MB (Mysore→Bangalore) | CP-01 → CP-02 → CP-03 → CP-04 → CP-05 → CP-06 → CP-07 → CP-08 → CP-09 → CP-10 → CP-11 → CP-12 |
| BM (Bangalore→Mysore) | CP-12 → CP-11 → CP-10 → CP-09 → CP-08 → CP-07 → CP-06 → CP-05 → CP-04 → CP-03 → CP-02 → CP-01 |

### Inter-Checkpoint Distance & Minimum Time

| From → To | Distance (km) | Min Time @ 120 km/h (s) |
|-----------|---------------|--------------------------|
| CP-01 → CP-02 | 15 | 450 |
| CP-02 → CP-03 | 13 | 390 |
| CP-03 → CP-04 | 12 | 360 |
| CP-04 → CP-05 | 15 | 450 |
| CP-05 → CP-06 | 3 | 90 |
| CP-06 → CP-07 | 4 | 120 |
| CP-07 → CP-08 | 9 | 270 |
| CP-08 → CP-09 | 11 | 330 |
| CP-09 → CP-10 | 13 | 390 |
| CP-10 → CP-11 | 19 | 570 |
| CP-11 → CP-12 | 6 | 180 |

Speed limit: 120 km/h for cars, 80 km/h for trucks/buses. Minimum time calculated at speed limit — anything faster is physically impossible.

---

## Zone State Aggregator

**File**: `backend/zones/aggregator.py`

```
Input: PostgreSQL (recent events) — runs on 30-second tick
Output: Redis (zone_state:{zone_id}) + PostgreSQL (zone_baselines) + Redis Stream (stream:zone_states)
```

### Zone Definitions

Zones map to checkpoint pairs covering a road segment:

| Zone ID | Segment | KM Range | Checkpoints | Type |
|---------|---------|----------|-------------|------|
| ZONE-01 | Mysore Entry–Srirangapatna | 0–15 | CP-01, CP-02 | highway |
| ZONE-02 | Srirangapatna–Nidaghatta | 15–28 | CP-02, CP-03 | highway |
| ZONE-03 | Nidaghatta–Cauvery Entry | 28–40 | CP-03, CP-04 | highway |
| ZONE-04 | Cauvery Wildlife Corridor | 40–55 | CP-04, CP-05 | forest_corridor |
| ZONE-05 | Cauvery Exit–Maddur | 55–58 | CP-05, CP-06 | highway |
| ZONE-06 | Maddur–Mandya Forest Entry | 58–62 | CP-06, CP-07 | highway |
| ZONE-07 | Mandya Forest Corridor | 62–71 | CP-07, CP-08 | forest_corridor |
| ZONE-08 | Mandya Exit–Ramanagara | 71–82 | CP-08, CP-09 | highway |
| ZONE-09 | Ramanagara–Bidadi | 82–95 | CP-09, CP-10 | highway |
| ZONE-10 | Bidadi–Kengeri | 95–114 | CP-10, CP-11 | highway |
| ZONE-11 | Kengeri–Bangalore Entry | 114–120 | CP-11, CP-12 | highway |

### Zone State Vector (computed every 30s)

```json
{
  "zone_id": "ZONE-06",
  "timestamp": "2024-01-15T09:30:00Z",
  "vehicle_throughput_deviation": -0.15,
  "flow_continuity_score": 0.82,
  "cctv_motion_mean": 0.65,
  "cctv_motion_rate_of_change": -0.02,
  "fastag_rate_deviation": -0.10,
  "upstream_vs_downstream_density": 1.3,
  "opposing_direction_flow_rate": 0.91,
  "time_slot_baseline_deviation": -0.08,
  "sensor_reliability": 0.98,
  "wx_code": "WX-RA",
  "ill_code": "ILL-DAY"
}
```

**Field definitions**:

| Field | Computation |
|-------|-------------|
| `vehicle_throughput_deviation` | (current 30s count − 15min baseline mean) / baseline mean |
| `flow_continuity_score` | vehicles exiting zone in last 10min / vehicles entering in last 10min |
| `cctv_motion_mean` | Mean motion_index across all zone cameras in last 30s |
| `cctv_motion_rate_of_change` | (current motion mean − previous 30s motion mean) |
| `fastag_rate_deviation` | (current FASTag rate − baseline FASTag rate) / baseline |
| `upstream_vs_downstream_density` | ANPR count at upstream checkpoint / downstream checkpoint (last 5min) |
| `opposing_direction_flow_rate` | Opposite direction throughput / baseline (sanity check) |
| `time_slot_baseline_deviation` | Composite deviation from this time slot's historical average |
| `sensor_reliability` | Average of `sensor_reliability` from all checkpoints in zone (simulated, always >0.95) |
| `wx_code` | Simulated weather code (hourly basis): `WX-CLR` (Clear), `WX-RA` (Rain), `WX-FG` (Fog) |
| `ill_code` | Simulated illumination code (hourly basis): `ILL-DAY`, `ILL-NIGHT-LIT`, `ILL-NIGHT-UNLIT` |

**Weather and Illumination Simulation**:
- Weather codes change on hourly basis during simulation
- Illumination codes follow simulated time of day (day/night transitions)
- Codes are generated by simulator and included in zone state computation
- Historical seed data includes realistic weather patterns (75% clear, 20% rain, 5% fog)

### Baseline Computation

- Per zone, per 15-minute time slot (96 slots/day), per day type (weekday/weekend/holiday)
- Rolling 30-day window
- Stored in Redis: `zone_baseline:{zone_id}:{HH:MM}:{day_type}` (TTL 7 days)
- Backed by PostgreSQL `zone_baselines` table (permanent)
- Recomputed nightly by Risk Zone Scorer batch job

---

## Checkpoint Configuration

Static configuration loaded from `simulator/data/checkpoints.json` and seeded into PostgreSQL `checkpoints` table.

| CP ID | Location | KM | Type | Camera IDs | Direction Coverage |
|-------|----------|-----|------|------------|-------------------|
| CP-01 | Mysore Entry | 0 | full_plaza | CAM-001, CAM-002, CAM-003 | Both |
| CP-02 | Srirangapatna | 15 | monitor | CAM-007, CAM-008 | Both |
| CP-03 | Nidaghatta Toll | 28 | full_plaza | CAM-013, CAM-014, CAM-015 | Both |
| CP-04 | Cauvery Zone Entry | 40 | wildlife_sensor | CAM-019, CAM-020 | Both |
| CP-05 | Cauvery Zone Exit | 55 | wildlife_sensor | CAM-026, CAM-027 | Both |
| CP-06 | Maddur Toll | 58 | full_plaza | CAM-028, CAM-029, CAM-030 | Both |
| CP-07 | Mandya Forest Entry | 62 | wildlife_sensor | CAM-031 | Both |
| CP-08 | Mandya Forest Exit | 71 | wildlife_sensor | CAM-035 | Both |
| CP-09 | Ramanagara | 82 | monitor | CAM-040, CAM-041 | Both |
| CP-10 | Bidadi Toll | 95 | full_plaza | CAM-047, CAM-048, CAM-049 | Both |
| CP-11 | Kengeri Toll | 114 | full_plaza | CAM-056, CAM-057, CAM-058 | Both |
| CP-12 | Bangalore Entry | 120 | monitor | CAM-059, CAM-060 | Both |

**Checkpoint types and capabilities**:

| Type | ANPR | FASTag | CCTV | Toll Collection |
|------|------|--------|------|-----------------|
| full_plaza | ✓ | ✓ | ✓ | CP-03, CP-06, CP-10, CP-11 only |
| monitor | ✓ | ✗ | ✓ | ✗ |
| wildlife_sensor | ✗ | ✗ | ✓ | ✗ |

**Note on CP-01 and CP-12**: These are classified as `full_plaza` (have ANPR + FASTag readers + CCTV) but do NOT collect toll. They serve as entry/exit registration points. FASTag is read for vehicle identification only — no `amount_charged`. This matches real expressway operation where toll is collected at intermediate plazas.

**Toll-collecting plazas**: CP-03 (Nidaghatta), CP-06 (Maddur), CP-10 (Bidadi), CP-11 (Kengeri). Total toll for full route Car: 4 × ₹80 = ₹320.

**Evasion hotspots**: CP-03 (Nidaghatta) and CP-06 (Maddur) — simulator injects higher evasion frequency at these plazas due to parallel state road bypass routes.
