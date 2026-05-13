"""
Generate seed data for RAAH Highway Monitoring System
Creates VAHAN-compliant vehicle records and related seed data
"""

import json
import random
import uuid
from datetime import datetime, timedelta, date
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for seed generation
VEHICLE_COUNT = 50000
EXEMPTION_COUNT = 1000  # 2% of vehicles

# Vehicle class distribution
VEHICLE_CLASSES = {
    'Car': 0.50,      # 50%
    'LMV': 0.20,      # 20%
    'Bus': 0.10,      # 10%
    'Truck': 0.10,    # 10%
    'MAV': 0.05,      # 5%
    '2W': 0.05        # 5%
}

# Registration state distribution
REGISTRATION_STATES = {
    'KA': 0.70,    # Karnataka - 70%
    'TN': 0.15,    # Tamil Nadu - 15%
    'AP': 0.10,    # Andhra Pradesh - 10%
    'KL': 0.03,    # Kerala - 3%
    'MH': 0.02     # Maharashtra - 2%
}

# Fuel type distribution by vehicle class
FUEL_TYPES = {
    'Car': {'PETROL': 0.70, 'DIESEL': 0.20, 'EV': 0.07, 'CNG': 0.03},
    'LMV': {'PETROL': 0.50, 'DIESEL': 0.40, 'EV': 0.05, 'CNG': 0.05},
    'Bus': {'DIESEL': 0.85, 'CNG': 0.10, 'EV': 0.05},
    'Truck': {'DIESEL': 0.95, 'CNG': 0.03, 'EV': 0.02},
    'MAV': {'DIESEL': 0.98, 'CNG': 0.02},
    '2W': {'PETROL': 0.95, 'EV': 0.05}
}

# Registration status distribution
REGISTRATION_STATUS = {
    'active': 0.97,
    'expired': 0.02,
    'suspended': 0.01
}

# Owner type distribution
OWNER_TYPES = {
    'private': 0.75,
    'commercial': 0.20,
    'government': 0.05
}

# Maker models by vehicle class
MAKER_MODELS = {
    'Car': ['MARUTI SWIFT', 'MARUTI DZIRE', 'HYUNDAI I20', 'HYUNDAI I10', 'TATA TIAGO', 'MAHINDRA XUV700', 'TOYOTA INNOVA'],
    'LMV': ['MAHINDRA BOLERO', 'TATA SUMO', 'TOYOTA QUALIS', 'MAHINDRA SCORPIO'],
    'Bus': ['ASHOK LEYLAND VIKING', 'TATA LP 712', 'EICHER SKYLINE', 'SWARAJ MAZDA'],
    'Truck': ['TATA LPT 3118', 'ASHOK LEYLAND U-TRUCK', 'EICHER PRO 6000', 'BHARATBENZ 2523'],
    'MAV': ['TATA LPT 4223', 'ASHOK LEYLAND 4220', 'EICHER PRO 8000'],
    '2W': ['HERO SPLENDOR', 'HONDA ACTIVA', 'BAJAJ PULSAR', 'TVS APACHE']
}

# Exemption types
EXEMPTION_TYPES = ['emergency', 'government', 'diplomatic', 'military', 'permit_exempt']


def weighted_choice(choices):
    """Helper function to make weighted random choices"""
    items = list(choices.items())
    weights = [item[1] for item in items]
    values = [item[0] for item in items]
    return random.choices(values, weights=weights)[0]


def generate_plate_number(state, count):
    """Generate VAHAN-compliant plate number"""
    # Format: {state}{district}{series}{number}
    # e.g., KA09AB1234
    
    districts = {
        'KA': ['01', '02', '03', '04', '05', '06', '07', '08', '09'],  # Karnataka districts
        'TN': ['01', '02', '03', '04', '05', '06', '07', '08', '09'],  # Tamil Nadu districts
        'AP': ['01', '02', '03', '04', '05', '06', '07', '08', '09'],  # Andhra Pradesh districts
        'KL': ['01', '02', '03', '04', '05', '06', '07', '08', '09'],  # Kerala districts
        'MH': ['01', '02', '03', '04', '05', '06', '07', '08', '09']   # Maharashtra districts
    }
    
    district = random.choice(districts.get(state, ['09']))
    series = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))
    number = str(random.randint(1000, 9999))
    
    return f"{state}{district}{series}{number}"


