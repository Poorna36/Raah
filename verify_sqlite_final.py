"""
Python verification script for RAAH SQLite database
Verifies 50,000 vehicle count and database integrity
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.session import get_engine, create_tables
from backend.db.models import Base, Vehicle, Checkpoint, Zone, VehicleExemption, HistoricalIncident
from sqlalchemy.orm import sessionmaker

def setup_and_verify_database():
    """Setup SQLite database and verify contents"""
    print("🚀 Setting up SQLite database and verifying contents...")
    
    try:
        # Create tables
        create_tables()
        print("✅ Database tables created successfully")
        
        # Create session
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check vehicle count
        vehicle_count = session.query(Vehicle).count()
        print(f"Vehicle count: {vehicle_count}")
        
        # Check other tables
        checkpoint_count = session.query(Checkpoint).count()
        zone_count = session.query(Zone).count()
        exemption_count = session.query(VehicleExemption).count()
        incident_count = session.query(HistoricalIncident).count()
        
        print(f"Checkpoint count: {checkpoint_count}")
        print(f"Zone count: {zone_count}")
        print(f"Exemption count: {exemption_count}")
        print(f"Historical incident count: {incident_count}")
        
        # Show sample vehicles if any exist
        if vehicle_count > 0:
            sample_vehicles = session.query(Vehicle).limit(5).all()
            print("\nSample vehicles:")
            for vehicle in sample_vehicles:
                print(f"  - {vehicle.plate_number} ({vehicle.registered_class}, {vehicle.registration_state})")
        
        session.close()
        
        # Check if we have the required 50,000 vehicles
        if vehicle_count >= 50000:
            print(f"\n🎉 Phase 0 Checkpoint PASSED: {vehicle_count} vehicles in database")
            return True
        else:
            print(f"\n❌ Phase 0 Checkpoint FAILED: Only {vehicle_count} vehicles in database")
            return False
            
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("RAAH SQLite Database Verification")
    print("=" * 60)
    
    success = setup_and_verify_database()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Phase 0 Implementation Complete!")
        print("Ready for Phase 1: Simulator implementation")
    else:
        print("❌ Phase 0 Implementation Needs Data")
        print("Run the following commands:")
        print("1. python scripts/generate_seed_data.py")
        print("2. python scripts/seed_db.py")
        print("3. python verify_sqlite_final.py")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)