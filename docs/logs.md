# RAAH Implementation Log

## System Overview
- RAAH: Real-time AI Highway Monitoring for NH-275 (Mysore-Bangalore)
- Architecture: Simulator (8001) → Redis Streams → Backend (8000) → Dashboards (5173, 5174)
- ML Service (8002) for scoring + PostgreSQL/Redis for storage
- Human-in-the-loop required: ML produces candidates, not verdicts

## Inconsistencies Found
1. **Toll plaza count**: MAP_DEMO_SCRIPT says 2 toll plazas but DATA_PIPELINE has 4 (CP-03, CP-06, CP-10, CP-11). Will implement per DATA_PIPELINE (4 toll plazas).
2. **MAP_IMPLEMENTATION_PLAN**: Shows only CP-03 and CP-11 as full plazas, contradicts DATA_PIPELINE. Will follow DATA_PIPELINE.
3. **Zone descriptions**: Slight naming differences between docs. Will follow DATA_PIPELINE as system-of-record.

## Implementation Order
1. Docker infrastructure (docker-compose.yml) ✅
2. Database models (backend/db/models.py) ✅
3. DB session + seed script (next)
4. Simulator (generators + main.py)
5. Backend (FastAPI + ingestion + journey + hard logic)
6. ML Service (scoring + training pipelines)
7. Authority Dashboard (React + Leaflet + Socket.IO)
8. Commuter Portal (React + basic features)
9. Integration & polish

## Notes
- Keeping ML pipeline functional but pragmatic (scikit-learn based)
- Dashboard needs smooth CSS animations (no Framer Motion)
- All 5 demo scenarios must work
