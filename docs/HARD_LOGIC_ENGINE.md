# Hard Logic Engine

## Principle

This layer handles everything legally defined and mathematically deterministic. **AI never touches this layer.** No ML model, no training cycle, no feedback loop, no officer action ever modifies these rules. Violations produced here are **facts with legal basis**, not predictions. Output is always a **legal event record** with confidence 1.0.

**File**: `backend/hard_logic/engine.py` (rule executor), `backend/hard_logic/rules.py` (rule definitions)

---

## Rule Execution Order

Engine receives a journey state update from `stream:journey_updates`. Runs rules in this fixed order:

```
Journey Update Received
    → EX: Exemption whitelist check (skip E1–E3 if exempt)
    → R1: Validate checkpoint sequence
    → R2: Check inter-checkpoint timing
    → R3: Check journey timeout
    → E4: Check vehicle DB match
    → E1: Check FASTag presence at Full Plazas
    → E2: Check FASTag amount vs minimum
    → E3: Check vehicle class match
    → E5: Check impossible journey timing
```

**Why this order**: Route validation rules (R-series) run first because they can flag the entire journey as invalid (cloned plate, ghost vehicle), which changes how evasion rules (E-series) interpret the data. E4 runs before E1–E3 because unregistered vehicles need a different enforcement path.

Each rule runs independently. A single journey update can fire multiple rules. Each fired rule produces one `legal_event` record.

---

## Evasion Rules

### Rule E1: Non-Payment

**Legal basis**: National Highways Fee (Determination of Rates and Collection) Rules, 2008, **Rule 5** — "Every vehicle using a national highway is obligated to pay the prescribed fee at the designated toll plaza."

**Penalty basis**: **Rule 15** — liable to pay twice the applicable fee as penalty.

**Trigger condition**:
```
ANPR event exists at a toll-collecting plaza (CP-03, CP-06, CP-10, CP-11)
AND
No FASTag transaction for same plate at same plaza within 90 seconds of ANPR timestamp
AND
FASTag transaction_status is NOT 'failed' or 'low_balance' (those are handled separately)
```

Note: CP-01 and CP-12 are full plazas with FASTag readers but do NOT collect toll. E1 does not fire at these checkpoints. FASTag reads at CP-01/CP-12 are for vehicle identification only.

**Input**:
- Journey object → `checkpoints_visited` array
- For each Full Plaza checkpoint in visited list: check if both `anpr` and `fastag` type entries exist
- Time window: FASTag timestamp must be within [ANPR timestamp, ANPR timestamp + 90s]

**Output**:
```json
{
  "rule_code": "E1",
  "rule_description": "Non-payment of toll fee at full plaza",
  "legal_reference": "NH Fee Rules 2008, Section 14",
  "violation_type": "toll_non_payment",
  "plate": "KA09AB1234",
  "checkpoint_id": "CP-06",
  "evidence_ids": ["anpr_event_uuid"],
  "confidence": 1.0,
  "missed_amount": 80.0,
  "applicable_penalty": 160.0,
  "status": "pending_review"
}
```

**Penalty calculation (2-stage)**:
- `missed_amount`: Toll rate for `vehicle_class_detected` (base fee not paid)
- `applicable_penalty`: `missed_amount × 2` (penalty per Rule 15, only applied if officer confirms violation)
- If officer dismisses case: no penalty collected, only `missed_amount` is recorded for audit
- If officer confirms: collect `missed_amount + applicable_penalty` = 3× base fee

---

### Rule E2: Underpayment

**Legal basis**: NH Fee Rules 2008, **Rule 7** — "Fees are determined by vehicle class." **Rule 15** — penalty of 2× applicable fee applies.

**Trigger condition**:
```
FASTag transaction exists at Full Plaza
AND
amount_charged < minimum toll rate for vehicle_class_detected (from ANPR)
```

**Rate lookup table** (used for comparison):

| ANPR-detected class | Minimum toll (₹) |
|---------------------|-------------------|
| 2W | 0 (exempt) |
| LMV | 80 |
| Car | 80 |
| LCV | 130 |
| Bus | 270 |
| Truck | 270 |
| MAV | 415 |

**Input**: ANPR event `vehicle_class_detected` + paired FASTag event `amount_charged`

**Output**:
```json
{
  "rule_code": "E2",
  "rule_description": "Toll underpayment — charged amount below minimum for detected vehicle class",
  "legal_reference": "NH Fee Rules 2008, Rule 7 & 15",
  "violation_type": "toll_underpayment",
  "plate": "KA09AB1234",
  "checkpoint_id": "CP-03",
  "evidence_ids": ["anpr_event_uuid", "fastag_event_uuid"],
  "confidence": 1.0,
  "missed_amount": 95.0,
  "applicable_penalty": 190.0
}
```

