# API Contracts

**Base URL**: `http://localhost:8000/api/v1`  
**Auth**: JWT Bearer token in `Authorization: Bearer <token>` header  
**Content-Type**: `application/json`

---

## Authentication

### POST `/auth/login`

No auth required.

**Request**:
```json
{
  "username": "authority",
  "password": "raah2024"
}
```

**Response** `200`:
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "role": "AUTHORITY",
  "expires_in": 86400
}
```

**Hardcoded credentials**:

| Username | Password | Role |
|----------|----------|------|
| `authority` | `raah2024` | AUTHORITY |
| `commuter` | `raah2024` | COMMUTER |

**Error** `401`:
```json
{ "error": "invalid_credentials", "message": "Invalid username or password" }
```

---

## Authority Endpoints (role: AUTHORITY)

### GET `/dashboard/stats`

Current system overview stats.

**Response** `200`:
```json
{
  "active_vehicles": 342,
  "active_journeys": 342,
  "evasion_cases_today": 12,
  "confirmed_evasions_today": 8,
  "active_incidents": 1,
  "wildlife_alerts_today": 2,
  "total_revenue_today": 245680.0,
  "estimated_evasion_loss_today": 3920.0,
  "zones": [
    {
      "zone_id": "ZONE-06",
      "status": "incident",
      "risk_tier": "High",
      "active_alert_count": 1
    }
  ]
}
```

### GET `/alerts`

Paginated alert feed. Supports filtering.

**Query params**:

| Param | Type | Default | Options |
|-------|------|---------|---------|
| `type` | string | `all` | `all, legal, ml_evasion, incident, wildlife` |
| `status` | string | `all` | `all, pending_review, confirmed, dismissed` |
| `zone_id` | string | null | `ZONE-01` to `ZONE-11` |
| `page` | int | 1 | |
| `per_page` | int | 20 | max 100 |
| `sort` | string | `newest` | `newest, oldest, severity` |

**Response** `200`:
```json
{
  "alerts": [
    {
      "alert_id": "uuid",
      "type": "ml_evasion",
      "source_layer": "ml",
      "severity": "high",
      "plate": "KA09AB1234",
      "zone_id": "ZONE-05",
      "summary": "Probable plaza skip evasion — 91% confidence",
      "evasion_probability": 0.91,
      "missed_amount": 320.0,
      "applicable_penalty": 640.0,
      "status": "pending_review",
      "created_at": "2024-01-15T10:00:00Z",
      "evidence_bundle_id": "uuid"
    }
  ],
  "total": 45,
  "page": 1,
  "per_page": 20
}
```

### GET `/alerts/{alert_id}`

Full alert detail with evidence bundle.

**Response** `200`:
```json
{
  "alert_id": "uuid",
  "type": "ml_evasion",
  "source_layer": "ml",
  "plate": "KA09AB1234",
  "journey_id": "uuid",
  "evidence_bundle": {
    "anpr_events": [
      {"checkpoint_id": "CP-01", "timestamp": "2024-01-15T09:00:00Z", "confidence": 0.96}
    ],
    "fastag_events": [
      {"plaza_id": "CP-01", "timestamp": "2024-01-15T09:00:22Z", "amount": 80.0}
    ],
    "expected_sequence": ["CP-01","CP-03","CP-06","CP-10","CP-11","CP-12"],
    "actual_sequence": ["CP-01","CP-12"],
    "timing_proof": {
      "total_time_seconds": 2400,
      "minimum_possible_seconds": 3600,
      "conclusion": "Journey completed 33% faster than physically possible"
    },
    "evasion_score": 0.91,
    "top_features": [
      {"feature": "checkpoint_completeness", "value": 0.17, "contribution": 0.42}
    ],
    "estimated_revenue_loss": 320.0,
    "revenue_calculation": "Car × ₹80 × 4 missed toll plazas (CP-03, CP-06, CP-10, CP-11)"
  },
  "status": "pending_review",
  "created_at": "2024-01-15T10:00:00Z"
}
```

### POST `/alerts/{alert_id}/feedback`

Submit officer feedback on an ML alert.

**Request**:
```json
{
  "action": "confirm",
  "reason": null,
  "notes": "Clear plaza skip pattern"
}
```

**Valid actions**: `confirm, dismiss_sensor_error, dismiss_legitimate_exception, dismiss_insufficient_evidence`

**Response** `200`:
```json
{
  "feedback_id": "uuid",
  "alert_id": "uuid",
  "action": "confirm",
  "processed": true,
  "effects": {
    "training_label_added": true,
    "sensor_reliability_updated": false,
    "model_retrain_queued": false
  }
}
```

### GET `/evasion/cases`

Evasion case list (both hard logic and ML).

**Query params**: `status` (`all, pending, confirmed, dismissed`), `date_from`, `date_to`, `page`, `per_page`

**Response** `200`:
```json
{
  "cases": [
    {
      "case_id": "uuid",
      "type": "legal_e1",
      "source_layer": "hard_logic",
      "plate": "KA09AB1234",
      "violation_rule": "E1",
      "legal_reference": "NH Fee Rules 2008, Section 14",
      "checkpoint_id": "CP-06",
      "timestamp": "2024-01-15T09:45:00Z",
      "status": "pending_review",
      "missed_amount": 80.0,
      "applicable_penalty": 160.0
    }
  ],
  "total": 23,
  "page": 1
}
```

### GET `/journeys/active`

All currently active journeys on highway.

**Query params**: `direction` (`all, MB, BM`), `zone_id`, `page`, `per_page`

**Response** `200`:
```json
{
  "journeys": [
    {
      "plate": "KA09AB1234",
      "direction": "MB",
      "vehicle_class": "Car",
      "entry_checkpoint": "CP-01",
      "entry_time": "2024-01-15T09:00:00Z",
      "last_checkpoint": "CP-06",
      "last_seen": "2024-01-15T09:45:00Z",
      "estimated_position_km": 62.5,
      "status": "active",
      "flags": []
    }
  ],
  "total_active": 342
}
```

### GET `/journeys/{plate}/{direction}`

Single journey detail.

**Response** `200`: Full journey object (see DATA_PIPELINE.md journey object structure).

### GET `/zones`

All zone states for a given highway.

**Query params**:
- `highway_id` (string, default: `NH-275`)

**Response** `200`:
```json
{
  "zones": [
    {
      "zone_id": "ZONE-06",
      "name": "Maddur–Mandya Forest Entry",
      "km_range": "58–62",
      "type": "highway",
      "status": "incident",
      "risk_tier": "High",
      "anomaly_score": -0.82,
      "incident_type": "partial_blockage",
      "vehicle_count": 45,
      "flow_continuity": 0.42,
      "motion_index_mean": 0.15,
      "camera_ids": ["CAM-028", "CAM-029", "CAM-030"],
      "active_alerts": 1,
      "updated_at": "2024-01-15T09:30:30Z"
    }
  ]
}
```

### GET `/zones/{zone_id}/risk-profile`

Zone risk profile from nightly scorer.

**Response** `200`:
```json
{
  "zone_id": "ZONE-06",
  "risk_tier": "High",
  "dominant_risk_type": "evasion_concentration",
  "risk_score": 0.78,
  "peak_risk_hours": [7, 8, 9, 17, 18, 19],
  "time_risk_curve": [0.2, 0.15, 0.1, 0.08, 0.05, 0.05, 0.1, 0.6, 0.75, 0.8, 0.5, 0.4, 0.35, 0.3, 0.3, 0.35, 0.4, 0.7, 0.75, 0.65, 0.5, 0.4, 0.3, 0.25],
  "computed_at": "2024-01-15T02:00:00Z"
}
```

### GET `/analytics/model-metrics`

Model performance metrics.

**Response** `200`:
```json
{
  "models": [
    {
      "model_name": "evasion_scorer",
      "current_version": "evasion_v3_2024-01-15",
      "accuracy_7d": [0.82, 0.83, 0.84, 0.85, 0.86, 0.87, 0.88],
      "false_positive_rate_7d": [0.12, 0.11, 0.10, 0.09, 0.09, 0.08, 0.07],
      "confirmed_rate_7d": [0.78, 0.80, 0.82, 0.83, 0.85, 0.86, 0.88],
      "total_predictions": 1250,
      "total_confirmed": 1025,
      "total_dismissed": 225
    }
  ]
}
```

### GET `/checkpoints`

All checkpoint configurations.

**Query params**:
- `highway_id` (string, default: `NH-275`)

**Response** `200`: Array of checkpoint objects per DATA_PIPELINE.md checkpoint table.

---

## Commuter Endpoints (role: COMMUTER)

### POST `/commuter/route-query`

Query route for journey estimation.

**Request**:
```json
{
  "origin_checkpoint": "CP-01",
  "destination_checkpoint": "CP-12",
  "vehicle_class": "Car",
  "departure_time": "2024-01-15T21:00:00Z"
}
```

**Response** `200`:
```json
{
  "route": {
    "origin": "CP-01 (Mysore Entry)",
    "destination": "CP-12 (Bangalore Entry)",
    "distance_km": 120,
    "vehicle_class": "Car"
  },
  "journey_estimate": {
    "estimated_minutes": 115,
    "confidence_range_minutes": [100, 135],
    "based_on": "Median of 342 similar journeys in last 7 days"
  },
  "toll_breakdown": {
    "plazas": [
      {"checkpoint": "CP-03", "name": "Nidaghatta Toll", "amount": 80},
      {"checkpoint": "CP-06", "name": "Maddur Toll", "amount": 80},
      {"checkpoint": "CP-10", "name": "Bidadi Toll", "amount": 80},
      {"checkpoint": "CP-11", "name": "Kengeri Toll", "amount": 80}
    ],
    "total": 320
  },
  "risk_warnings": [
    {
      "zone_id": "ZONE-06",
      "zone_name": "Maddur–Mandya Forest Entry",
      "warning": "Active incident — partial blockage detected",
      "severity": "high",
      "anomaly_score": 0.84
    },
    {
      "zone_id": "ZONE-04",
      "zone_name": "Cauvery Wildlife Corridor",
      "warning": "Wildlife advisory — recent wildlife activity detected",
      "severity": "medium"
    }
  ],
  "departure_recommendation": {
    "recommended": true,
    "message": "Zone 6 incident typically clears within 60 minutes. Consider departing after 10:30 PM for smoother journey.",
    "alternative_departure": "2024-01-15T22:30:00Z"
  }
}
```

### POST `/commuter/track-journey`

Register a vehicle for active journey tracking.

**Request**:
```json
{
  "plate_number": "KA09AB1234",
  "direction": "MB"
}
```

**Response** `200`:
```json
{
  "tracking_id": "uuid",
  "plate": "KA09AB1234",
  "status": "waiting_for_entry",
  "message": "You will receive real-time updates via WebSocket once your vehicle is detected"
}
```

### GET `/commuter/journey/{plate}/{direction}`

Get current journey status for tracked vehicle.

**Response** `200`:
```json
{
  "plate": "KA09AB1234",
  "direction": "MB",
  "status": "active",
  "entry_checkpoint": "CP-01",
  "entry_time": "2024-01-15T21:00:00Z",
  "last_checkpoint": "CP-06",
  "last_seen": "2024-01-15T21:45:00Z",
  "estimated_position_km": 62.5,
  "remaining_km": 57.5,
  "estimated_arrival_minutes": 35,
  "ahead_warnings": [
    {
      "zone_id": "ZONE-07",
      "warning": "Wildlife advisory — Mandya Forest Corridor",
      "severity": "medium"
    }
  ]
}
```

---

## Simulator / Demo Endpoints (role: AUTHORITY)

### POST `/simulator/scenario`

Inject a demo scenario.

**Request**:
```json
{
  "scenario": "incident",
  "params": {
    "zone_id": "ZONE-06",
    "duration_minutes": 10
  }
}
```

**Available scenarios**:

| Scenario | Required Params | Description |
|----------|----------------|-------------|
| `incident` | `zone_id`, `duration_minutes` | Drops flow + motion in zone |
| `evasion` | none (auto-generated) | Vehicle at CP-01 and CP-12 only, impossible timing |
| `wildlife` | `zone_id` (must be ZONE-04 or ZONE-07) | Motion pulse during vehicle gap in forest zone |
| `ghost_vehicle` | none | ANPR reads for plate absent from vehicle DB |
| `high_risk_hour` | `duration_minutes` | Increases incident + evasion frequency |

**Response** `200`:
```json
{
  "scenario_id": "uuid",
  "scenario": "incident",
  "status": "active",
  "started_at": "2024-01-15T10:00:00Z",
  "expected_end": "2024-01-15T10:10:00Z",
  "affected_zone": "ZONE-06"
}
```

### GET `/simulator/status`

Current simulator state.

**Response** `200`:
```json
{
  "running": true,
  "time_scale": 60,
  "simulated_time": "2024-01-15T14:00:00Z",
  "real_uptime_seconds": 840,
  "events_generated": {
    "anpr": 15234,
    "fastag": 8120,
    "cctv": 45600
  },
  "active_scenarios": [
    {"scenario_id": "uuid", "type": "incident", "zone_id": "ZONE-06"}
  ]
}
```

### POST `/simulator/config`

Update simulator configuration.

**Request**:
```json
{
  "time_scale": 60,
  "peak_vehicles_per_hour": 1500,
  "evasion_base_rate": 0.05
}
```

### POST `/simulator/reset`

Reset simulator state. Clears active scenarios, resets event counters.

### POST `/risk-scorer/run`

Trigger on-demand risk zone scoring (normally nightly).

**Response** `200`:
```json
{
  "status": "completed",
  "zones_scored": 11,
  "computation_time_seconds": 2.3,
  "profiles_updated": true
}
```

---

## Socket.IO Events

**Server**: `http://localhost:8000` (same as REST API)

