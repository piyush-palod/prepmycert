#!/usr/bin/env python3
"""
Comprehensive migration script to update database schema for Azure integration
and missing User model fields.

This script will:
1. Add missing User table columns (failed_login_attempts, last_failed_login)
2. Add azure_folder_name column to TestPackage
3. Create OTPToken table if it doesn't exist
4. Verify all changes

Usage: python migrate_azure_folders_complete.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import without triggering app initialization
os.environ['SKIP_APP_INIT'] = '1'
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Create minimal app for migration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    try:
        with db.engine.connect() as conn:
            result = conn.execute(db.text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}' 
                AND column_name = '{column_name}'
            """))
            return result.fetchone() is not None
    except Exception as e:
        print(f"Error checking column {table_name}.{column_name}: {e}")
        return False

def check_table_exists(table_name):
    """Check if a table exists"""
    try:
        with db.engine.connect() as conn:
            result = conn.execute(db.text(f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = '{table_name}'
            """))
            return result.fetchone() is not None
    except Exception as e:
        print(f"Error checking table {table_name}: {e}")
        return False

def migrate_user_table():
    """Add missing columns to users table"""
    print("Migrating users table...")
    
    migrations = [
        ("failed_login_attempts", "INTEGER DEFAULT 0"),
        ("last_failed_login", "TIMESTAMP"),
    ]
    
    for column_name, column_def in migrations:
        if not check_column_exists('users', column_name):
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text(f"""
                        ALTER TABLE users 
                        ADD COLUMN {column_name} {column_def}
                    """))
                    conn.commit()
                print(f"✓ Added users.{column_name}")
            except Exception as e:
                print(f"✗ Error adding users.{column_name}: {e}")
                return False
        else:
            print(f"✓ users.{column_name} already exists")
    
    return True

def migrate_test_packages_table():
    """Add azure_folder_name column to test_packages table"""
    print("Migrating test_packages table...")
    
    if not check_column_exists('test_packages', 'azure_folder_name'):
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text("""
                    ALTER TABLE test_packages 
                    ADD COLUMN azure_folder_name VARCHAR(100)
                """))
                
                # Create index for better performance
                conn.execute(db.text("""
                    CREATE INDEX IF NOT EXISTS idx_test_packages_azure_folder 
                    ON test_packages(azure_folder_name)
                """))
                
                conn.commit()
            print("✓ Added test_packages.azure_folder_name with index")
            return True
        except Exception as e:
            print(f"✗ Error adding azure_folder_name: {e}")
            return False
    else:
        print("✓ test_packages.azure_folder_name already exists")
        return True

def create_otp_tokens_table():
    """Create otp_tokens table if it doesn't exist"""
    print("Checking otp_tokens table...")
    
    if not check_table_exists('otp_tokens'):
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text("""
                    CREATE TABLE otp_tokens (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        token VARCHAR(10) NOT NULL,
                        purpose VARCHAR(50) NOT NULL,
                        is_used BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        ip_address VARCHAR(45)
                    )
                """))
                
                # Create indexes
                conn.execute(db.text("""
                    CREATE INDEX idx_otp_tokens_token ON otp_tokens(token)
                """))
                conn.execute(db.text("""
                    CREATE INDEX idx_otp_tokens_user_purpose ON otp_tokens(user_id, purpose)
                """))
                
                conn.commit()
            print("✓ Created otp_tokens table with indexes")
        except Exception as e:
            print(f"✗ Error creating otp_tokens table: {e}")
            return False
    else:
        print("✓ otp_tokens table already exists")
    
    return True

def suggest_folder_names():
    """Suggest Azure folder names for existing packages"""
    try:
        with app.app_context():
            # Query test packages directly without using models
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT id, title FROM test_packages WHERE is_active = true"))
                packages = result.fetchall()
            
            if not packages:
                print("No active test packages found")
                return
            
            print("\n" + "="*60)
            print("SUGGESTED AZURE FOLDER NAMES FOR EXISTING PACKAGES")
            print("="*60)
            print("You can use these suggestions to manually set folder names via admin interface:")
            print()
            
            for package_id, title in packages:
                # Generate suggested folder name from title
                suggested = title.lower()
                suggested = suggested.replace(' ', '-')
                suggested = ''.join(c for c in suggested if c.isalnum() or c == '-')
                suggested = '-'.join(filter(None, suggested.split('-')))  # Remove empty parts
                
                print(f"Package ID {package_id}: {title}")
                print(f"Suggested folder: {suggested}")
                print(f"Admin can set this via: /admin/packages/{package_id}/edit")
                print("-" * 40)
            
            print("\nNOTE: These are suggestions only. You should:")
            print("1. Verify the folder names match your Azure Blob Storage structure")
            print("2. Set them via the admin interface after the migration")
            print("3. Test image loading after configuration")
            
    except Exception as e:
        print(f"✗ Error generating suggestions: {e}")

def verify_migration():
    """Verify the migration was successful"""
    print("Verifying migration...")
    
    checks = [
        ("users", "failed_login_attempts"),
        ("users", "last_failed_login"),
        ("test_packages", "azure_folder_name"),
    ]
    
    all_good = True
    for table, column in checks:
        if check_column_exists(table, column):
            print(f"✓ {table}.{column} exists")
        else:
            print(f"✗ {table}.{column} missing")
            all_good = False
    
    # Check otp_tokens table
    if check_table_exists('otp_tokens'):
        print("✓ otp_tokens table exists")
    else:
        print("✗ otp_tokens table missing")
        all_good = False
    
    if all_good:
        # Show statistics
        try:
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT COUNT(*) FROM test_packages"))
                total_packages = result.fetchone()[0]
                
                result = conn.execute(db.text("""
                    SELECT COUNT(*) FROM test_packages 
                    WHERE azure_folder_name IS NOT NULL AND azure_folder_name != ''
                """))
                configured_packages = result.fetchone()[0]
                
                print(f"✓ Total packages: {total_packages}")
                print(f"✓ Packages with Azure folders configured: {configured_packages}")
                print(f"✓ Packages pending configuration: {total_packages - configured_packages}")
        except Exception as e:
            print(f"Warning: Could not get statistics: {e}")
    
    return all_good

def main():
    """Main migration function"""
    print("Comprehensive Database Migration Script")
    print("=" * 50)
    print(f"Started at: {datetime.now()}")
    print()
    
    with app.app_context():
        # Step 1: Migrate users table
        print("Step 1: Migrating users table...")
        if not migrate_user_table():
            print("Migration failed at Step 1")
            sys.exit(1)
        
        # Step 2: Migrate test_packages table
        print("\nStep 2: Migrating test_packages table...")
        if not migrate_test_packages_table():
            print("Migration failed at Step 2")
            sys.exit(1)
        
        # Step 3: Create OTP tokens table
        print("\nStep 3: Creating OTP tokens table...")
        if not create_otp_tokens_table():
            print("Migration failed at Step 3")
            sys.exit(1)
        
        # Step 4: Verify migration
        print("\nStep 4: Verifying migration...")
        if not verify_migration():
            print("Migration verification failed")
            sys.exit(1)
        
        # Step 5: Provide suggestions
        print("\nStep 5: Generating folder name suggestions...")
        suggest_folder_names()
    
    print("\n" + "="*50)
    print("✓ MIGRATION COMPLETED SUCCESSFULLY")
    print("="*50)
    print("\nNext steps:")
    print("1. Restart your application to pick up the schema changes")
    print("2. Use the admin interface to set Azure folder names for each package")
    print("3. Verify your Azure Blob Storage has the corresponding folders")
    print("4. Test image loading after configuration")
    print("5. Proceed with Phase 2 of the Azure integration")

if __name__ == '__main__':
    main()