**Penalty calculation (2-stage)**:
- `missed_amount`: (Correct rate for detected class − amount actually charged)
- `applicable_penalty`: `missed_amount × 2` (per Rule 15, only applied if officer confirms)
- Total if confirmed: `missed_amount + applicable_penalty`

---

### Rule EX: Exemption Whitelist Check

**Legal basis**: NH Fee Rules 2008, **Rule 14** — "Certain vehicle categories are statutorily exempt from fee payment — defense vehicles, vehicles of the President and Governor, emergency vehicles."

**Additional basis**: MV Act 1988, **Section 66** — "No person shall drive a transport vehicle without a valid permit."

**Trigger condition**:
```
Vehicle plate matches exemption whitelist in vehicle_exemptions table
AND
is_active = true
AND
current date between valid_from and valid_until
OR
Vehicle has permit_status = 'not_required' in vehicles table
```

**Exemption categories**:
| Category | Fee Collection | Evasion Detection | Alert Generation |
|----------|---------------|-------------------|------------------|
| emergency | Bypassed | Bypassed | None |
| government | Bypassed | Bypassed | None |
| diplomatic | Bypassed | Bypassed | None |
| military | Bypassed | Bypassed | None |
| permit_exempt | Bypassed | Bypassed | None |

**System Implementation**:
- Exemption whitelist maintained in `vehicle_exemptions` table
- Permit status maintained in `vehicles` table (permit_status field)
- Checked during ingestion enrichment before any evasion rules (E1–E3)
- Exempt vehicles produce no legal events for toll violations
- Still monitored for safety violations (E4, E5) if applicable
- If permit_status = 'expired', vehicle is NOT exempt and E1–E3 rules apply

**Rule execution position**: Run FIRST in the rule sequence, before R1–R3 and E1–E5. If exemption matches, skip all E1–E3 rules for that journey.

---

### Rule E3: Vehicle Class Misclassification

**Legal basis**: NH Fee Rules 2008, **Rule 7** — fee determined by vehicle class. Class misrepresentation constitutes evasion. **Rule 15** — penalty of 2× applicable fee applies.

**Trigger condition**:
```
FASTag vehicle_class_tagged ≠ ANPR vehicle_class_detected
AND
FASTag class is a LOWER fee tier than ANPR-detected class
```

Fee tier order (lowest to highest): `2W < LMV = Car < LCV < Bus = Truck < MAV`

**Note**: If FASTag class is HIGHER than ANPR class, this is not evasion (overpayment). No rule fires. If classes differ but are in same fee tier (e.g., `Bus` vs `Truck`), no rule fires.

**Input**: Journey object with `vehicle_class_fastag` and `vehicle_class_anpr` fields.

**Output**:
```json
{
  "rule_code": "E3",
  "rule_description": "Vehicle class misclassification — FASTag tag class lower than detected class",
  "legal_reference": "NH Fee Rules 2008, Rule 7 & 15",
  "violation_type": "class_misclassification",
  "plate": "KA09AB1234",
  "checkpoint_id": "CP-10",
  "evidence_ids": ["anpr_event_uuid", "fastag_event_uuid"],
  "confidence": 1.0,
  "estimated_loss": 140.0
}
```

---

### Rule E4: Unregistered Vehicle

**Legal basis**: Motor Vehicles Act 1988, **Section 39** — "Every motor vehicle used on a public road must be registered."

**Penalty provision**: **Section 192** — "Using vehicle without registration" — penalty citation included in legal event.

**Trigger condition**:
```
ANPR event enrichment field vehicle_db_match = false
(Plate not found in vehicles table during ingestion enrichment)
```

**Input**: Enriched ANPR event with `vehicle_db_match = false`.

**Output**:
```json
{
  "rule_code": "E4",
  "rule_description": "Vehicle plate not found in government registration database",
  "legal_reference": "Motor Vehicles Act 1988, Section 39 & 192",
  "violation_type": "unregistered_vehicle",
  "plate": "XX00ZZ9999",
  "checkpoint_id": "CP-01",
  "evidence_ids": ["anpr_event_uuid"],
  "confidence": 1.0,
  "estimated_loss": null
}
```

**Note**: This fires immediately on the first ANPR read, not waiting for journey completion.

---

### Rule E5: Impossible Journey / Cloned Plate

**Legal basis**: Motor Vehicles Act 1988:
- **Section 112** — Speed limits: "No person shall drive exceeding the prescribed speed limit"
- **Section 183** — "Driving at excessive speed" — penalty provision
- **Section 192A** — "Using vehicle with false registration mark" — cloned/duplicate plates