### Namespace: `/authority`

**Auth**: Connect with `{ auth: { token: "Bearer <jwt>" } }`

**Server → Client events**:

| Event | Payload | Trigger |
|-------|---------|---------|
| `legal_alert` | `{ alert_id, type, plate, rule, checkpoint, severity, summary, timestamp }` | Hard Logic fires violation |
| `ml_alert` | `{ alert_id, type, plate, zone_id, probability, summary, severity, timestamp }` | ML Scorer flags candidate |
| `zone_update` | `{ zone_id, status, anomaly_score, incident_type, motion_mean, flow_continuity }` | Zone state changes significantly |
| `journey_update` | `{ plate, direction, last_checkpoint, estimated_km, status, flags }` | Vehicle detected at new checkpoint |
| `wildlife_alert` | `{ alert_id, zone_id, confidence, signals, suggested_actions, timestamp }` | Wildlife detected |
| `model_metrics` | `{ model_name, accuracy, fpr, confirmed_rate }` | After feedback processed |
| `scenario_started` | `{ scenario_id, type, zone_id, duration }` | Demo scenario activated |
| `scenario_ended` | `{ scenario_id, type }` | Demo scenario completed |

**Client → Server events**:

| Event | Payload | Purpose |
|-------|---------|---------|
| `feedback_submit` | `{ alert_id, action, reason, notes }` | Officer submits feedback (also available via REST) |
| `subscribe_zone` | `{ zone_id }` | Get frequent updates for specific zone |

