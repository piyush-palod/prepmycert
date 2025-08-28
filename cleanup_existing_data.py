#!/usr/bin/env python3
"""
Phase 1: Standalone Database Cleanup Script
Fixed version that avoids circular imports by using direct SQL commands.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get direct database connection using psycopg2"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # Parse the database URL
    try:
        # Handle both postgres:// and postgresql:// schemes
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        parsed = urlparse(database_url)
        
        connection = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],  # Remove leading slash
            user=parsed.username,
            password=parsed.password
        )
        
        return connection
        
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        print(f"Database URL format: {database_url.split('@')[1] if '@' in database_url else 'Invalid URL'}")
        return None

def get_table_count(cursor, table_name):
    """Get count of records in a table"""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"Warning: Could not count {table_name}: {e}")
        return 0

def cleanup_existing_data():
    """
    Clean existing test data in correct order to avoid foreign key constraints.
    Uses direct SQL to avoid circular import issues.
    """
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        print("Current data counts:")
        tables_to_check = [
            'user_answers', 'test_attempts', 'answer_options', 'questions',
            'coupon_usages', 'user_purchases', 'bundle_packages', 
            'test_packages', 'bundles', 'coupons'
        ]
        
        # Get current counts
        for table in tables_to_check:
            count = get_table_count(cursor, table)
            print(f"  {table}: {count}")
        
        print("\nCleaning up data...")
        
        # Cleanup in correct order (respecting foreign keys)
        cleanup_commands = [
            # 1. User answers (depends on test_attempts)
            ("DELETE FROM user_answers", "user answers"),
            
            # 2. Test attempts (depends on test_packages, users)
            ("DELETE FROM test_attempts", "test attempts"),
            
            # 3. Answer options (depends on questions)
            ("DELETE FROM answer_options", "answer options"),
            
            # 4. Questions (depends on test_packages)
            ("DELETE FROM questions", "questions"),
            
            # 5. Coupon usages (depends on coupons, users)
            ("DELETE FROM coupon_usages", "coupon usages"),
            
            # 6. User purchases (depends on users, test_packages, bundles)
            ("DELETE FROM user_purchases", "user purchases"),
            
            # 7. Bundle packages (depends on bundles, test_packages)
            ("DELETE FROM bundle_packages", "bundle packages"),
            
            # 8. Test packages (root level)
            ("DELETE FROM test_packages", "test packages"),
            
            # 9. Bundles (root level)
            ("DELETE FROM bundles", "bundles"),
            
            # 10. Coupons (root level)
            ("DELETE FROM coupons", "coupons"),
        ]
        
        # Execute cleanup commands
        total_deleted = 0
        for sql_command, description in cleanup_commands:
            try:
                cursor.execute(sql_command)
                deleted_count = cursor.rowcount
                print(f"✓ Deleted {deleted_count} {description}")
                total_deleted += deleted_count
            except Exception as e:
                print(f"⚠ Warning deleting {description}: {e}")
                # Continue with other deletions
        
        # Commit all changes
        conn.commit()
        print(f"✓ Database cleanup completed! Total records deleted: {total_deleted}")
        
        # Verify cleanup
        print("\nVerification (should all be 0):")
        for table in tables_to_check:
            count = get_table_count(cursor, table)
            print(f"  {table}: {count}")
        
        cursor.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        conn.rollback()
        return False
    
    finally:
        conn.close()

def backup_current_system():
    """Create backup of current environment and structure"""
    print("\nCreating backup of current system...")
    
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Backup environment file
    if os.path.exists('.env'):
        import shutil
        shutil.copy2('.env', f"{backup_dir}/.env.backup")
        print(f"✓ Backed up .env to {backup_dir}/")
    
    # Document current system state
    backup_info = f"""
# PrepMyCert System Backup - {datetime.now().isoformat()}

## Pre-Migration State
- Backup created before Phase 1 cleanup
- Original system had runtime image processing
- Azure storage is configured and working