def generate_vehicle_data():
    """Generate a single vehicle record"""
    
    # Basic vehicle attributes
    registered_class = weighted_choice(VEHICLE_CLASSES)
    registration_state = weighted_choice(REGISTRATION_STATES)
    
    # Generate plate number
    plate = generate_plate_number(registration_state, 1)
    
    # Fuel type based on vehicle class
    fuel_type = weighted_choice(FUEL_TYPES[registered_class])
    
    # Registration status
    reg_status = weighted_choice(REGISTRATION_STATUS)
    
    # Owner type
    owner_type = weighted_choice(OWNER_TYPES)
    
    # Maker model
    maker_model = random.choice(MAKER_MODELS[registered_class])
    
    # Registration date (within last 10 years)
    reg_date = date.today() - timedelta(days=random.randint(0, 3650))
    
    # Fitness expiry (1-5 years from registration)
    fitness_expiry = reg_date + timedelta(days=random.randint(365, 1825))
    
    # Insurance expiry (1 year from now, with some expired)
    insurance_days = random.randint(-30, 365)  # Some expired, some future
    insurance_expiry = date.today() + timedelta(days=insurance_days)
    
    # PUC validity (6 months from now, with some expired)
    puc_days = random.randint(-30, 180)
    puc_upto = date.today() + timedelta(days=puc_days)
    
    # Permit status (for commercial vehicles)
    if owner_type == 'commercial':
        permit_status = weighted_choice({'valid': 0.90, 'expired': 0.08, 'not_required': 0.02})
        if permit_status != 'not_required':
            permit_expiry = date.today() + timedelta(days=random.randint(30, 1095))
        else:
            permit_expiry = None
    else:
        permit_status = 'not_required'
        permit_expiry = None
    
    vehicle = {
        'plate_number': plate,
        'registered_class': registered_class,
        'registration_state': registration_state,
        'registration_status': reg_status,
        'owner_type': owner_type,
        'registration_date': reg_date.isoformat(),
        'fitness_expiry': fitness_expiry.isoformat(),
        'insurance_expiry': insurance_expiry.isoformat(),
        'fuel_type': fuel_type,
        'puc_upto': puc_upto.isoformat(),
        'permit_status': permit_status,
        'permit_expiry': permit_expiry.isoformat() if permit_expiry else None,
        'maker_model': maker_model,
        'created_at': datetime.now().isoformat()
    }
    
    return vehicle


def generate_vehicle_exemption(vehicle):
    """Generate exemption record for a vehicle"""
    
    exemption_type = random.choice(EXEMPTION_TYPES)
    
    # Generate valid date range
    valid_from = date.today() - timedelta(days=random.randint(0, 365))
    valid_until = valid_from + timedelta(days=random.randint(180, 1825))
    
    exemption = {
        'exemption_id': str(uuid.uuid4()),
        'plate_number': vehicle['plate_number'],
        'exemption_type': exemption_type,
        'authority_issued': f"{exemption_type.upper()} AUTHORITY",
        'valid_from': valid_from.isoformat(),
        'valid_until': valid_until.isoformat(),
        'reference_number': f"EXEMPT-{random.randint(10000, 99999)}",
        'is_active': True,
        'created_at': datetime.now().isoformat()
    }
    
    return exemption