**Violation type**: Either speed violation (mathematically proven) or cloned plate indication.

**Trigger condition**:
```
Time between two consecutive checkpoint reads for same plate
< minimum physically possible time for that distance at speed limit
```

**Minimum time lookup**: See DATA_PIPELINE.md inter-checkpoint distance table. Minimum time = distance / speed_limit_for_class.

Speed limits by class (per MV Act and highway regulations):

| Class | Speed Limit (km/h) |
|-------|-------------------|
| Car, LMV | 120 |
| LCV | 100 |
| Bus | 90 |
| Truck, MAV | 80 |

**Note**: Inter-checkpoint time below minimum possible time = Section 112 violation (speed limit breach). Section 183 is the penalty provision cited in enforcement.

**Input**: Two consecutive ANPR events for same plate, same direction. Calculate time delta vs minimum possible time.

**Output**:
```json
{
  "rule_code": "E5",
  "rule_description": "Inter-checkpoint time below physical minimum — possible cloned plate or GPS spoofing",
  "legal_reference": "Motor Vehicles Act 1988, Sections 112, 183, 192A",
  "violation_type": "impossible_journey",
  "plate": "KA09AB1234",
  "checkpoint_id": "CP-06",
  "evidence_ids": ["anpr_event_uuid_1", "anpr_event_uuid_2"],
  "confidence": 1.0,
  "estimated_loss": null
}
```

---

## Route Monitoring Rules

### Rule R1: Invalid Checkpoint Sequence

**Trigger condition**:
```
Vehicle detected at a checkpoint that is NOT the next expected checkpoint
in the direction of travel
AND
the checkpoint is geographically behind the last visited checkpoint
(vehicle appears to be going backwards)
```

**Example**: Vehicle traveling MB (Mysore→Bangalore) detected at CP-01, then CP-06, then CP-03. CP-03 is behind CP-06 in MB direction.

**Output**: Sets `journey.flags.append("invalid_sequence")`. Does not produce a `legal_event` directly — instead, flags the journey for manual review and ensures ML models weight this journey higher for evasion scoring.

---

### Rule R2: Physical Impossibility Check

Same logic as E5 but runs as a route monitoring rule on every checkpoint pair, not just for evasion detection. When R2 fires, it also triggers E5.

**Legal basis**: Same as E5 — Motor Vehicles Act 1988, Sections 112, 183, 192A.

---

### Rule R3: Journey Timeout

**Trigger condition**:
```
Vehicle detected at entry checkpoint
AND
No further reads for 3× expected total journey time
AND
No exit checkpoint read
```

**Expected total journey time**: 120 km / speed_limit_for_class × 1.5 (buffer). For a car: 120/120 × 1.5 = 1.5 hours. Timeout at 4.5 hours.

**Output**: Sets `journey.status = 'timeout'`. Emits journey update. Does not produce a `legal_event` — this is informational. Could indicate breakdown, exit via service road, or legitimate stop.

---

## Legal Event Record — Complete Schema

Every rule that fires produces exactly one record with this structure:

```json
{
  "legal_event_id": "uuid (auto-generated)",
  "rule_code": "E1",
  "rule_description": "Human-readable description of violation",
  "legal_reference": "Specific act, section, and clause (e.g., 'NH Fee Rules 2008, Rule 5 & 15' or 'MV Act 1988, Section 39 & 192')",
  "plate": "KA09AB1234",
  "journey_id": "uuid (FK to journeys)",
  "checkpoint_id": "CP-06",
  "violation_type": "toll_non_payment",
  "evidence_ids": ["uuid1", "uuid2"],
  "confidence": 1.0,
  "estimated_loss": 80.0,
  "status": "pending_review",
  "officer_notes": null,
  "created_at": "2024-01-15T09:45:30Z"
}
```

**Immutability enforcement**:
- PostgreSQL role for app user: `GRANT INSERT, SELECT ON legal_events TO raah_app;`
- No `UPDATE` or `DELETE` permission
- `status` can be updated to `reviewed` via a separate admin role only
- `officer_notes` added via separate admin UPDATE path

---

## Why AI Cannot Touch This Layer

1. **Legal certainty**: These rules map directly to codified law. A toll non-payment is either factual or not. There is no probability.
2. **Evidence admissibility**: Under IT Act 2000, electronic evidence must be deterministic and reproducible. ML scores are not admissible as standalone evidence; mathematical proofs are.
3. **Liability boundary**: If the system wrongly accuses via ML, it's a model error. If hard logic wrongly fires, it's a code bug — fixable and auditable. Mixing the two creates unclear liability.
4. **Separation of concerns**: Hard logic produces facts. ML produces hypotheses. The alert engine presents both, clearly labeled, to human officers who make final decisions.
