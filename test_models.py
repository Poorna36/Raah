"""
Simple test to verify our database models work correctly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.models import Vehicle, Base
from backend.db.session import get_engine, create_tables

def test_models():
    """Test that our models can be created"""
    print("Testing RAAH database models...")
    
    try:
        # Create engine (in-memory SQLite for testing)
        from sqlalchemy import create_engine
        test_engine = create_engine('sqlite:///:memory:')
        
        # Create all tables
        Base.metadata.create_all(bind=test_engine)
        print("✅ All tables created successfully")
        
        # Test creating a vehicle
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=test_engine)
        session = Session()
        
        from datetime import date
        test_vehicle = Vehicle(
            plate_number="KA09AB1234",
            registered_class="Car",
            registration_state="KA",
            registration_status="active",
            owner_type="private",
            registration_date=date.today(),
            fitness_expiry=date.today(),
            insurance_expiry=date.today(),
            fuel_type="PETROL",
            puc_upto=date.today(),
            permit_status="valid",
            maker_model="MARUTI SWIFT"
        )
        
        session.add(test_vehicle)
        session.commit()
        
        # Query the vehicle
        vehicle = session.query(Vehicle).filter_by(plate_number="KA09AB1234").first()
        if vehicle:
            print(f"✅ Vehicle created and retrieved: {vehicle.plate_number}")
        else:
            print("❌ Vehicle not found after creation")
            return False
            
        session.close()
        print("✅ All model tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_models()
    sys.exit(0 if success else 1)