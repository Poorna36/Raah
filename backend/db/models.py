"""
SQLAlchemy models for RAAH Highway Monitoring System
Based on DATABASE_SCHEMA.md specifications - SQLite compatible version
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, Date, DateTime, Text, JSON, Numeric, ForeignKey, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class Vehicle(Base):
    __tablename__ = 'vehicles'
    
    plate_number = Column(String(15), primary_key=True)
    registered_class = Column(String(10), nullable=False)
    registration_state = Column(String(5), nullable=False)
    registration_status = Column(String(15), nullable=False, default='active')
    owner_type = Column(String(15), nullable=False)
    registration_date = Column(Date, nullable=False)
    fitness_expiry = Column(Date, nullable=False)
    insurance_expiry = Column(Date, nullable=False)
    fuel_type = Column(String(10), nullable=False)
    puc_upto = Column(Date, nullable=False)
    permit_status = Column(String(20), nullable=False, default='valid')
    permit_expiry = Column(Date, nullable=True)
    maker_model = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_vehicles_registration_status', 'registration_status'),
        Index('ix_vehicles_registered_class', 'registered_class'),
    )


class VehicleExemption(Base):
    __tablename__ = 'vehicle_exemptions'
    
    exemption_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plate_number = Column(String(15), ForeignKey('vehicles.plate_number'), nullable=False, unique=True)
    exemption_type = Column(String(30), nullable=False)
    authority_issued = Column(String(50), nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_until = Column(Date, nullable=False)
    reference_number = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_vehicle_exemptions_plate_number', 'plate_number'),
        Index('ix_vehicle_exemptions_exemption_type', 'exemption_type'),
        Index('ix_vehicle_exemptions_is_active', 'is_active'),
    )


class Zone(Base):
    __tablename__ = 'zones'
    
    zone_id = Column(String(10), primary_key=True)
    highway_id = Column(String(20), nullable=False, default='NH-275')
    name = Column(String(50), nullable=False)
    km_start = Column(Float, nullable=False)
    km_end = Column(Float, nullable=False)
    type = Column(String(20), nullable=False)
    zone_class = Column(String(20), nullable=False)
    access_type = Column(String(20), nullable=False)
    entry_checkpoint = Column(String(10), ForeignKey('checkpoints.checkpoint_id'))
    exit_checkpoint = Column(String(10), ForeignKey('checkpoints.checkpoint_id'))


class Checkpoint(Base):
    __tablename__ = 'checkpoints'
    
    checkpoint_id = Column(String(10), primary_key=True)
    highway_id = Column(String(20), nullable=False, default='NH-275')
    name = Column(String(50), nullable=False)
    km_marker = Column(Float, nullable=False)
    type = Column(String(20), nullable=False)
    camera_ids = Column(JSON, nullable=False)  # Changed from ARRAY to JSON for SQLite
    direction_coverage = Column(String(10), default='both')
    zone_id = Column(String(10), ForeignKey('zones.zone_id'))
    sensor_reliability = Column(Float, nullable=False, default=0.98)


class CheckpointEvent(Base):
    __tablename__ = 'checkpoint_events'
    
    event_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    checkpoint_id = Column(String(10), ForeignKey('checkpoints.checkpoint_id'), nullable=False)
    camera_id = Column(String(10), nullable=False)
    plate_number = Column(String(15), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    confidence_score = Column(Float, nullable=False)
    vehicle_class_detected = Column(String(10), nullable=False)
    lane_id = Column(String(5), nullable=True)
    image_ref = Column(String(100), nullable=True)
    direction = Column(String(5), nullable=False)
    raw_read = Column(String(20), nullable=True)
    vehicle_db_match = Column(Boolean, default=True)
    registered_class = Column(String(10), nullable=True)
    registration_status = Column(String(15), nullable=True)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_checkpoint_events_plate_number_timestamp', 'plate_number', 'timestamp'),
        Index('ix_checkpoint_events_checkpoint_id_timestamp', 'checkpoint_id', 'timestamp'),
        Index('ix_checkpoint_events_timestamp', 'timestamp'),
    )


class FastagEvent(Base):
    __tablename__ = 'fastag_events'
    
    transaction_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tag_id = Column(String(30), nullable=False)
    vehicle_plate = Column(String(15), nullable=False)
    plaza_id = Column(String(10), ForeignKey('checkpoints.checkpoint_id'), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    amount_charged = Column(Numeric(10, 2), nullable=False)
    vehicle_class_tagged = Column(String(10), nullable=False)
    transaction_status = Column(String(15), nullable=False)
    bank_id = Column(String(20), nullable=True)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_fastag_events_vehicle_plate_timestamp', 'vehicle_plate', 'timestamp'),
        Index('ix_fastag_events_plaza_id_timestamp', 'plaza_id', 'timestamp'),
        Index('ix_fastag_events_timestamp', 'timestamp'),
    )


class CctvEvent(Base):
    __tablename__ = 'cctv_events'
    
    event_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id = Column(String(10), nullable=False)
    checkpoint_id = Column(String(10), ForeignKey('checkpoints.checkpoint_id'), nullable=False)
    segment_id = Column(String(20), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    motion_index = Column(Float, nullable=False)
    zone_type = Column(String(20), nullable=False)
    frame_window_seconds = Column(Integer, default=5)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_cctv_events_camera_id_timestamp', 'camera_id', 'timestamp'),
        Index('ix_cctv_events_checkpoint_id_timestamp', 'checkpoint_id', 'timestamp'),
        Index('ix_cctv_events_timestamp', 'timestamp'),
    )


class Journey(Base):
    __tablename__ = 'journeys'
    
    journey_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    highway_id = Column(String(20), nullable=False, default='NH-275')
    plate = Column(String(15), nullable=False)
    direction = Column(String(5), nullable=False)
    vehicle_class_anpr = Column(String(10), nullable=True)
    vehicle_class_registered = Column(String(10), nullable=True)
    vehicle_class_fastag = Column(String(10), nullable=True)
    entry_checkpoint = Column(String(10), ForeignKey('checkpoints.checkpoint_id'))
    exit_checkpoint = Column(String(10), ForeignKey('checkpoints.checkpoint_id'), nullable=True)
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    last_checkpoint = Column(String(10), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    checkpoints_visited = Column(JSON, nullable=False)  # Changed from JSONB to JSON
    expected_checkpoints = Column(JSON, nullable=False)  # Changed from ARRAY to JSON
    status = Column(String(15), default='active')
    journey_start = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('plate', 'direction', 'journey_start'),
        Index('ix_journeys_status', 'status'),
        Index('ix_journeys_entry_time', 'entry_time'),
    )


class LegalEvent(Base):
    __tablename__ = 'legal_events'
    
    legal_event_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_code = Column(String(5), nullable=False)
    rule_description = Column(String(200), nullable=False)
    legal_reference = Column(String(200), nullable=False)
    plate = Column(String(15), nullable=False)
    journey_id = Column(String(36), ForeignKey('journeys.journey_id'))
    checkpoint_id = Column(String(10), ForeignKey('checkpoints.checkpoint_id'))
    violation_type = Column(String(30), nullable=False)
    evidence_ids = Column(JSON, nullable=False)  # Changed from ARRAY to JSON
    confidence = Column(Float, default=1.0)
    missed_amount = Column(Numeric(10, 2), nullable=True)
    applicable_penalty = Column(Numeric(10, 2), nullable=True)
    status = Column(String(20), default='pending_review')
    officer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_legal_events_plate', 'plate'),
        Index('ix_legal_events_rule_code', 'rule_code'),
        Index('ix_legal_events_created_at', 'created_at'),
        Index('ix_legal_events_status', 'status'),
    )


class MlAlert(Base):
    __tablename__ = 'ml_alerts'
    
    alert_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_type = Column(String(20), nullable=False)
    model_name = Column(String(30), nullable=False)
    model_version = Column(String(50), nullable=False)
    plate = Column(String(15), nullable=True)
    journey_id = Column(String(36), ForeignKey('journeys.journey_id'), nullable=True)
    zone_id = Column(String(10), ForeignKey('zones.zone_id'))
    probability = Column(Float, nullable=False)
    top_features = Column(JSON, nullable=True)  # Changed from JSONB to JSON
    incident_type = Column(String(30), nullable=True)
    evidence_bundle = Column(JSON, nullable=True)  # Changed from JSONB to JSON
    suggested_action = Column(Text, nullable=True)
    severity = Column(String(10), nullable=False)
    officer_action = Column(String(30), default='pending_review')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_ml_alerts_alert_type_created_at', 'alert_type', 'created_at'),
        Index('ix_ml_alerts_officer_action', 'officer_action'),
        Index('ix_ml_alerts_zone_id', 'zone_id'),
        Index('ix_ml_alerts_plate', 'plate'),
    )


class AlertFeedback(Base):
    __tablename__ = 'alert_feedback'
    
    feedback_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String(36), ForeignKey('ml_alerts.alert_id'), nullable=False, unique=True)
    action = Column(String(30), nullable=False)
    reason = Column(Text, nullable=True)
    officer_id = Column(String(30), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    training_label = Column(Integer, nullable=True)
    processed = Column(Boolean, default=False)
    
    __table_args__ = (
        Index('ix_alert_feedback_alert_id', 'alert_id'),
        Index('ix_alert_feedback_processed', 'processed'),
        Index('ix_alert_feedback_created_at', 'created_at'),
    )


class ZoneRiskProfile(Base):
    __tablename__ = 'zone_risk_profiles'
    
    profile_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    zone_id = Column(String(10), ForeignKey('zones.zone_id'), nullable=False)
    risk_tier = Column(String(10), nullable=False)
    risk_score = Column(Float, nullable=False)
    dominant_risk_type = Column(String(30), nullable=False)
    peak_risk_hours = Column(JSON, nullable=True)  # Changed from ARRAY to JSON
    time_risk_curve = Column(JSON, nullable=True)  # Changed from ARRAY to JSON
    corridor_risk_elevated = Column(Boolean, default=False)
    computed_at = Column(DateTime(timezone=True), nullable=False)
    model_version = Column(String(50), nullable=True)
    
    __table_args__ = (
        Index('ix_zone_risk_profiles_zone_id_computed_at', 'zone_id', 'computed_at'),
    )


class HistoricalIncident(Base):
    __tablename__ = 'historical_incidents'
    
    incident_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    segment_id = Column(String(20), nullable=False)
    km_marker = Column(Float, nullable=False)
    incident_type = Column(String(20), nullable=False)
    severity = Column(String(10), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    vehicles_involved = Column(Integer, default=1)
    response_time_minutes = Column(Integer, nullable=True)
    resolution_time_minutes = Column(Integer, nullable=True)
    
    __table_args__ = (
        Index('ix_historical_incidents_segment_id_timestamp', 'segment_id', 'timestamp'),
        Index('ix_historical_incidents_incident_type', 'incident_type'),
        Index('ix_historical_incidents_timestamp', 'timestamp'),
    )


class ModelMetric(Base):
    __tablename__ = 'model_metrics'
    
    metric_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name = Column(String(30), nullable=False)
    model_version = Column(String(50), nullable=False)
    accuracy = Column(Float, nullable=True)
    precision_score = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1 = Column(Float, nullable=True)
    false_positive_rate = Column(Float, nullable=True)
    confirmed_rate = Column(Float, nullable=True)
    auc_roc = Column(Float, nullable=True)
    silhouette_score = Column(Float, nullable=True)
    training_samples = Column(Integer, nullable=True)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_model_metrics_model_name_computed_at', 'model_name', 'computed_at'),
    )


class ZoneBaseline(Base):
    __tablename__ = 'zone_baselines'
    
    baseline_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    zone_id = Column(String(10), ForeignKey('zones.zone_id'), nullable=False)
    time_slot = Column(String(5), nullable=False)
    day_type = Column(String(10), nullable=False)
    throughput_mean = Column(Float, nullable=True)
    throughput_std = Column(Float, nullable=True)
    flow_continuity_mean = Column(Float, nullable=True)
    motion_mean = Column(Float, nullable=True)
    motion_std = Column(Float, nullable=True)
    fastag_rate_mean = Column(Float, nullable=True)
    sample_count = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('zone_id', 'time_slot', 'day_type'),
    )