def generate_checkpoints():
    """Generate checkpoint data for NH-275"""
    
    checkpoints = [
        {
            'checkpoint_id': 'CP-01',
            'highway_id': 'NH-275',
            'name': 'Mysore Entry',
            'km_marker': 0.0,
            'type': 'full_plaza',
            'camera_ids': ['CAM-001', 'CAM-002', 'CAM-003', 'CAM-004'],
            'direction_coverage': 'both',
            'zone_id': 'ZONE-01',
            'sensor_reliability': 0.98
        },
        {
            'checkpoint_id': 'CP-02',
            'highway_id': 'NH-275',
            'name': 'Srirangapatna',
            'km_marker': 15.5,
            'type': 'monitor',
            'camera_ids': ['CAM-005', 'CAM-006'],
            'direction_coverage': 'both',
            'zone_id': 'ZONE-02',
            'sensor_reliability': 0.97
        },
        {
            'checkpoint_id': 'CP-03',
            'highway_id': 'NH-275',
            'name': 'Maddur',
            'km_marker': 32.0,
            'type': 'full_plaza',
            'camera_ids': ['CAM-007', 'CAM-008', 'CAM-009', 'CAM-010'],
            'direction_coverage': 'both',
            'zone_id': 'ZONE-03',
            'sensor_reliability': 0.98
        },
        {
            'checkpoint_id': 'CP-04',
            'highway_id': 'NH-275',
            'name': 'Mandya',
            'km_marker': 45.5,
            'type': 'monitor',
            'camera_ids': ['CAM-011', 'CAM-012'],
            'direction_coverage': 'both',
            'zone_id': 'ZONE-04',
            'sensor_reliability': 0.96
        },
        {
            'checkpoint_id': 'CP-05',
            'highway_id': 'NH-275',
            'name': 'Ramanagara',
            'km_marker': 58.0,
            'type': 'full_plaza',
            'camera_ids': ['CAM-013', 'CAM-014', 'CAM-015', 'CAM-016'],
            'direction_coverage': 'both',
            'zone_id': 'ZONE-05',
            'sensor_reliability': 0.99
        },
        {
            'checkpoint_id': 'CP-06',
            'highway_id': 'NH-275',
            'name': 'Bidadi',
            'km_marker': 72.5,
            'type': 'monitor',
            'camera_ids': ['CAM-017', 'CAM-018'],
            'direction_coverage': 'both',
            'zone_id': 'ZONE-06',
            'sensor_reliability': 0.97
        },
        {
            'checkpoint_id': 'CP-07',
            'highway_id': 'NH-275',
            'name': 'Kengeri',
            'km_marker': 85.0,
            'type': 'monitor',
            'camera_ids': ['CAM-019', 'CAM-020'],
            'direction_coverage': 'both',
            'zone_id': 'ZONE-07',
            'sensor_reliability': 0.98
        },
        {
            'checkpoint_id': 'CP-08',
            'highway_id': 'NH-275',
            'name': 'Bangalore West',
            'km_marker': 95.5,
            'type': 'full_plaza',
            'camera_ids': ['CAM-021', 'CAM-022', 'CAM-023', 'CAM-024'],
            'direction_coverage': 'both',
            'zone_id': 'ZONE-08',
            'sensor_reliability': 0.99
        },
        {
            'checkpoint_id': 'CP-09',
            'highway_id': 'NH-275',
            'name': 'Bangalore Central',
            'km_marker': 105.0,
            'type': 'monitor',
            'camera_ids': ['CAM-025', 'CAM-026'],
            'direction_coverage': 'both',
            'zone_id': 'ZONE-09',
            'sensor_reliability': 0.96
        },
        {
            'checkpoint_id': 'CP-10',
            'highway_id': 'NH-275',
            'name': 'Bangalore East',
            'km_marker': 115.5,
            'type': 'full_plaza',
            'camera_ids': ['CAM-027', 'CAM-028', 'CAM-029', 'CAM-030'],
            'direction_coverage': 'both',
            'zone_id': 'ZONE-10',
            'sensor_reliability': 0.98
        },
        {
            'checkpoint_id': 'CP-11',
            'highway_id': 'NH-275',
            'name': 'Hoskote',
            'km_marker': 125.0,
            'type': 'monitor',
            'camera_ids': ['CAM-031', 'CAM-032'],
            'direction_coverage': 'both',
            'zone_id': 'ZONE-11',
            'sensor_reliability': 0.97
        },
        {
            'checkpoint_id': 'CP-12',
            'highway_id': 'NH-275',
            'name': 'Wildlife Corridor',
            'km_marker': 135.5,
            'type': 'wildlife_sensor',
            'camera_ids': ['CAM-033', 'CAM-034', 'CAM-035'],
            'direction_coverage': 'both',
            'zone_id': 'ZONE-11',
            'sensor_reliability': 0.95
        }
    ]
    
    return checkpoints


