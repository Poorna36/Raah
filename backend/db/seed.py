"""
Database seeding and initialization for RAAH Highway Monitoring System
Handles table creation and initial data loading
"""

import argparse
import logging
from .session import create_tables, get_engine
from .models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """
    Initialize the database by creating all tables.
    This is the main entry point for database setup.
    """
    try:
        logger.info("Creating database tables...")
        create_tables()
        logger.info("Database tables created successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        return False


def reset_database():
    """
    Reset the database by dropping and recreating all tables.
    Use with caution - this will delete all data!
    """
    try:
        logger.warning("Resetting database - this will delete all data!")
        from .session import drop_tables
        drop_tables()
        create_tables()
        logger.info("Database reset completed successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        return False


def check_connection():
    """
    Test database connection and return engine info.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute("SELECT version()")
            version = result.scalar()
            logger.info(f"Database connection successful: {version}")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def main():
    """
    Main entry point for the seed script.
    Can be run as: python -m backend.db.seed
    """
    parser = argparse.ArgumentParser(description="RAAH Database Seeding Tool")
    parser.add_argument(
        "--reset", 
        action="store_true", 
        help="Reset database (drop and recreate all tables)"
    )
    parser.add_argument(
        "--check", 
        action="store_true", 
        help="Check database connection only"
    )
    
    args = parser.parse_args()
    
    if args.check:
        success = check_connection()
        return 0 if success else 1
    
    if args.reset:
        success = reset_database()
    else:
        success = init_database()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())