### Namespace: `/commuter`

**Auth**: Connect with `{ auth: { token: "Bearer <jwt>" } }`

**Server → Client events**:

| Event | Payload | Trigger |
|-------|---------|---------|
| `journey_progress` | `{ plate, last_checkpoint, estimated_km, remaining_km, eta_minutes }` | Tracked vehicle moves |
| `route_alert` | `{ zone_id, warning, severity, message }` | Incident/wildlife on tracked route |
| `zone_warning` | `{ zone_id, zone_name, status, advisory }` | Zone status change affecting commuter |

**Client → Server events**:

| Event | Payload | Purpose |
|-------|---------|---------|
| `track_journey` | `{ plate, direction }` | Start tracking (joins room `commuter:{plate}`) |
| `stop_tracking` | `{ plate }` | Stop tracking (leaves room) |

---

## Error Codes

| HTTP Code | Error Key | Description |
|-----------|-----------|-------------|
| 400 | `invalid_request` | Malformed request body or missing required fields |
| 401 | `invalid_credentials` | Bad username/password |
| 401 | `token_expired` | JWT expired |
| 403 | `insufficient_role` | Role doesn't have access to endpoint |
| 404 | `not_found` | Resource not found |
| 409 | `feedback_exists` | Feedback already submitted for this alert |
| 422 | `invalid_scenario` | Invalid scenario type or params |
| 500 | `internal_error` | Server error |

**Standard error response**:
```json
{
  "error": "error_key",
  "message": "Human readable description",
  "details": {}
}
```
