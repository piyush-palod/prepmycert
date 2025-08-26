#!/usr/bin/env python3
"""
Rollback script for Azure integration migration.
Use this if you need to undo the migration changes.

WARNING: This will remove columns and potentially lose data!
Only use if you need to revert the changes.

Usage: python rollback_migration.py
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

# Create minimal app for rollback
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def confirm_rollback():
    """Ask user to confirm rollback operation"""
    print("⚠️  WARNING: This will remove database columns and potentially lose data!")
    print("\nThis rollback will:")
    print("- Remove 'azure_folder_name' column from test_packages table")
    print("- Remove 'failed_login_attempts' and 'last_failed_login' columns from users table")
    print("- Drop 'otp_tokens' table (if it was created by migration)")
    print("\nDATA LOSS RISK:")
    print("- Any configured Azure folder names will be lost")
    print("- OTP authentication data will be lost")
    print("- Failed login attempt tracking will be lost")
    
    response = input("\nAre you absolutely sure you want to proceed? (type 'ROLLBACK' to confirm): ")
    return response == 'ROLLBACK'

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

def rollback_test_packages():
    """Remove azure_folder_name column from test_packages"""
    print("Rolling back test_packages table...")
    
    if check_column_exists('test_packages', 'azure_folder_name'):
        try:
            with db.engine.connect() as conn:
                # Drop index first
                conn.execute(db.text("DROP INDEX IF EXISTS idx_test_packages_azure_folder"))
                
                # Drop column
                conn.execute(db.text("ALTER TABLE test_packages DROP COLUMN azure_folder_name"))
                conn.commit()
            print("✓ Removed azure_folder_name column and index")
            return True
        except Exception as e:
            print(f"✗ Error removing azure_folder_name: {e}")
            return False
    else:
        print("✓ azure_folder_name column not present")
        return True

def rollback_users():
    """Remove new columns from users table"""
    print("Rolling back users table...")
    
    columns_to_remove = ['failed_login_attempts', 'last_failed_login']
    
    for column in columns_to_remove:
        if check_column_exists('users', column):
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text(f"ALTER TABLE users DROP COLUMN {column}"))
                    conn.commit()
                print(f"✓ Removed users.{column}")
            except Exception as e:
                print(f"✗ Error removing users.{column}: {e}")
                return False
        else:
            print(f"✓ users.{column} not present")
    
    return True

def rollback_otp_tokens():
    """Drop otp_tokens table"""
    print("Rolling back otp_tokens table...")
    
    if check_table_exists('otp_tokens'):
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text("DROP TABLE otp_tokens"))
                conn.commit()
            print("✓ Dropped otp_tokens table")
            return True
        except Exception as e:
            print(f"✗ Error dropping otp_tokens table: {e}")
            return False
    else:
        print("✓ otp_tokens table not present")
        return True

def verify_rollback():
    """Verify rollback was successful"""
    print("Verifying rollback...")
    
    checks = [
        ("test_packages", "azure_folder_name"),
        ("users", "failed_login_attempts"),
        ("users", "last_failed_login"),
    ]
    
    all_good = True
    for table, column in checks:
        if not check_column_exists(table, column):
            print(f"✓ {table}.{column} successfully removed")
        else:
            print(f"✗ {table}.{column} still exists")
            all_good = False
    
    # Check otp_tokens table
    if not check_table_exists('otp_tokens'):
        print("✓ otp_tokens table successfully removed")
    else:
        print("✗ otp_tokens table still exists")
        all_good = False
    
    return all_good

def main():
    """Main rollback function"""
    print("Migration Rollback Script")
    print("=" * 30)
    print(f"Started at: {datetime.now()}")
    print()
    
    # Confirm with user
    if not confirm_rollback():
        print("Rollback cancelled by user")
        sys.exit(0)
    
    with app.app_context():
        print("\nStarting rollback process...")
        
        # Step 1: Rollback test_packages
        if not rollback_test_packages():
            print("Rollback failed at test_packages")
            sys.exit(1)
        
        # Step 2: Rollback users
        if not rollback_users():
            print("Rollback failed at users")
            sys.exit(1)
        
        # Step 3: Rollback otp_tokens
        if not rollback_otp_tokens():
            print("Rollback failed at otp_tokens")
            sys.exit(1)
        
        # Step 4: Verify rollback
        if not verify_rollback():
            print("Rollback verification failed")
            sys.exit(1)
    
    print("\n" + "="*30)
    print("✓ ROLLBACK COMPLETED SUCCESSFULLY")
    print("="*30)
    print("\nThe database has been reverted to its previous state.")
    print("You may need to restart your application.")

if __name__ == '__main__':
    main()