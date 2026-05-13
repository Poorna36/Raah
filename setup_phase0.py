#!/usr/bin/env python3
"""
Phase 0 Setup Script for RAAH Highway Monitoring System
Executes the complete infrastructure and seed data setup
"""

import subprocess
import sys
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, description, cwd=None):
    """Run a shell command and handle errors"""
    logger.info(f"Running: {description}")
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Command failed: {command}")
            logger.error(f"Error: {result.stderr}")
            return False
        logger.info(f"✅ {description} completed successfully")
        return True
    except Exception as e:
        logger.error(f"Exception running command: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are available"""
    logger.info("Checking dependencies...")
    
    # Check Python
    if not run_command("python --version", "Check Python version"):
        return False
    
    # Check PostgreSQL
    if not run_command("psql --version", "Check PostgreSQL client"):
        logger.warning("PostgreSQL client not found. Please install PostgreSQL.")
        return False
    
    return True

def setup_database():
    """Set up PostgreSQL database"""
    logger.info("Setting up PostgreSQL database...")
    
    # Create database if it doesn't exist
    commands = [
        ("createdb raah", "Create raah database"),
        ("psql raah -c \"SELECT version();\"", "Test database connection")
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            logger.error("Database setup failed")
            return False
    
    return True

def install_backend_dependencies():
    """Install backend dependencies"""
    logger.info("Installing backend dependencies...")
    
    backend_dir = Path("backend")
    if not backend_dir.exists():
        logger.error("Backend directory not found")
        return False
    
    # Create virtual environment
    if not run_command("python -m venv venv", "Create virtual environment", cwd=backend_dir):
        return False
    
    # Activate virtual environment and install requirements
    if sys.platform == "win32":
        activate_cmd = ".\\venv\\Scripts\\activate"
    else:
        activate_cmd = "source venv/bin/activate"
    
    install_cmd = f"{activate_cmd} && pip install -r requirements.txt"
    if not run_command(install_cmd, "Install backend requirements", cwd=backend_dir):
        return False
    
    return True

def generate_seed_data():
    """Generate seed data files"""
    logger.info("Generating seed data...")
    
    # Generate vehicle and related data
    if not run_command("python scripts/generate_seed_data.py", "Generate seed data"):
        return False
    
    # Fetch OSM data
    if not run_command("python scripts/fetch_osm_data.py", "Fetch OSM NH-275 data"):
        logger.warning("OSM data fetch failed, but continuing with setup")
    
    return True

def create_database_tables():
    """Create database tables"""
    logger.info("Creating database tables...")
    
    backend_dir = Path("backend")
    
    # Set PYTHONPATH to include project root
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    
    # Create tables using the seed script
    cmd = "python -m backend.db.seed"
    if not run_command(cmd, "Create database tables", cwd=backend_dir):
        return False
    
    return True

def seed_database():
    """Seed database with generated data"""
    logger.info("Seeding database...")
    
    # Set PYTHONPATH to include project root
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    
    # Run the database seeding script
    if not run_command("python scripts/seed_db.py", "Seed database with data"):
        return False
    
    return True

def verify_database():
    """Verify database contents"""
    logger.info("Verifying database contents...")
    
    # Check vehicle count
    result = subprocess.run(
        "psql raah -c \"SELECT count(*) FROM vehicles;\"",
        shell=True, capture_output=True, text=True
    )
    
    if result.returncode != 0:
        logger.error("Failed to verify database")
        return False
    
    # Extract count from output
    output_lines = result.stdout.strip().split('\n')
    for line in output_lines:
        if line.strip().isdigit():
            count = int(line.strip())
            if count >= 50000:
                logger.info(f"✅ Database verification PASSED: {count} vehicles found")
                return True
            else:
                logger.error(f"❌ Database verification FAILED: Only {count} vehicles found (expected 50,000+)")
                return False
    
    logger.error("Could not parse vehicle count from database output")
    return False

def main():
    """Main setup function"""
    logger.info("🚀 Starting RAAH Phase 0 Setup")
    logger.info("This will set up the database and generate seed data for the RAAH system")
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Dependency check failed")
        return False
    
    # Set up database
    if not setup_database():
        logger.error("Database setup failed")
        return False
    
    # Install backend dependencies
    if not install_backend_dependencies():
        logger.error("Backend dependency installation failed")
        return False
    
    # Generate seed data
    if not generate_seed_data():
        logger.error("Seed data generation failed")
        return False
    
    # Create database tables
    if not create_database_tables():
        logger.error("Database table creation failed")
        return False
    
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
    logger.info("1. Start PostgreSQL and Redis services")
    logger.info("2. Proceed to Phase 1: Simulator implementation")
    logger.info("3. Check the PROGRESS_LOGBOOK.md for detailed status")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)