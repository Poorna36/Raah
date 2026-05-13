# Database Schema

## PostgreSQL Tables

### `vehicles`

Government vehicle database. Seeded with 50,000 records at startup.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `plate_number` | VARCHAR(15) | PK | e.g. `KA09AB1234` |
| `registered_class` | VARCHAR(10) | NOT NULL | Enum: `2W, LMV, Car, Bus, Truck, MAV` |
| `registration_state` | VARCHAR(5) | NOT NULL | e.g. `KA`, `TN`, `MH` |
| `registration_status` | VARCHAR(15) | NOT NULL, DEFAULT 'active' | Enum: `active, expired, suspended` |
| `owner_type` | VARCHAR(15) | NOT NULL | Enum: `private, commercial, government` |
| `registration_date` | DATE | NOT NULL | |
| `fitness_expiry` | DATE | NOT NULL | |
| `insurance_expiry` | DATE | NOT NULL | |
| `fuel_type` | VARCHAR(10) | NOT NULL | `PETROL, DIESEL, EV, CNG` |
| `puc_upto` | DATE | NOT NULL | Pollution certificate validity |
| `permit_status` | VARCHAR(20) | NOT NULL, DEFAULT 'valid' | Enum: `valid, expired, not_required` (MV Act Section 66) |
| `permit_expiry` | DATE | | NULL if not_required |
| `maker_model` | VARCHAR(50) | NOT NULL | e.g. `TATA LPT 3118`, `MARUTI SWIFT` |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Indexes**: `registration_status`, `registered_class`
**Seed distribution**: 97% active, 2% expired, 1% suspended

---

### `vehicle_exemptions`