def generate_zones():
    """Generate zone data for NH-275"""
    
    zones = [
        {
            'zone_id': 'ZONE-01',
            'highway_id': 'NH-275',
            'name': 'Mysore Urban',
            'km_start': 0.0,
            'km_end': 15.0,
            'type': 'highway',
            'zone_class': 'ZN-URB',
            'access_type': 'ACC-CTRL',
            'entry_checkpoint': 'CP-01',
            'exit_checkpoint': 'CP-02'
        },
        {
            'zone_id': 'ZONE-02',
            'highway_id': 'NH-275',
            'name': 'Srirangapatna Rural',
            'km_start': 15.0,
            'km_end': 30.0,
            'type': 'highway',
            'zone_class': 'ZN-RUR',
            'access_type': 'ACC-CTRL',
            'entry_checkpoint': 'CP-02',
            'exit_checkpoint': 'CP-03'
        },
        {
            'zone_id': 'ZONE-03',
            'highway_id': 'NH-275',
            'name': 'Maddur Urban',
            'km_start': 30.0,
            'km_end': 42.0,
            'type': 'highway',
            'zone_class': 'ZN-URB',
            'access_type': 'ACC-CTRL',
            'entry_checkpoint': 'CP-03',
            'exit_checkpoint': 'CP-04'
        },
        {
            'zone_id': 'ZONE-04',
            'highway_id': 'NH-275',
            'name': 'Mandya Rural',
            'km_start': 42.0,
            'km_end': 55.0,
            'type': 'highway',
            'zone_class': 'ZN-RUR',
            'access_type': 'ACC-CTRL',
            'entry_checkpoint': 'CP-04',
            'exit_checkpoint': 'CP-05'
        },
        {
            'zone_id': 'ZONE-05',
            'highway_id': 'NH-275',
            'name': 'Ramanagara Forest',
            'km_start': 55.0,
            'km_end': 65.0,
            'type': 'forest_corridor',
            'zone_class': 'ZN-FOR',
            'access_type': 'ACC-CTRL',
            'entry_checkpoint': 'CP-05',
            'exit_checkpoint': 'CP-06'
        },
        {
            'zone_id': 'ZONE-06',
            'highway_id': 'NH-275',
            'name': 'Bidadi Industrial',
            'km_start': 65.0,
            'km_end': 80.0,
            'type': 'highway',
            'zone_class': 'ZN-RUR',
            'access_type': 'ACC-CTRL',
            'entry_checkpoint': 'CP-06',
            'exit_checkpoint': 'CP-07'
        },
        {
            'zone_id': 'ZONE-07',
            'highway_id': 'NH-275',
            'name': 'Kengeri Suburban',
            'km_start': 80.0,
            'km_end': 92.0,
            'type': 'highway',
            'zone_class': 'ZN-URB',
            'access_type': 'ACC-CTRL',
            'entry_checkpoint': 'CP-07',
            'exit_checkpoint': 'CP-08'
        },
        {
            'zone_id': 'ZONE-08',
            'highway_id': 'NH-275',
            'name': 'Bangalore West Urban',
            'km_start': 92.0,
            'km_end': 102.0,
            'type': 'highway',
            'zone_class': 'ZN-URB',
            'access_type': 'ACC-CTRL',
            'entry_checkpoint': 'CP-08',
            'exit_checkpoint': 'CP-09'
        },
        {
            'zone_id': 'ZONE-09',
            'highway_id': 'NH-275',
            'name': 'Bangalore Central Metro',
            'km_start': 102.0,
            'km_end': 112.0,
            'type': 'highway',
            'zone_class': 'ZN-URB',
            'access_type': 'ACC-CTRL',
            'entry_checkpoint': 'CP-09',
            'exit_checkpoint': 'CP-10'
        },
        {
            'zone_id': 'ZONE-10',
            'highway_id': 'NH-275',
            'name': 'Bangalore East Urban',
            'km_start': 112.0,
            'km_end': 122.0,
            'type': 'highway',
            'zone_class': 'ZN-URB',
            'access_type': 'ACC-CTRL',
            'entry_checkpoint': 'CP-10',
            'exit_checkpoint': 'CP-11'
        },
        {
            'zone_id': 'ZONE-11',
            'highway_id': 'NH-275',
            'name': 'Hoskote Rural Corridor',
            'km_start': 122.0,
            'km_end': 140.0,
            'type': 'forest_corridor',
            'zone_class': 'ZN-RUR',
            'access_type': 'ACC-CTRL',
            'entry_checkpoint': 'CP-11',
            'exit_checkpoint': 'CP-12'
        }
    ]
    
    return zones


