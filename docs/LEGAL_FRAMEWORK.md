# Legal Framework — RAAH System Compliance

This document defines the complete statutory basis for the RAAH enforcement system. Every hard logic rule, evidence bundle, and enforcement action derives authority from these provisions.

---

## 1. National Highways Fee (Determination of Rates and Collection) Rules, 2008

### Rule 5 — Fee Collection
Every vehicle using a national highway is obligated to pay the prescribed fee at the designated toll plaza. Non-payment is an enforceable violation.

**System Implementation:**
- Primary legal basis for toll evasion detection (E1: Non-Payment)
- Fee obligation is statutory, not contractual
- Violation triggers 2× penalty under Rule 15

### Rule 7 — Vehicle Classification
Fees are determined by vehicle class: 2W, LMV, Car, Bus, Truck, MAV. Payment below the applicable rate for the detected vehicle class constitutes an underpayment violation. Class misrepresentation through FASTag tag category mismatch is a Rule 7 violation.

**System Implementation:**
- E2 (Underpayment): Charged amount < minimum rate for ANPR-detected class
- E3 (Misclassification): FASTag class lower than ANPR-detected class
- Rate schedule enforced as deterministic lookup table

### Rule 14 — Exemptions
Certain vehicle categories are statutorily exempt from fee payment:
- Defense vehicles
- Vehicles of the President and Governor
- Emergency vehicles (ambulance, fire, police on duty)

**System Implementation:**
- Exemption whitelist maintained in `vehicle_exemptions` table
- Exempt vehicles bypass all evasion detection logic (E1, E2, E3)
- Exemption status verified during ingestion enrichment

### Rule 15 — Penalty for Non-Payment
A vehicle that does not pay the applicable fee is liable to pay **twice the applicable fee** as penalty.

**System Implementation:**
- Revenue loss calculations use 2× multiplier (Rule 15 penalty)
- `estimated_loss` = (applicable fee × 2) − amount actually paid
- If unpaid: `estimated_loss` = applicable fee × 2
- Evidence bundles cite Rule 15 for penalty computation

---

## 2. Motor Vehicles Act, 1988 (Amended 2019)

### Section 39 — Registration Obligation
Every motor vehicle used on a public road must be registered. A vehicle detected by ANPR whose plate is absent from the government vehicle registry is in violation of Section 39.

**System Implementation:**
- E4 (Unregistered Vehicle) fires when `vehicle_db_match = false`
- Immediate legal event on first ANPR read
- Evidence bundle cites Section 39

### Section 66 — Permit Requirement
Commercial vehicles operating on national highways require a valid permit. Permit status is part of the vehicle DB lookup.

**System Implementation:**
- Commercial vehicle permit status checked during enrichment
- Invalid/expired permit flagged as Section 66 violation
- Stored in `vehicle_db.permit_status` field

### Section 112 — Speed Limits
No person shall drive a vehicle exceeding the prescribed speed limit. Inter-checkpoint travel time below the minimum possible for the distance and speed limit constitutes a mathematically demonstrable Section 112 violation.

**System Implementation:**
- E5 (Impossible Journey) uses speed limits as baseline
- Minimum time = distance / speed_limit_for_class
- Speed limits by class: Car/LMV=120, LCV=100, Bus=90, Truck/MAV=80 km/h

### Section 183 — Driving at Excessive Speed
The enforcement provision for speeding violations with defined penalty structure. Enhanced penalties apply for commercial vehicles.

**System Implementation:**
- Speed violation alerts cite Section 183 (penalty provision)
- Not Section 112 alone (which is the obligation)
- Evidence bundles structured for penalty computation

### Section 192 — Using Vehicle Without Registration
Penalty provision for Section 39 violations. Unregistered vehicle flags cite both Section 39 (obligation) and Section 192 (penalty).

**System Implementation:**
- Legal event records include both citations: `Section 39 & 192, MV Act 1988`
- Dual citation for complete legal basis

### Section 177 — General Penalty
Any violation of the Act for which no specific penalty is prescribed is punishable under Section 177.

**System Implementation:**
- Fallback citation for detected violations without specific penalty provision
- Applied as catch-all where needed

### 2019 Amendment — Electronic Enforcement
The 2019 amendment significantly increased penalties and introduced provisions explicitly contemplating electronic enforcement mechanisms. Digital evidence from ANPR systems and FASTag transactions falls within the enforcement framework this amendment envisioned.

**System Implementation:**
- System designed within electronic enforcement framework
- ANPR captures, FASTag logs constitute digital evidence
- Evidence admissibility under IT Act 2000, Section 65B

---

## 3. Information Technology Act, 2000

### Section 4 — Legal Recognition of Electronic Records
Electronic records have the same legal validity as paper records.

**System Implementation:**
- ANPR captures, FASTag transaction logs, timestamps, system-generated evidence bundles are legally valid electronic records
- No paper trail required for enforcement proceedings

### Section 43A — Compensation for Failure to Protect Data
Bodies corporate handling sensitive personal data and failing to implement reasonable security practices are liable for compensation.

**System Implementation:**
- Statutory basis for data security architecture
- Documented security safeguards required
- Encryption, access controls, audit logging implemented

### Section 65B — Admissibility of Electronic Records
Electronic records are admissible as evidence when:
1. Computer system was functioning properly
2. Record was produced from data stored in ordinary course of activity
3. Record has not been altered

