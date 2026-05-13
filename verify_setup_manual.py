"""
Manual verification guide for RAAH SQLite setup
This script shows what should be present after successful setup
"""

import os
import json
from pathlib import Path

def check_file_structure():
    """Check if all required files exist"""
    print("🔍 Checking file structure...")
    
    required_files = [
        "backend/db/models.py",
        "backend/db/session.py", 
        "backend/db/seed.py",
        "scripts/generate_seed_data.py",
        "scripts/fetch_osm_data.py",
        "scripts/seed_db.py",
        "backend/requirements.txt",
        "scripts/requirements.txt"
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            all_exist = False
    
    return all_exist

def check_database_file():
    """Check if SQLite database exists"""
    print("\n🔍 Checking database file...")
    
    db_path = Path("raah.db")
    if db_path.exists():
        size = db_path.stat().st_size
        print(f"✅ raah.db exists ({size:,} bytes)")
        return True
    else:
        print("❌ raah.db not found")
        return False

def check_seed_data_files():
    """Check if seed data files exist"""
    print("\n🔍 Checking seed data files...")
    
    seed_files = [
        "simulator/data/vehicles_seed.json",
        "simulator/data/checkpoints.json",
        "simulator/data/zones.json", 
        "simulator/data/historical_incidents.json",
        "simulator/data/vehicle_exemptions.json"
    ]
    
    all_exist = True
    total_vehicles = 0
    
    for file_path in seed_files:
        path = Path(file_path)
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                count = len(data)
                print(f"✅ {file_path}: {count:,} records")
                
                if 'vehicles' in file_path:
                    total_vehicles = count
                    
            except Exception as e:
                print(f"⚠️  {file_path}: Error reading - {e}")
        else:
            print(f"❌ {file_path}: Not found")
            all_exist = False
    
    return all_exist, total_vehicles

def show_setup_instructions():
    """Show setup instructions"""
    print("\n" + "="*60)
    print("🚀 RAAH SQLite Setup Instructions")
    print("="*60)
    
    print("\n1. Install dependencies:")
    print("   pip install -r backend/requirements.txt")
    print("   pip install -r scripts/requirements.txt")
    
    print("\n2. Generate seed data:")
    print("   python scripts/generate_seed_data.py")
    
    print("\n3. Create database and tables:")
    print("   python -m backend.db.seed")
    
    print("\n4. Seed database:")
    print("   python scripts/seed_db.py")
    
    print("\n5. Verify setup:")
    print("   python verify_sqlite_final.py")
    
    print("\n" + "="*60)
    print("Expected Results:")
    print("- SQLite database: raah.db")
    print("- 50,000+ vehicle records")
    print("- 12 checkpoints")
    print("- 11 zones")
    print("- Historical incident data")
    print("="*60)

def main():
    """Main verification function"""
    print("🎯 RAAH Phase 0 SQLite Setup Verification")
    print("="*60)
    
    # Check file structure
    files_ok = check_file_structure()
    
    # Check database
    db_exists = check_database_file()
    
    # Check seed data
    seed_ok, vehicle_count = check_seed_data_files()
    
    print("\n" + "="*60)
    print("📊 Summary:")
    
    if files_ok:
        print("✅ All required files present")
    else:
        print("❌ Missing required files")
    
    if db_exists:
        print("✅ Database file exists")
    else:
        print("❌ Database file missing")
    
    if seed_ok and vehicle_count >= 50000:
        print(f"✅ Seed data ready ({vehicle_count:,} vehicles)")
    elif seed_ok:
        print(f"⚠️  Seed data incomplete ({vehicle_count:,} vehicles)")
    else:
        print("❌ Seed data files missing")
    
    # Show setup instructions
    show_setup_instructions()
    
    # Final status
    print("\n" + "="*60)
    if files_ok and db_exists and seed_ok and vehicle_count >= 50000:
        print("🎉 Phase 0 Setup Ready!")
        print("Run verification script when Python is available:")
        print("python verify_sqlite_final.py")
    else:
        print("⚠️  Setup incomplete - follow instructions above")
    
    return files_ok and db_exists and seed_ok and vehicle_count >= 50000

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)