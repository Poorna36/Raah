# Compliance & Ethics

## Legal Framework Mapping
Every hard logic rule maps to a specific legal provision. This mapping is enforced in code — each `legal_event` record carries the exact citation. 

**Refer to `LEGAL_FRAMEWORK.md` for:**
- Statutory Basis (NH Fee Rules 2008, Motor Vehicles Act 1988)
- Penalty Structure (e.g., Rule 15 for 2x penalty)
- Full citation mapping and Evidence Admissibility framework.

---

## Data Governance

### Data Classification

| Data Type | Classification | Retention | Anonymization |
|-----------|---------------|-----------|---------------|
| ANPR events (plate numbers) | PII — vehicle identifier | 90 days raw, then anonymized | Plate hashed with SHA-256 + salt |
| FASTag transactions | PII — financial | 90 days raw, then anonymized | Tag ID + plate hashed |
| CCTV motion index | Non-PII (aggregate metric) | 30 days raw, hourly aggregates permanent | None needed |
| Journey records | PII — movement tracking | 90 days raw, then anonymized | Plate hashed, checkpoints retained |
| Legal event records | PII — enforcement | Retained while case open + 1 year after closure | Plate hashed after retention period |
| ML alerts | PII if plate attached | 90 days, then anonymized | Plate hashed |
| Officer feedback | Non-PII (operational) | Permanent (training data) | Already anonymized (no plate in feedback record post-processing) |
| Vehicle DB records | PII — government data | Mirror of source. Updated per source policy | N/A — government controlled |
| Zone state vectors | Non-PII (aggregate) | Permanent (baselines) | None needed |
| Model metrics | Non-PII | Permanent | None needed |

### Anonymization Implementation

After 90 days, a nightly batch job:
1. Selects all records with `created_at < NOW() - INTERVAL '90 days'`
2. Checks if any record is linked to an **open** enforcement case (legal_event with status ≠ 'closed')
3. If linked to open case: skip (retain until case closes + 1 year)
4. If not linked: replace `plate_number` with `SHA256(plate_number + ANONYMIZATION_SALT)`
5. Log anonymization batch in audit table

**ANONYMIZATION_SALT**: Stored in env var, not in code. Prevents rainbow table reversal.

---

## DPDP Act 2023 Alignment
**Refer to `LEGAL_FRAMEWORK.md` (Section 5)** for complete details on DPDP Act 2023 alignment, grounds for processing without explicit individual consent (state function), and obligations of Data Fiduciary (Section 8). Data retention/anonymization is implemented as described in the Data Governance section above.

---

## Human-in-the-Loop Design

### What AI Can Do

| Action | Permitted | Requires Human |
|--------|-----------|----------------|
| Score a journey for evasion probability | ✅ | No |
| Generate evidence bundle | ✅ | No |
| Detect zone anomaly | ✅ | No |
| Classify incident type | ✅ | No |
| Detect wildlife intrusion | ✅ | No |
| Score zone risk tiers | ✅ | No |
| Estimate commuter journey time | ✅ | No |
| **Issue enforcement action** | ❌ | **Always** |
| **Label a vehicle as evader** | ❌ | **Always** |
| **Generate a legal charge** | ❌ | **Always** |
| **Share vehicle data externally** | ❌ | **Always** |
| Modify hard logic rules | ❌ | Never (code change only) |

### Enforcement Boundary

```
ML Output → Candidate Alert (status: pending_review)
                    ↓
         Officer Reviews Evidence
                    ↓
         Officer Confirms or Dismisses
                    ↓
         If Confirmed → Enforcement Pipeline (outside RAAH scope)
```

**No automated enforcement.** Every ML-generated alert requires explicit officer action. The system presents evidence and recommendations. Humans decide.

### Why This Boundary Exists

1. **Legal requirement**: Automated penalty systems require specific legislative authority (e.g., speed cameras under MV Act). ML-based evasion detection does not have explicit legislative backing for automated enforcement.
2. **Model uncertainty**: ML outputs are probabilistic. A 91% evasion probability means 9% chance of being wrong. Automated enforcement at this error rate is unacceptable.
3. **Accountability**: When a human confirms a case, there is clear accountability. When an algorithm acts alone, liability is ambiguous.
4. **Trust building**: Officers who see the system get it right learn to trust it. Officers who are overridden by automation resist it.

---

## Evidence Bundle Admissibility
**Refer to `LEGAL_FRAMEWORK.md`** for dual compliance structure under IT Act 2000 (Section 65B) and BSA 2023 (Section 63). 

**Evidence bundle structure implementation**:
- Every event has a UUID traceable to raw storage
- Timestamps are ISO8601 with timezone
- Chain of custody: raw event → enriched event → journey → alert → evidence bundle → officer review
- All intermediate states persisted (see ARCHITECTURE.md intermediate persistence table)

---

## Sensor Reliability & Data Quality

### Sensor Trust Scores

Each checkpoint has a `sensor_reliability` score (0–1, default 1.0).

| Event | Effect on Score |
|-------|----------------|
| Officer confirms alert using this sensor's data | No change (expected behavior) |
| Officer dismisses as "Sensor Error" | Score decremented by 0.02 |
| Score drops below 0.7 | Warning in analytics dashboard |
| Score drops below 0.5 | Alerts from this sensor downgraded in priority |

**Purpose**: If a camera is malfunctioning and producing false reads, the system learns to trust it less. This is an operational feedback loop, not an ML training loop.

### Data Quality Checks (Ingestion Layer)

| Check | Action on Failure |
|-------|-------------------|
| Missing required fields | Event rejected, logged to error table |
| Plate format invalid | Event accepted with `quality_flag = format_error` |
| Timestamp in future | Event rejected |
| Timestamp >1 hour old | Event accepted with `quality_flag = delayed` |
| Confidence score <0.5 | Event accepted with `quality_flag = low_confidence` |
| Duplicate event_id | Event rejected (idempotency) |

---

## What RAAH Is Not

| RAAH Is | RAAH Is Not |
|---------|-------------|
| An intelligence layer that assists officers | An autonomous enforcement system |
| A decision support tool | A decision maker |
| A pattern detector that surfaces candidates | A judge that issues verdicts |
| A system that improves with human feedback | A system that learns to bypass human judgment |
| A hackathon prototype demonstrating feasibility | A production-ready deployment |

---

## Ethical Considerations

| Concern | Mitigation |
|---------|------------|
| False accusations | ML never accuses. It scores. Humans decide. Evidence bundle provides full transparency |
| Bias in detection | ML trained on simulator data (unbiased by design). In production: regular bias audits on detection rates by vehicle state, class |
| Privacy of movement | Data anonymized after 90 days. Commuter tracking is opt-in. No persistent movement profiles |
| Surveillance overreach | System only processes highway toll/safety data. No facial recognition. No audio. CCTV is motion index only, not video |
| Accountability gap | Every alert has a human decision. Every decision is logged with officer ID and reason |