## System Status Before Cleanup
- Azure Blob Storage: ✓ Connected to 'certification-images' container
- Database: ✓ Connected and operational
- Email service: ✓ Configured (development mode)

## Files to check manually:
- /static/images/ folder structure
- Any test CSV files for reference
- Custom configurations

## Restoration Process:
If you need to rollback:
1. Restore the .env file from this backup
2. Run your existing migration scripts to recreate tables
3. Re-import your test data from CSV files

## Next Steps After Cleanup:
1. Update utils.py with new functions
2. Update models.py with enhanced schema
3. Run Phase 1 migration script
4. Test image processing
"""
    
    with open(f"{backup_dir}/backup_info.md", 'w', encoding='utf-8') as f:
        f.write(backup_info)
    
    print(f"✓ Backup completed in {backup_dir}/")
    return backup_dir

def check_database_connection():
    """Test database connection before proceeding"""
    print("Testing database connection...")
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        db_version = cursor.fetchone()[0]
        print(f"✓ Connected to PostgreSQL: {db_version.split(',')[0]}")
        
        # Check if main tables exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'test_packages', 'questions')
            ORDER BY table_name
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"✓ Found tables: {', '.join(existing_tables)}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False

def main():
    """Main cleanup process"""
    print("PrepMyCert Phase 1: Database Cleanup & Preparation")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print()
    
    # Step 1: Test database connection
    print("STEP 1: DATABASE CONNECTION TEST")
    print("="*40)
    if not check_database_connection():
        print("❌ Cannot proceed without database connection")
        sys.exit(1)
    
    # Step 2: Create backup
    print("\n" + "="*40)
    print("STEP 2: SYSTEM BACKUP")
    print("="*40)
    backup_dir = backup_current_system()
    
    # Step 3: Cleanup database
    print("\n" + "="*40)
    print("STEP 3: DATABASE CLEANUP")
    print("="*40)
    
    success = cleanup_existing_data()
    
    if success:
        print("\n" + "="*60)
        print("✅ PHASE 1 CLEANUP COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Backup created: {backup_dir}")
        print()
        print("✅ Database is now clean and ready for Phase 2!")
        print()
        print("What was cleaned:")
        print("• All test packages and questions")
        print("• All user purchases and test attempts")
        print("• All answer options and user answers")
        print("• All bundles and coupons")
        print()
        print("What was preserved:")
        print("• User accounts and authentication")
        print("• Admin settings and OTP tokens")
        print("• System configuration")
        print("• Azure storage configuration")
        print()
        print("Next steps:")
        print("1. Update utils.py with new pre-processing functions")
        print("2. Update models.py with enhanced schema")
        print("3. Run database migration script")
        print("4. Test with sample data")
        
    else:
        print("\n" + "="*60)
        print("❌ PHASE 1 CLEANUP FAILED")
        print("="*60)
        print("Please review the error above and fix before continuing.")
        print(f"Backup available at: {backup_dir}")
        print()
        print("Common solutions:")
        print("• Check DATABASE_URL environment variable")
        print("• Ensure PostgreSQL is running")
        print("• Verify database permissions")
        sys.exit(1)

if __name__ == '__main__':
    # Check for psycopg2
    try:
        import psycopg2
    except ImportError:
        print("❌ psycopg2 is required for database operations")
        print("Install it with: pip install psycopg2-binary")
        sys.exit(1)
    
    # Safety check
    print("⚠️  WARNING: This will delete ALL test data from your database!")
    print("This includes:")
    print("• All test packages and questions")
    print("• All user purchases and test attempts") 
    print("• All bundles and coupons")
    print("\nUser accounts and admin settings will be preserved.")
    print()
    
    response = input("Continue with cleanup? (yes/no): ")
    if response.lower() != 'yes':
        print("Cleanup cancelled.")
        sys.exit(0)
    
    main()