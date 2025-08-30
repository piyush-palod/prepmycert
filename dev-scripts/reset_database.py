#!/usr/bin/env python3
"""
Database Reset Script - Fresh Start for Course > Practice Test > Questions Architecture

This script:
1. Drops ALL existing tables
2. Creates fresh tables with new Course > Practice Test > Questions structure
3. Creates initial admin user
4. Provides clean slate for testing new architecture

Usage: python3 dev-scripts/reset_database.py
"""

import os
import sys
import logging
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app import app, db
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def drop_all_tables():
    """Drop all tables in the database"""
    logger.info("🗑️  Dropping all existing tables...")
    try:
        with app.app_context():
            # Get all table names
            result = db.session.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename NOT IN ('spatial_ref_sys')
            """))
            
            tables = [row.tablename for row in result]
            logger.info(f"Found {len(tables)} tables to drop: {', '.join(tables)}")
            
            if tables:
                # Drop all tables with CASCADE to handle foreign keys
                for table in tables:
                    db.session.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                    logger.info(f"✅ Dropped table: {table}")
                    
                # Also drop any sequences that might be left over
                db.session.execute(text("DROP SEQUENCE IF EXISTS users_id_seq CASCADE"))
                db.session.execute(text("DROP SEQUENCE IF EXISTS courses_id_seq CASCADE"))
                db.session.execute(text("DROP SEQUENCE IF EXISTS practice_tests_id_seq CASCADE"))
                db.session.execute(text("DROP SEQUENCE IF EXISTS questions_id_seq CASCADE"))
                
                # Commit the changes
                db.session.commit()
                
            logger.info("🎯 All tables dropped successfully!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error dropping tables: {str(e)}")
        db.session.rollback()
        return False

def verify_database_is_empty():
    """Verify database is clean after dropping tables"""
    logger.info("🔍 Verifying database is clean...")
    try:
        with app.app_context():
            result = db.session.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename NOT IN ('spatial_ref_sys')
            """))
            
            remaining_tables = [row.tablename for row in result]
            
            if remaining_tables:
                logger.warning(f"⚠️  Some tables still exist: {', '.join(remaining_tables)}")
                return False
            else:
                logger.info("✅ Database is completely clean!")
                return True
                
    except Exception as e:
        logger.error(f"❌ Error verifying clean database: {str(e)}")
        return False

def main():
    """Main execution function"""
    logger.info("🚀 Starting database reset for Course > Practice Test > Questions architecture")
    logger.info("=" * 80)
    
    # Step 1: Drop all tables
    if not drop_all_tables():
        logger.error("💥 Failed to drop tables. Exiting.")
        sys.exit(1)
    
    # Step 2: Verify database is clean
    if not verify_database_is_empty():
        logger.error("💥 Database cleanup verification failed. Exiting.")
        sys.exit(1)
    
    logger.info("=" * 80)
    logger.info("🎯 DATABASE RESET COMPLETED SUCCESSFULLY!")
    logger.info("")
    logger.info("📋 What Was Done:")
    logger.info("   ✅ All existing tables dropped")
    logger.info("   ✅ Database is completely clean")
    logger.info("")
    logger.info("🚀 Next Steps:")
    logger.info("   1. Start the application: python3 main.py")
    logger.info("      → Flask will automatically create tables (via db.create_all())")
    logger.info("      → Flask will handle admin user setup (via setup_admin.py logic)")
    logger.info("   2. Login as admin and test course creation: /admin/courses")
    logger.info("   3. Add practice tests and questions")
    logger.info("   4. Test user flow: browse courses → purchase → take practice tests")
    logger.info("")
    logger.info("🗑️  Remember to delete dev-scripts/ folder after testing!")
    logger.info("💡 If you need admin user, run: python3 setup_admin.py")

if __name__ == '__main__':
    main()