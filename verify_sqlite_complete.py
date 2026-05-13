"""
Comprehensive SQLite verification script for RAAH Highway Monitoring System
This script can be run when Python is available to verify the database setup
"""

import sys
import os
import json
import sqlite3
from pathlib import Path

def check_sqlite_database():
    """Check if SQLite database exists and has proper structure"""
    db_path = Path("raah.db")
    
    if not db_path.exists():
        print("❌ Database file raah.db not found")
        return False
    
    try:
        conn = sqlite3.connect("raah.db")
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"Found tables: {tables}")
        
        # Check for vehicles table specifically
        if 'vehicles' in tables:
            cursor.execute("SELECT COUNT(*) FROM vehicles;")
            count = cursor.fetchone()[0]
            print(f"✅ Vehicles table found with {count} records")
            
            if count >= 50000:
                print("🎉 Phase 0 Checkpoint PASSED: 50,000+ vehicles in database")
                return True
            else:
                print(f"❌ Phase 0 Checkpoint FAILED: Only {count} vehicles in database")
                return False
        else:
            print("❌ Vehicles table not found")
            return False
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def generate_seed_data_summary():
    """Generate a summary of what seed data should contain"""
    expected_files = [
        "simulator/data/vehicles_seed.json",
        "simulator/data/checkpoints.json", 
        "simulator/data/zones.json",
        "simulator/data/historical_incidents.json",
        "simulator/data/vehicle_exemptions.json"
    ]
    
    print("\n=== Expected Seed Data Files ===")
    for file_path in expected_files:
        path = Path(file_path)
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                print(f"✅ {file_path}: {len(data)} records")
            except Exception as e:
                print(f"❌ {file_path}: Error reading - {e}")
        else:
            print(f"❌ {file_path}: Not found")

def main():
    """Main verification function"""
    print("🚀 RAAH SQLite Database Verification")
    print("=" * 50)
    
    # Check if database exists and has data
    db_success = check_sqlite_database()
    
    # Check seed data files
    generate_seed_data_summary()
    
    print("\n" + "=" * 50)
    if db_success:
        print("✅ Phase 0 Implementation Complete!")
        print("Ready for Phase 1: Simulator implementation")
    else:
        print("❌ Phase 0 Implementation Needs Attention")
        print("Run the following commands to complete setup:")
        print("1. python scripts/generate_seed_data.py")
        print("2. python scripts/seed_db.py")
        print("3. python verify_sqlite_complete.py")
    
    return db_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)