**System Implementation:**
- Every evidence bundle includes system integrity log
- Evidence bundles are traceable to raw event records

---

## 4. Bharatiya Sakshya Adhiniyam, 2023 (BSA)

### Section 61 — Electronic and Digital Records
Electronic records are admissible as documentary evidence. Covers computer-generated records, electronic communications, and digital images. ANPR captures and FASTag records are documentary evidence under this provision.

**System Implementation:**
- BSA 2023 supersedes Indian Evidence Act 1872
- Current applicable evidence statute
- ANPR images and FASTag logs admissible under Section 61

### Section 63 — Admissibility Conditions
Mirrors and reinforces IT Act Section 65B requirements under new evidentiary framework.

**System Implementation:**
- Evidence bundles structured to satisfy both:
  - Section 65B of IT Act 2000
  - Section 63 of BSA 2023
- Both provisions operative during transition period

---

## 5. Digital Personal Data Protection Act, 2023 (DPDP Act)

### Section 4 — Grounds for Processing
Personal data may only be processed for a lawful purpose. Vehicle plate numbers and journey records constitute personal data.

**System Implementation:**
- Lawful basis: state function and public interest (highway enforcement, road safety)
- NOT individual consent
- Processing purpose documented and limited

### Section 8 — Obligations of Data Fiduciary
The entity operating the system must:
- Ensure data accuracy
- Implement security safeguards
- Delete or anonymize data when purpose is fulfilled

**System Implementation:**
- 90-day anonymization policy: plate numbers hashed, personal identifiers stripped
- Exception: records attached to open enforcement cases retained until closure + 1 year
- Direct implementation of Section 8 obligations

### Section 17 — Exemptions for State Instrumentalities
State entities and instrumentalities processing data for public order, public interest, or sovereign functions are partially exempt from consent requirements.

**System Implementation:**
- Specific provision making system processing lawful without individual consent
- Highway authorities (NHAI) and concessionaires qualify under this exemption
- Vehicle journey data processed under Section 17 exemption

---

## 6. National Highways Authority of India Act, 1988

### Section 16 — Power to Collect Fees
NHAI has statutory power to levy and collect fees for use of national highways. The toll enforcement function operates in direct support of this statutory authority.

**System Implementation:**
- System operates under NHAI statutory authority
- Fee collection and enforcement authorized by Section 16

### Section 8A — Entrustment to Private Entities
NHAI may entrust highway development, maintenance, and management to private concessionaires. NH-275 and most national expressways operate under this concessionaire model.

**System Implementation:**
- Concessionaires hold same fee collection rights as NHAI under Section 8A
- System serves both NHAI and concessionaires as joint stakeholders
- Enforcement actions carry authority of both entities

---

## 7. Wildlife Protection Act, 1972

### Schedule I — Protected Species
Schedule I lists species afforded highest level of legal protection. Elephants are Schedule I animals.

**System Implementation:**
- Wildlife intrusion events in Cauvery Wildlife Sanctuary buffer corridor (KM 40–55, NH-275) treated as potential Schedule I incidents
- Not merely road safety events — legal protection status applies
- Priority escalation for Schedule I detections

### Section 38O — Conservation and Management of National Parks
Protected area authorities have jurisdiction over wildlife movement in and adjacent to designated sanctuaries and buffer zones. Forest Department is competent authority under this provision.

**System Implementation:**
- Wildlife intrusion alerts routed to Forest Department as competent authority under Wildlife Protection Act
- Not merely "relevant government department" — statutory authority under Section 38O
- Alerts include legal citation for authority reference

---

## Legal Citation Quick Reference

| Violation Type | Primary Citation | Penalty Citation |
|----------------|------------------|------------------|
| Toll Non-Payment | NH Fee Rules 2008, Rule 5 | Rule 15 (2× penalty) |
| Toll Underpayment | NH Fee Rules 2008, Rule 7 | Rule 15 (2× penalty) |
| Class Misclassification | NH Fee Rules 2008, Rule 7 | Rule 15 (2× penalty) |
| Exemption Claim | NH Fee Rules 2008, Rule 14 | N/A (exempt) |
| Unregistered Vehicle | MV Act 1988, Section 39 | Section 192 |
| Invalid Permit | MV Act 1988, Section 66 | Section 177 (general) |
| Speed Violation | MV Act 1988, Section 112 | Section 183 |
| Impossible Journey | MV Act 1988, Section 192A | Section 192A |
| Cloned Plate | MV Act 1988, Section 66 | Section 192A |

---

## Evidence Admissibility Framework

### Dual Compliance Structure
All evidence bundles must satisfy:
1. **IT Act 2000, Section 65B** — Electronic records admissibility
2. **BSA 2023, Section 63** — Digital records admissibility

### Required Certificate Elements
- System functioning status at time of capture
- Data stored in ordinary course of activity
- Record integrity (no alteration)
- Responsible official identification
- Timestamp and location verification

### Data Retention for Legal Proceedings
- Open enforcement cases: retain until closure + 1 year
- All other records: 90 days then anonymize
- Anonymization: SHA-256 hash with salt
- Audit trail of all retention decisions

---

*This document is the statutory foundation for all system operations. Any system change affecting legal compliance must be reviewed against this framework.*
