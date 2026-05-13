"""
SQLite setup and verification script for RAAH Highway Monitoring System
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.session import create_tables, get_engine
from backend.db.models import Base, Vehicle
from sqlalchemy.orm import sessionmaker

def setup_sqlite_database():
    """Create SQLite database and tables"""
    print("Setting up SQLite database...")
    
    try:
        # Create all tables
        create_tables()
        print("✅ Database tables created successfully")
        
        # Test connection
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in result.fetchall()]
            print(f"Created tables: {tables}")
        
        return True
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def verify_database_contents():
    """Verify database contents and count vehicles"""
    print("Verifying database contents...")
    
    try:
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Count vehicles
        vehicle_count = session.query(Vehicle).count()
        print(f"Vehicle count: {vehicle_count}")
        
        # Show sample vehicles
        sample_vehicles = session.query(Vehicle).limit(5).all()
        print("\nSample vehicles:")
        for vehicle in sample_vehicles:
            print(f"  - {vehicle.plate_number} ({vehicle.registered_class}, {vehicle.registration_state})")
        
        session.close()
        
        if vehicle_count >= 50000:
            print(f"✅ Phase 0 Checkpoint PASSED: {vehicle_count} vehicles in database")
            return True
        else:
            print(f"❌ Phase 0 Checkpoint FAILED: Only {vehicle_count} vehicles in database")
            return False
            
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

def main():
    """Main function"""
    print("🚀 RAAH SQLite Setup and Verification")
    
    # Setup database
    if not setup_sqlite_database():
        return False
    
    # Verify contents (will show 0 vehicles initially)
    verify_database_contents()
    
    print("\nNext steps:")
    print("1. Generate seed data: python scripts/generate_seed_data.py")
    print("2. Seed database: python scripts/seed_db.py")
    print("3. Verify final count: python verify_sqlite.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)