Exemption whitelist for NH Fee Rules 2008 Rule 14. Vehicles on this list bypass evasion detection.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `exemption_id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `plate_number` | VARCHAR(15) | NOT NULL, FK → vehicles, UNIQUE | |
| `exemption_type` | VARCHAR(30) | NOT NULL | Enum: `emergency, government, diplomatic, military, permit_exempt` |
| `authority_issued` | VARCHAR(50) | NOT NULL | Issuing authority |
| `valid_from` | DATE | NOT NULL | |
| `valid_until` | DATE | NOT NULL | |
| `reference_number` | VARCHAR(50) | NOT NULL | Official reference |
| `is_active` | BOOLEAN | DEFAULT true | |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Indexes**: `(plate_number)`, `(exemption_type)`, `(is_active)` partial where true
**Seed distribution**: ~2% of vehicles (1,000 of 50,000) are exempt

---

### `checkpoints`

Static highway checkpoint configuration.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `checkpoint_id` | VARCHAR(10) | PK | `CP-01` to `CP-12` |
| `highway_id` | VARCHAR(20) | NOT NULL, DEFAULT 'NH-275' | Multi-highway support |
| `name` | VARCHAR(50) | NOT NULL | e.g. `Mysore Entry` |
| `km_marker` | FLOAT | NOT NULL | 0–120 |
| `type` | VARCHAR(20) | NOT NULL | Enum: `full_plaza, monitor, wildlife_sensor` |
| `camera_ids` | VARCHAR[] | NOT NULL | Array of camera IDs |
| `direction_coverage` | VARCHAR(10) | DEFAULT 'both' | `both, MB, BM` |
| `zone_id` | VARCHAR(10) | FK → zones | |
| `sensor_reliability` | FLOAT | NOT NULL, DEFAULT 0.98 | Simulated reliability score (0–1), always >0.95 |

---

### `zones`

Zone definitions.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `zone_id` | VARCHAR(10) | PK | `ZONE-01` to `ZONE-11` |
| `highway_id` | VARCHAR(20) | NOT NULL, DEFAULT 'NH-275' | Multi-highway support |
| `name` | VARCHAR(50) | NOT NULL | |
| `km_start` | FLOAT | NOT NULL | |
| `km_end` | FLOAT | NOT NULL | |
| `type` | VARCHAR(20) | NOT NULL | `highway, forest_corridor` |
| `zone_class` | VARCHAR(20) | NOT NULL | `ZN-URB` (Urban), `ZN-RUR` (Rural), `ZN-FOR` (Forest) |
| `access_type` | VARCHAR(20) | NOT NULL | `ACC-CTRL` (Controlled), `ACC-OPEN` (Service roads) |
| `entry_checkpoint` | VARCHAR(10) | FK → checkpoints | |
| `exit_checkpoint` | VARCHAR(10) | FK → checkpoints | |

---

### `checkpoint_events`

All ANPR events. High-volume — partitioned by date.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `event_id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `checkpoint_id` | VARCHAR(10) | NOT NULL, FK → checkpoints | |
| `camera_id` | VARCHAR(10) | NOT NULL | |
| `plate_number` | VARCHAR(15) | NOT NULL | |
| `timestamp` | TIMESTAMPTZ | NOT NULL | |
| `confidence_score` | FLOAT | NOT NULL | 0–1 |
| `vehicle_class_detected` | VARCHAR(10) | NOT NULL | |
| `lane_id` | VARCHAR(5) | | |
| `image_ref` | VARCHAR(100) | | Mock path |
| `direction` | VARCHAR(5) | NOT NULL | `MB` or `BM` |
| `raw_read` | VARCHAR(20) | | Original OCR output |
| `vehicle_db_match` | BOOLEAN | DEFAULT true | |
| `registered_class` | VARCHAR(10) | | From enrichment |
| `registration_status` | VARCHAR(15) | | From enrichment |
| `ingested_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Indexes**: `(plate_number, timestamp)`, `(checkpoint_id, timestamp)`, `(timestamp)` — for range queries  
**Partition**: By month on `timestamp`

---

### `fastag_events`

All FASTag transactions.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `transaction_id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `tag_id` | VARCHAR(30) | NOT NULL | |
| `vehicle_plate` | VARCHAR(15) | NOT NULL | |
| `plaza_id` | VARCHAR(10) | NOT NULL, FK → checkpoints | Full plaza only |
| `timestamp` | TIMESTAMPTZ | NOT NULL | |
| `amount_charged` | DECIMAL(10,2) | NOT NULL | |
| `vehicle_class_tagged` | VARCHAR(10) | NOT NULL | |
| `transaction_status` | VARCHAR(15) | NOT NULL | `success, failed, blacklisted, low_balance` |
| `bank_id` | VARCHAR(20) | | |
| `ingested_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Indexes**: `(vehicle_plate, timestamp)`, `(plaza_id, timestamp)`, `(timestamp)`

---

### `cctv_events`

CCTV motion index readings. Highest volume table.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `event_id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `camera_id` | VARCHAR(10) | NOT NULL | |
| `checkpoint_id` | VARCHAR(10) | NOT NULL | |
| `segment_id` | VARCHAR(20) | | e.g. `SEG-KM40-KM42` |
| `timestamp` | TIMESTAMPTZ | NOT NULL | |
| `motion_index` | FLOAT | NOT NULL | 0–1 |
| `zone_type` | VARCHAR(20) | NOT NULL | |
| `frame_window_seconds` | INT | DEFAULT 5 | |
| `ingested_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Indexes**: `(camera_id, timestamp)`, `(checkpoint_id, timestamp)`, `(timestamp)`  
**Partition**: By month on `timestamp`  
**Retention**: Aggregate to hourly summaries after 7 days, delete raw after 30 days

---

### `journeys`

Journey records — active and completed.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `journey_id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `highway_id` | VARCHAR(20) | NOT NULL, DEFAULT 'NH-275' | |
| `plate` | VARCHAR(15) | NOT NULL | |
| `direction` | VARCHAR(5) | NOT NULL | |
| `vehicle_class_anpr` | VARCHAR(10) | | |
| `vehicle_class_registered` | VARCHAR(10) | | |
| `vehicle_class_fastag` | VARCHAR(10) | | |
| `entry_checkpoint` | VARCHAR(10) | FK → checkpoints | |
| `exit_checkpoint` | VARCHAR(10) | FK → checkpoints | NULL if active |
| `entry_time` | TIMESTAMPTZ | NOT NULL | |
| `exit_time` | TIMESTAMPTZ | | NULL if active |
| `last_checkpoint` | VARCHAR(10) | | |
| `last_seen` | TIMESTAMPTZ | | |
| `checkpoints_visited` | JSONB | NOT NULL | Array of {cp, time, type} |
| `expected_checkpoints` | VARCHAR[] | NOT NULL | Ordered array |
| `status` | VARCHAR(15) | DEFAULT 'active' | `active, completed, timeout` |
| `journey_start` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Indexes**: `(plate, direction, journey_start)` UNIQUE, `(status)` partial where active, `(entry_time)`

---

### `legal_events`

