#!/usr/bin/env python3
"""
SQLite Setup Script for RAAH Highway Monitoring System
Executes the complete infrastructure and seed data setup for hackathon demo
"""

import subprocess
import sys
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_python_script(script_path, description):
    """Run a Python script and handle errors"""
    logger.info(f"Running: {description}")
    try:
        # Use python command, will work if Python is available
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True, cwd=Path.cwd())
        if result.returncode != 0:
            logger.error(f"Script failed: {script_path}")
            logger.error(f"Error: {result.stderr}")
            return False
        logger.info(f"✅ {description} completed successfully")
        if result.stdout:
            logger.info(f"Output: {result.stdout.strip()}")
        return True
    except Exception as e:
        logger.error(f"Exception running script: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are available"""
    logger.info("Checking dependencies...")
    
    # Check if we can import required modules
    try:
        import sqlalchemy
        logger.info("✅ SQLAlchemy available")
    except ImportError:
        logger.error("❌ SQLAlchemy not available")
        return False
    
    try:
        import requests
        logger.info("✅ Requests available")
    except ImportError:
        logger.warning("⚠️  Requests not available (needed for OSM data)")
    
    return True

def create_database():
    """Create SQLite database"""
    logger.info("Creating SQLite database...")
    
    try:
        # Import and create database
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from backend.db.session import create_tables
        
        create_tables()
        logger.info("✅ Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Database creation failed: {e}")
        return False

def generate_seed_data():
    """Generate seed data files"""
    logger.info("Generating seed data...")
    
    script_path = "scripts/generate_seed_data.py"
    if not Path(script_path).exists():
        logger.error(f"Seed data script not found: {script_path}")
        return False
    
    return run_python_script(script_path, "Generate seed data")

def fetch_osm_data():
    """Fetch OSM data (optional)"""
    logger.info("Fetching OSM data...")
    
    script_path = "scripts/fetch_osm_data.py"
    if not Path(script_path).exists():
        logger.error(f"OSM data script not found: {script_path}")
        return False
    
    success = run_python_script(script_path, "Fetch OSM NH-275 data")
    if not success:
        logger.warning("OSM data fetch failed, but continuing with setup")
    
    return True

def seed_database():
    """Seed database with generated data"""
    logger.info("Seeding database...")
    
    script_path = "scripts/seed_db.py"
    if not Path(script_path).exists():
        logger.error(f"Database seed script not found: {script_path}")
        return False
    
    return run_python_script(script_path, "Seed database with data")

def verify_database():
    """Verify database contents"""
    logger.info("Verifying database contents...")
    
    try:
        # Import and verify
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from backend.db.session import get_engine
        from backend.db.models import Vehicle
        from sqlalchemy.orm import sessionmaker
        
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check vehicle count
        vehicle_count = session.query(Vehicle).count()
        logger.info(f"Vehicle count: {vehicle_count}")
        
        # Show sample vehicles
        sample_vehicles = session.query(Vehicle).limit(3).all()
        logger.info("Sample vehicles:")
        for vehicle in sample_vehicles:
            logger.info(f"  - {vehicle.plate_number} ({vehicle.registered_class}, {vehicle.registration_state})")
        
        session.close()
        
        if vehicle_count >= 50000:
            logger.info(f"✅ Database verification PASSED: {vehicle_count} vehicles found")
            return True
        else:
            logger.error(f"❌ Database verification FAILED: Only {vehicle_count} vehicles found")
            return False
            
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False

def main():
    """Main setup function"""
    logger.info("🚀 Starting RAAH SQLite Setup")
    logger.info("This will set up the SQLite database and generate seed data for the hackathon demo")
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Dependency check failed")
        return False
    
    # Create database
    if not create_database():
        logger.error("Database creation failed")
        return False
    
    # Generate seed data
    if not generate_seed_data():
        logger.error("Seed data generation failed")
        return False
    
    # Fetch OSM data (optional)
    fetch_osm_data()
    
    # Seed database
    if not seed_database():
        logger.error("Database seeding failed")
        return False
    
    # Verify database
    if not verify_database():
        logger.error("Database verification failed")
        return False
    
    logger.info("🎉 Phase 0 Setup completed successfully!")
    logger.info("\nNext steps:")
    logger.info("1. Proceed to Phase 1: Simulator implementation")
    logger.info("2. Check the PROGRESS_LOGBOOK.md for detailed status")
    logger.info("3. Database file: raah.db")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)