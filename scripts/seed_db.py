"""
Seed database with generated data for RAAH Highway Monitoring System
Loads vehicles, checkpoints, zones, and historical data into SQLite
"""

import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.db.models import (
    Vehicle, VehicleExemption, Checkpoint, Zone, HistoricalIncident,
    ZoneBaseline, ModelMetric
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_json_data(file_path):
    """Load data from JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        return None


def create_database_session(database_url):
    """Create database session"""
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal(), engine


def seed_vehicles(session, vehicles_data):
    """Seed vehicles table"""
    logger.info(f"Seeding {len(vehicles_data)} vehicles...")
    
    vehicles = []
    for vehicle_data in vehicles_data:
        vehicle = Vehicle(
            plate_number=vehicle_data['plate_number'],
            registered_class=vehicle_data['registered_class'],
            registration_state=vehicle_data['registration_state'],
            registration_status=vehicle_data['registration_status'],
            owner_type=vehicle_data['owner_type'],
            registration_date=datetime.fromisoformat(vehicle_data['registration_date']).date(),
            fitness_expiry=datetime.fromisoformat(vehicle_data['fitness_expiry']).date(),
            insurance_expiry=datetime.fromisoformat(vehicle_data['insurance_expiry']).date(),
            fuel_type=vehicle_data['fuel_type'],
            puc_upto=datetime.fromisoformat(vehicle_data['puc_upto']).date(),
            permit_status=vehicle_data['permit_status'],
            permit_expiry=datetime.fromisoformat(vehicle_data['permit_expiry']).date() if vehicle_data['permit_expiry'] else None,
            maker_model=vehicle_data['maker_model'],
            created_at=datetime.fromisoformat(vehicle_data['created_at'])
        )
        vehicles.append(vehicle)
    
    session.bulk_save_objects(vehicles)
    session.commit()
    logger.info(f"Seeded {len(vehicles)} vehicles successfully")


def seed_vehicle_exemptions(session, exemptions_data):
    """Seed vehicle exemptions table"""
    logger.info(f"Seeding {len(exemptions_data)} vehicle exemptions...")
    
    exemptions = []
    for exemption_data in exemptions_data:
        exemption = VehicleExemption(
            exemption_id=exemption_data['exemption_id'],
            plate_number=exemption_data['plate_number'],
            exemption_type=exemption_data['exemption_type'],
            authority_issued=exemption_data['authority_issued'],
            valid_from=datetime.fromisoformat(exemption_data['valid_from']).date(),
            valid_until=datetime.fromisoformat(exemption_data['valid_until']).date(),
            reference_number=exemption_data['reference_number'],
            is_active=exemption_data['is_active'],
            created_at=datetime.fromisoformat(exemption_data['created_at'])
        )
        exemptions.append(exemption)
    
    session.bulk_save_objects(exemptions)
    session.commit()
    logger.info(f"Seeded {len(exemptions)} vehicle exemptions successfully")


def seed_checkpoints(session, checkpoints_data):
    """Seed checkpoints table"""
    logger.info(f"Seeding {len(checkpoints_data)} checkpoints...")
    
    checkpoints = []
    for checkpoint_data in checkpoints_data:
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_data['checkpoint_id'],
            highway_id=checkpoint_data['highway_id'],
            name=checkpoint_data['name'],
            km_marker=checkpoint_data['km_marker'],
            type=checkpoint_data['type'],
            camera_ids=checkpoint_data['camera_ids'],
            direction_coverage=checkpoint_data['direction_coverage'],
            zone_id=checkpoint_data['zone_id'],
            sensor_reliability=checkpoint_data['sensor_reliability']
        )
        checkpoints.append(checkpoint)
    
    session.bulk_save_objects(checkpoints)
    session.commit()
    logger.info(f"Seeded {len(checkpoints)} checkpoints successfully")


def seed_zones(session, zones_data):
    """Seed zones table"""
    logger.info(f"Seeding {len(zones_data)} zones...")
    
    zones = []
    for zone_data in zones_data:
        zone = Zone(
            zone_id=zone_data['zone_id'],
            highway_id=zone_data['highway_id'],
            name=zone_data['name'],
            km_start=zone_data['km_start'],
            km_end=zone_data['km_end'],
            type=zone_data['type'],
            zone_class=zone_data['zone_class'],
            access_type=zone_data['access_type'],
            entry_checkpoint=zone_data['entry_checkpoint'],
            exit_checkpoint=zone_data['exit_checkpoint']
        )
        zones.append(zone)
    
    session.bulk_save_objects(zones)
    session.commit()
    logger.info(f"Seeded {len(zones)} zones successfully")


def seed_historical_incidents(session, incidents_data):
    """Seed historical incidents table"""
    logger.info(f"Seeding {len(incidents_data)} historical incidents...")
    
    incidents = []
    for incident_data in incidents_data:
        incident = HistoricalIncident(
            incident_id=incident_data['incident_id'],
            segment_id=incident_data['segment_id'],
            km_marker=incident_data['km_marker'],
            incident_type=incident_data['incident_type'],
            severity=incident_data['severity'],
            timestamp=datetime.fromisoformat(incident_data['timestamp']),
            vehicles_involved=incident_data['vehicles_involved'],
            response_time_minutes=incident_data['response_time_minutes'],
            resolution_time_minutes=incident_data['resolution_time_minutes']
        )
        incidents.append(incident)
    
    session.bulk_save_objects(incidents)
    session.commit()
    logger.info(f"Seeded {len(incidents)} historical incidents successfully")


def generate_zone_baselines(session):
    """Generate zone baseline data"""
    logger.info("Generating zone baselines...")
    
    # Get all zones
    zones = session.query(Zone).all()
    baselines = []
    
    for zone in zones:
        # Generate baselines for each 15-minute time slot (96 per day)
        for hour in range(24):
            for minute in [0, 15, 30, 45]:
                time_slot = f"{hour:02d}:{minute:02d}"
                
                # Different patterns for different day types
                for day_type in ['weekday', 'weekend', 'holiday']:
                    # Base traffic patterns
                    if day_type == 'weekday':
                        # Rush hour patterns
                        if 7 <= hour <= 9 or 17 <= hour <= 19:
                            throughput_mean = random.uniform(80, 120)
                            throughput_std = random.uniform(10, 20)
                        elif 10 <= hour <= 16:
                            throughput_mean = random.uniform(40, 80)
                            throughput_std = random.uniform(5, 15)
                        else:
                            throughput_mean = random.uniform(20, 50)
                            throughput_std = random.uniform(3, 10)
                    else:  # weekend/holiday
                        if 10 <= hour <= 18:
                            throughput_mean = random.uniform(60, 100)
                            throughput_std = random.uniform(8, 18)
                        else:
                            throughput_mean = random.uniform(15, 40)
                            throughput_std = random.uniform(2, 8)
                    
                    baseline = ZoneBaseline(
                        baseline_id=str(uuid.uuid4()),
                        zone_id=zone.zone_id,
                        time_slot=time_slot,
                        day_type=day_type,
                        throughput_mean=throughput_mean,
                        throughput_std=throughput_std,
                        flow_continuity_mean=random.uniform(0.7, 0.95),
                        motion_mean=random.uniform(0.1, 0.4),
                        motion_std=random.uniform(0.02, 0.1),
                        fastag_rate_mean=random.uniform(0.85, 0.98),
                        sample_count=random.randint(20, 60),
                        updated_at=datetime.now()
                    )
                    baselines.append(baseline)
    
    session.bulk_save_objects(baselines)
    session.commit()
    logger.info(f"Generated {len(baselines)} zone baselines successfully")


def generate_model_metrics(session):
    """Generate initial model metrics"""
    logger.info("Generating model metrics...")
    
    models = [
        {'name': 'evasion_scorer', 'version': 'v1.0.0'},
        {'name': 'zone_anomaly', 'version': 'v1.0.0'},
        {'name': 'wildlife_detector', 'version': 'v1.0.0'},
        {'name': 'risk_scorer', 'version': 'v1.0.0'}
    ]
    
    metrics = []
    for model in models:
        metric = ModelMetric(
            metric_id=str(uuid.uuid4()),
            model_name=model['name'],
            model_version=model['version'],
            accuracy=random.uniform(0.85, 0.95),
            precision_score=random.uniform(0.80, 0.92),
            recall=random.uniform(0.75, 0.90),
            f1=random.uniform(0.78, 0.91),
            false_positive_rate=random.uniform(0.05, 0.15),
            confirmed_rate=random.uniform(0.70, 0.85),
            auc_roc=random.uniform(0.88, 0.96),
            silhouette_score=random.uniform(0.5, 0.8) if 'anomaly' in model['name'] else None,
            training_samples=random.randint(5000, 15000),
            computed_at=datetime.now()
        )
        metrics.append(metric)
    
    session.bulk_save_objects(metrics)
    session.commit()
    logger.info(f"Generated {len(metrics)} model metrics successfully")


def verify_database(session):
    """Verify database contents"""
    logger.info("Verifying database contents...")
    
    # Check vehicle count
    vehicle_count = session.query(Vehicle).count()
    logger.info(f"Vehicle count: {vehicle_count}")
    
    # Check exemption count
    exemption_count = session.query(VehicleExemption).count()
    logger.info(f"Exemption count: {exemption_count}")
    
    # Check checkpoint count
    checkpoint_count = session.query(Checkpoint).count()
    logger.info(f"Checkpoint count: {checkpoint_count}")
    
    # Check zone count
    zone_count = session.query(Zone).count()
    logger.info(f"Zone count: {zone_count}")
    
    # Check historical incident count
    incident_count = session.query(HistoricalIncident).count()
    logger.info(f"Historical incident count: {incident_count}")
    
    return {
        'vehicles': vehicle_count,
        'exemptions': exemption_count,
        'checkpoints': checkpoint_count,
        'zones': zone_count,
        'incidents': incident_count
    }


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Seed RAAH database")
    parser.add_argument("--database-url", 
                       default="sqlite:///./raah.db",
                       help="SQLite database URL")
    parser.add_argument("--data-dir", 
                       default="simulator/data",
                       help="Directory containing seed data files")
    parser.add_argument("--historical-days", 
                       type=int, default=30,
                       help="Number of days of historical data to generate")
    
    args = parser.parse_args()
    
    try:
        # Create database session
        session, engine = create_database_session(args.database_url)
        
        # Load data files
        data_dir = Path(args.data_dir)
        
        vehicles_data = load_json_data(data_dir / "vehicles_seed.json")
        exemptions_data = load_json_data(data_dir / "vehicle_exemptions.json")
        checkpoints_data = load_json_data(data_dir / "checkpoints.json")
        zones_data = load_json_data(data_dir / "zones.json")
        incidents_data = load_json_data(data_dir / "historical_incidents.json")
        
        if not all([vehicles_data, checkpoints_data, zones_data, incidents_data]):
            logger.error("Missing required data files")
            return False
        
        # Seed data in order (respect foreign key constraints)
        logger.info("Starting database seeding...")
        
        # 1. Seed zones first (checkpoints reference zones)
        seed_zones(session, zones_data)
        
        # 2. Seed checkpoints
        seed_checkpoints(session, checkpoints_data)
        
        # 3. Seed vehicles
        seed_vehicles(session, vehicles_data)
        
        # 4. Seed vehicle exemptions
        if exemptions_data:
            seed_vehicle_exemptions(session, exemptions_data)
        
        # 5. Seed historical incidents
        seed_historical_incidents(session, incidents_data)
        
        # 6. Generate additional data
        generate_zone_baselines(session)
        generate_model_metrics(session)
        
        # Verify database
        counts = verify_database(session)
        
        logger.info("Database seeding completed successfully!")
        logger.info(f"Summary: {counts}")
        
        # Check if we have the required 50,000 vehicles
        if counts['vehicles'] >= 50000:
            logger.info("✅ Phase 0 Checkpoint PASSED: 50,000+ vehicles in database")
            return True
        else:
            logger.error(f"❌ Phase 0 Checkpoint FAILED: Only {counts['vehicles']} vehicles in database")
            return False
        
    except Exception as e:
        logger.error(f"Database seeding failed: {e}")
        return False
    finally:
        session.close()


if __name__ == "__main__":
    import random  # Import needed for baseline generation
    success = main()
    exit(0 if success else 1)