def generate_historical_incidents():
    """Generate historical incident data for 18 months"""
    
    incidents = []
    incident_types = ['accident', 'breakdown', 'obstruction', 'wildlife', 'weather']
    severities = ['minor', 'major', 'fatal']
    severity_weights = {'minor': 0.60, 'major': 0.30, 'fatal': 0.10}
    
    # High-risk locations (KM markers)
    high_risk_locations = [58.0, 82.0, 95.0]  # Maddur, Ramanagara, Bidadi
    
    # Generate incidents for 18 months
    end_date = date.today()
    start_date = end_date - timedelta(days=547)  # ~18 months
    
    current_date = start_date
    incident_id = 1
    
    while current_date <= end_date:
        # Average 0.5 incidents per day
        if random.random() < 0.5:
            # Generate 1-2 incidents for this day
            daily_incidents = random.randint(1, 2)
            
            for _ in range(daily_incidents):
                # Choose location (weighted toward high-risk areas)
                if random.random() < 0.6:  # 60% chance of high-risk location
                    km_marker = random.choice(high_risk_locations) + random.uniform(-2, 2)
                else:
                    km_marker = random.uniform(0, 140)  # Entire corridor
                
                # Choose incident type
                incident_type = random.choice(incident_types)
                
                # Choose severity
                severity = weighted_choice(severity_weights)
                
                # Generate response and resolution times based on severity
                if severity == 'minor':
                    response_time = random.randint(10, 25)
                    resolution_time = random.randint(30, 90)
                elif severity == 'major':
                    response_time = random.randint(15, 35)
                    resolution_time = random.randint(60, 180)
                else:  # fatal
                    response_time = random.randint(20, 45)
                    resolution_time = random.randint(120, 240)
                
                # Generate segment ID
                segment_start = int(km_marker // 2) * 2
                segment_end = segment_start + 2
                segment_id = f"SEG-KM{segment_start:03d}-KM{segment_end:03d}"
                
                incident = {
                    'incident_id': str(uuid.uuid4()),
                    'segment_id': segment_id,
                    'km_marker': round(km_marker, 1),
                    'incident_type': incident_type,
                    'severity': severity,
                    'timestamp': datetime.combine(current_date, datetime.min.time()).isoformat(),
                    'vehicles_involved': random.randint(1, 4) if incident_type == 'accident' else 1,
                    'response_time_minutes': response_time,
                    'resolution_time_minutes': resolution_time
                }
                
                incidents.append(incident)
                incident_id += 1
        
        current_date += timedelta(days=1)
    
    return incidents


def generate_seed_data():
    """Generate all seed data"""
    
    logger.info("Generating vehicle seed data...")
    
    # Generate vehicles
    vehicles = []
    used_plates = set()
    
    for i in range(VEHICLE_COUNT):
        while True:
            vehicle = generate_vehicle_data()
            if vehicle['plate_number'] not in used_plates:
                used_plates.add(vehicle['plate_number'])
                vehicles.append(vehicle)
                break
        
        if (i + 1) % 10000 == 0:
            logger.info(f"Generated {i + 1} vehicles...")
    
    logger.info(f"Generated {len(vehicles)} vehicles")
    
    # Generate exemptions (2% of vehicles)
    logger.info("Generating vehicle exemptions...")
    exempted_vehicles = random.sample(vehicles, EXEMPTION_COUNT)
    exemptions = [generate_vehicle_exemption(vehicle) for vehicle in exempted_vehicles]
    logger.info(f"Generated {len(exemptions)} exemptions")
    
    # Generate checkpoints
    logger.info("Generating checkpoints...")
    checkpoints = generate_checkpoints()
    logger.info(f"Generated {len(checkpoints)} checkpoints")
    
    # Generate zones
    logger.info("Generating zones...")
    zones = generate_zones()
    logger.info(f"Generated {len(zones)} zones")
    
    # Generate historical incidents
    logger.info("Generating historical incidents...")
    incidents = generate_historical_incidents()
    logger.info(f"Generated {len(incidents)} historical incidents")
    
    # Save all data
    output_dir = Path("simulator/data")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save vehicles
    with open(output_dir / "vehicles_seed.json", "w") as f:
        json.dump(vehicles, f, indent=2)
    logger.info(f"Saved vehicles to {output_dir / 'vehicles_seed.json'}")
    
    # Save exemptions
    with open(output_dir / "vehicle_exemptions.json", "w") as f:
        json.dump(exemptions, f, indent=2)
    logger.info(f"Saved exemptions to {output_dir / 'vehicle_exemptions.json'}")
    
    # Save checkpoints
    with open(output_dir / "checkpoints.json", "w") as f:
        json.dump(checkpoints, f, indent=2)
    logger.info(f"Saved checkpoints to {output_dir / 'checkpoints.json'}")
    
    # Save zones
    with open(output_dir / "zones.json", "w") as f:
        json.dump(zones, f, indent=2)
    logger.info(f"Saved zones to {output_dir / 'zones.json'}")
    
    # Save historical incidents
    with open(output_dir / "historical_incidents.json", "w") as f:
        json.dump(incidents, f, indent=2)
    logger.info(f"Saved incidents to {output_dir / 'historical_incidents.json'}")
    
    # Generate summary
    summary = {
        'generated_at': datetime.now().isoformat(),
        'vehicles': len(vehicles),
        'exemptions': len(exemptions),
        'checkpoints': len(checkpoints),
        'zones': len(zones),
        'historical_incidents': len(incidents),
        'vehicle_class_distribution': {},
        'state_distribution': {},
        'fuel_type_distribution': {}
    }
    
    # Calculate distributions
    for vehicle in vehicles:
        vclass = vehicle['registered_class']
        state = vehicle['registration_state']
        fuel = vehicle['fuel_type']
        
        summary['vehicle_class_distribution'][vclass] = summary['vehicle_class_distribution'].get(vclass, 0) + 1
        summary['state_distribution'][state] = summary['state_distribution'].get(state, 0) + 1
        summary['fuel_type_distribution'][fuel] = summary['fuel_type_distribution'].get(fuel, 0) + 1
    
    # Save summary
    with open(output_dir / "seed_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info("Seed data generation completed!")
    logger.info(f"Summary: {summary}")
    
    return summary


def main():
    """Main function"""
    
    try:
        summary = generate_seed_data()
        
        print("\n=== Seed Data Generation Summary ===")
        print(f"Vehicles: {summary['vehicles']}")
        print(f"Exemptions: {summary['exemptions']}")
        print(f"Checkpoints: {summary['checkpoints']}")
        print(f"Zones: {summary['zones']}")
        print(f"Historical Incidents: {summary['historical_incidents']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate seed data: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)