Hard logic violation records. **Immutable — no UPDATE/DELETE for app DB user.**

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `legal_event_id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `rule_code` | VARCHAR(5) | NOT NULL | `E1, E2, E3, E4, E5, R1, R2, R3` |
| `rule_description` | VARCHAR(200) | NOT NULL | |
| `legal_reference` | VARCHAR(200) | NOT NULL | Specific act/section citation |
| `plate` | VARCHAR(15) | NOT NULL | |
| `journey_id` | UUID | FK → journeys | |
| `checkpoint_id` | VARCHAR(10) | FK → checkpoints | Where violation detected |
| `violation_type` | VARCHAR(30) | NOT NULL | |
| `evidence_ids` | UUID[] | NOT NULL | Array of event IDs used as evidence |
| `confidence` | FLOAT | DEFAULT 1.0 | Always 1.0 for hard logic |
| `missed_amount` | DECIMAL(10,2) | | Base toll amount missed |
| `applicable_penalty` | DECIMAL(10,2) | | Penalty amount (2× missed_amount, applied if confirmed) |
| `status` | VARCHAR(20) | DEFAULT 'pending_review' | `pending_review, reviewed` |
| `officer_notes` | TEXT | | Added during review |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Indexes**: `(plate)`, `(rule_code)`, `(created_at)`, `(status)`  
**Permissions**: App user has INSERT and SELECT only. No UPDATE/DELETE.

---

### `ml_alerts`

ML-generated candidate alerts.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `alert_id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `alert_type` | VARCHAR(20) | NOT NULL | `evasion, incident, wildlife` |
| `model_name` | VARCHAR(30) | NOT NULL | |
| `model_version` | VARCHAR(50) | NOT NULL | |
| `plate` | VARCHAR(15) | | NULL for non-vehicle alerts |
| `journey_id` | UUID | FK → journeys | NULL for zone alerts |
| `zone_id` | VARCHAR(10) | FK → zones | |
| `probability` | FLOAT | NOT NULL | 0–1 |
| `top_features` | JSONB | | Feature importance breakdown |
| `incident_type` | VARCHAR(30) | | For zone anomaly alerts |
| `evidence_bundle` | JSONB | | Full evidence if evasion |
| `suggested_action` | TEXT | | |
| `severity` | VARCHAR(10) | NOT NULL | `low, medium, high, critical` |
| `officer_action` | VARCHAR(30) | DEFAULT 'pending_review' | `pending_review, confirmed, dismissed` |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Indexes**: `(alert_type, created_at)`, `(officer_action)`, `(zone_id)`, `(plate)`

---

### `alert_feedback`

Officer feedback on ML alerts.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `feedback_id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `alert_id` | UUID | NOT NULL, FK → ml_alerts, UNIQUE | One feedback per alert |
| `action` | VARCHAR(30) | NOT NULL | `confirm, dismiss_sensor_error, dismiss_legitimate_exception, dismiss_insufficient_evidence` |
| `reason` | TEXT | | Free-text reason for dismissal |
| `officer_id` | VARCHAR(30) | NOT NULL | Username of officer |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |
| `training_label` | INT | | 1=positive, 0=negative, NULL=excluded |
| `processed` | BOOLEAN | DEFAULT false | Has been consumed by training pipeline |

**Indexes**: `(alert_id)` UNIQUE, `(processed)` partial where false, `(created_at)`

---

### `zone_risk_profiles`

Nightly risk scoring output.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `profile_id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `zone_id` | VARCHAR(10) | NOT NULL, FK → zones | |
| `risk_tier` | VARCHAR(10) | NOT NULL | `Low, Moderate, High, Critical` |
| `risk_score` | FLOAT | NOT NULL | 0–1 |
| `dominant_risk_type` | VARCHAR(30) | NOT NULL | `incident_history, evasion_concentration, wildlife, combination` |
| `peak_risk_hours` | INT[] | | Array of hour indices |
| `time_risk_curve` | FLOAT[] | | 24 floats, one per hour |
| `corridor_risk_elevated` | BOOLEAN | DEFAULT false | True if 3+ wildlife events in 30d |
| `computed_at` | TIMESTAMPTZ | NOT NULL | |
| `model_version` | VARCHAR(50) | | |

**Indexes**: `(zone_id, computed_at)` — latest profile per zone  
**Constraint**: Keep latest 30 profiles per zone, prune older.

---

### `historical_incidents`

Pre-seeded 18-month incident history.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `incident_id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `segment_id` | VARCHAR(20) | NOT NULL | |
| `km_marker` | FLOAT | NOT NULL | |
| `incident_type` | VARCHAR(20) | NOT NULL | `accident, breakdown, obstruction, wildlife, weather` |
| `severity` | VARCHAR(10) | NOT NULL | `minor, major, fatal` |
| `timestamp` | TIMESTAMPTZ | NOT NULL | |
| `vehicles_involved` | INT | DEFAULT 1 | |
| `response_time_minutes` | INT | | |
| `resolution_time_minutes` | INT | | |

**Indexes**: `(segment_id, timestamp)`, `(incident_type)`, `(timestamp)`

---

### `model_metrics`

Model performance tracking per training cycle.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `metric_id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `model_name` | VARCHAR(30) | NOT NULL | |
| `model_version` | VARCHAR(50) | NOT NULL | |
| `accuracy` | FLOAT | | |
| `precision_score` | FLOAT | | |
| `recall` | FLOAT | | |
| `f1` | FLOAT | | |
| `false_positive_rate` | FLOAT | | |
| `confirmed_rate` | FLOAT | | Confirmed / total predictions |
| `auc_roc` | FLOAT | | |
| `silhouette_score` | FLOAT | | For clustering models |
| `training_samples` | INT | | |
| `computed_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Indexes**: `(model_name, computed_at)`

---

### `zone_baselines`

Rolling baseline statistics per zone per time slot.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `baseline_id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `zone_id` | VARCHAR(10) | NOT NULL, FK → zones | |
| `time_slot` | VARCHAR(5) | NOT NULL | `HH:MM` format, 15-min slots (96/day) |
| `day_type` | VARCHAR(10) | NOT NULL | `weekday, weekend, holiday` |
| `throughput_mean` | FLOAT | | |
| `throughput_std` | FLOAT | | |
| `flow_continuity_mean` | FLOAT | | |
| `motion_mean` | FLOAT | | |
| `motion_std` | FLOAT | | |
| `fastag_rate_mean` | FLOAT | | |
| `sample_count` | INT | | Days of data in this average |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Indexes**: `(zone_id, time_slot, day_type)` UNIQUE

---

## Redis Key Structures

| Key Pattern | Value Format | TTL | Read By | Written By |
|-------------|-------------|-----|---------|------------|
| `journey:{plate}:{direction}` | JSON (journey object) | 24h | Hard Logic, ML Service, API | Journey Engine |
| `zone_state:{zone_id}` | JSON (zone state vector) | 60s | ML Service | Zone Aggregator |
| `zone_baseline:{zone_id}:{HH:MM}:{day_type}` | JSON (baseline stats) | 7d | Zone Aggregator | Risk Scorer |
| `sensor_reliability:{checkpoint_id}` | Float string `"0.95"` | None | ML Service, API | Feedback Processor |
| `active_alerts:{zone_id}` | JSON array of alert summaries | 1h | API, Commuter routes | Alert Engine |
| `wildlife_thresholds:{zone_id}` | JSON `{"motion_min":0.08,"motion_max":0.25,"speed_reduction":0.15}` | None | Wildlife Detector | Training pipeline |

---

## Seed Data

### Phase 1: Historical "Pre-computation" Seed (`scripts/seed_db.py --historical-days 30`)

Execution order (Run once at setup):
1. Create all tables (run migrations)
2. Seed `zones` (11 records, including `zone_class` and `access_type`)
3. Seed `checkpoints` (12 records) from `simulator/data/checkpoints.json`
4. Seed `vehicles` (50,000 records) from `simulator/data/vehicles_seed.json`
5. Generate 30 days of raw `checkpoint_events` and `fastag_events` using contextual probabilities (e.g. `WX-RA` impacts flow).
6. Build `journeys` from raw events.
7. Inject historical incidents (18 months of major, 30 days of minor).
8. Simulate ML processing: generate `ml_alerts`, `alert_feedback`, and nightly `zone_risk_profiles` for the 30-day period.
9. Result: Database is completely populated. Dashboard loads instantly via API without waiting for runtime simulation.

### Vehicle Seed Generation Rules (VAHAN Compliant)

- Plate format: `{state}{district}{series}{number}` — e.g. `KA09AB1234`
- 70% Karnataka (`KA`), 15% Tamil Nadu (`TN`), 10% Andhra Pradesh (`AP`), 5% other
- Class distribution: 50% Car, 20% LMV, 10% Bus, 10% Truck, 5% MAV, 5% 2W
- `fuel_type`: 60% Petrol, 30% Diesel, 5% EV, 5% CNG (Heavily weighted to Diesel for Truck/MAV/Bus)
- `maker_model`: Mapped to class (e.g. Swift/Dzire for Car, Tata Signa for MAV)
- `registration_status`: 97% active, 2% expired, 1% suspended
- Fitness/Insurance/`puc_upto`: 80% valid, 15% expiring within 60 days, 5% expired (Expired PUC correlates with higher ML evasion probability)

### Historical Incident Generation Rules

- 18 months of data ending at seed time
- Calibrated to MoRTH NH-275 accident frequency (~0.5 incidents/day average)
- Higher density at KM 58 (Maddur), KM 82 (Ramanagara), KM 95 (Bidadi)
- Type distribution: 40% accident, 25% breakdown, 15% obstruction, 10% wildlife, 10% weather
- Severity: 60% minor, 30% major, 10% fatal
- Response time: 10–45 min (mean 22 min)
- Resolution time: 30–240 min depending on severity
