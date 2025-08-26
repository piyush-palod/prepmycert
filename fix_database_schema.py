#!/usr/bin/env python3
"""
Complete database schema migration script.
This script will inspect your current database and add all missing columns
to match the updated models.

Usage: python fix_database_schema.py
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

def get_table_columns(table_name):
    """Get all columns for a table"""
    try:
        with db.engine.connect() as conn:
            result = conn.execute(db.text(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """))
            return {row[0]: {'type': row[1], 'nullable': row[2], 'default': row[3]} 
                    for row in result.fetchall()}
    except Exception as e:
        print(f"Error getting columns for {table_name}: {e}")
        return {}

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

def inspect_current_schema():
    """Inspect current database schema"""
    print("Inspecting current database schema...")
    
    tables_to_check = ['users', 'test_packages', 'questions', 'answer_options', 
                       'user_purchases', 'test_attempts', 'user_answers', 'coupons', 
                       'bundles', 'bundle_packages', 'coupon_usages', 'otp_tokens']
    
    schema_info = {}
    for table in tables_to_check:
        if check_table_exists(table):
            columns = get_table_columns(table)
            schema_info[table] = columns
            print(f"✓ Found table '{table}' with {len(columns)} columns")
        else:
            schema_info[table] = None
            print(f"✗ Table '{table}' does not exist")
    
    return schema_info

def get_expected_schema():
    """Define the expected schema based on the updated models"""
    return {
        'users': {
            'id': {'type': 'integer', 'nullable': 'NO'},
            'email': {'type': 'character varying', 'nullable': 'NO'},
            'first_name': {'type': 'character varying', 'nullable': 'NO'},
            'last_name': {'type': 'character varying', 'nullable': 'NO'},
            'password_hash': {'type': 'character varying', 'nullable': 'YES'},
            'is_admin': {'type': 'boolean', 'nullable': 'YES'},
            'is_email_verified': {'type': 'boolean', 'nullable': 'YES'},
            'is_locked': {'type': 'boolean', 'nullable': 'YES'},
            'failed_login_attempts': {'type': 'integer', 'nullable': 'YES'},
            'last_failed_login': {'type': 'timestamp without time zone', 'nullable': 'YES'},
            'created_at': {'type': 'timestamp without time zone', 'nullable': 'YES'},
        },
        'test_packages': {
            'id': {'type': 'integer', 'nullable': 'NO'},
            'title': {'type': 'character varying', 'nullable': 'NO'},
            'description': {'type': 'text', 'nullable': 'NO'},
            'price': {'type': 'double precision', 'nullable': 'NO'},
            'is_active': {'type': 'boolean', 'nullable': 'YES'},
            'created_at': {'type': 'timestamp without time zone', 'nullable': 'YES'},
            'created_by': {'type': 'integer', 'nullable': 'NO'},
            'azure_folder_name': {'type': 'character varying', 'nullable': 'YES'},
        },
        'otp_tokens': {
            'id': {'type': 'integer', 'nullable': 'NO'},
            'user_id': {'type': 'integer', 'nullable': 'NO'},
            'token': {'type': 'character varying', 'nullable': 'NO'},
            'purpose': {'type': 'character varying', 'nullable': 'NO'},
            'is_used': {'type': 'boolean', 'nullable': 'YES'},
            'created_at': {'type': 'timestamp without time zone', 'nullable': 'YES'},
            'expires_at': {'type': 'timestamp without time zone', 'nullable': 'NO'},
            'ip_address': {'type': 'character varying', 'nullable': 'YES'},
        }
    }

def add_missing_columns(current_schema, expected_schema):
    """Add missing columns to existing tables"""
    print("\nAdding missing columns...")
    
    # Column type mappings for SQL
    type_mapping = {
        'character varying': 'VARCHAR(255)',
        'text': 'TEXT',
        'integer': 'INTEGER',
        'double precision': 'DOUBLE PRECISION',
        'boolean': 'BOOLEAN',
        'timestamp without time zone': 'TIMESTAMP'
    }
    
    migrations_applied = []
    
    for table_name, expected_columns in expected_schema.items():
        if current_schema.get(table_name) is None:
            print(f"Skipping {table_name} - table doesn't exist (will create later)")
            continue
            
        current_columns = current_schema[table_name]
        
        for column_name, column_info in expected_columns.items():
            if column_name not in current_columns:
                # Determine SQL column definition
                sql_type = type_mapping.get(column_info['type'], 'VARCHAR(255)')
                
                # Add default values for certain columns
                if column_name == 'failed_login_attempts':
                    sql_def = f"{sql_type} DEFAULT 0"
                elif column_name == 'is_admin':
                    sql_def = f"{sql_type} DEFAULT FALSE"
                elif column_name == 'is_active':
                    sql_def = f"{sql_type} DEFAULT TRUE"
                elif column_name == 'is_email_verified':
                    sql_def = f"{sql_type} DEFAULT FALSE"
                elif column_name == 'is_locked':
                    sql_def = f"{sql_type} DEFAULT FALSE"
                elif column_name == 'is_used':
                    sql_def = f"{sql_type} DEFAULT FALSE"
                elif column_name == 'created_by':
                    # For created_by, we need to handle the foreign key constraint
                    # First add the column, then we'll set a default value
                    sql_def = f"{sql_type}"
                else:
                    sql_def = sql_type
                
                try:
                    with db.engine.connect() as conn:
                        conn.execute(db.text(f"""
                            ALTER TABLE {table_name} 
                            ADD COLUMN {column_name} {sql_def}
                        """))
                        conn.commit()
                    
                    print(f"✓ Added {table_name}.{column_name}")
                    migrations_applied.append(f"{table_name}.{column_name}")
                    
                    # Special handling for created_by - set to first admin user or 1
                    if column_name == 'created_by':
                        try:
                            with db.engine.connect() as conn:
                                # Try to find first admin user
                                result = conn.execute(db.text("""
                                    SELECT id FROM users WHERE is_admin = true LIMIT 1
                                """))
                                admin_user = result.fetchone()
                                
                                if admin_user:
                                    admin_id = admin_user[0]
                                else:
                                    # Use first user or default to 1
                                    result = conn.execute(db.text("SELECT id FROM users LIMIT 1"))
                                    first_user = result.fetchone()
                                    admin_id = first_user[0] if first_user else 1
                                
                                # Update all existing records
                                conn.execute(db.text(f"""
                                    UPDATE {table_name} 
                                    SET created_by = {admin_id} 
                                    WHERE created_by IS NULL
                                """))
                                conn.commit()
                            
                            print(f"  ✓ Set default created_by = {admin_id} for existing records")
                            
                        except Exception as e:
                            print(f"  ⚠ Warning: Could not set default created_by: {e}")
                    
                except Exception as e:
                    print(f"✗ Error adding {table_name}.{column_name}: {e}")
                    return False, migrations_applied
    
    return True, migrations_applied

def create_missing_tables(current_schema):
    """Create missing tables"""
    print("\nCreating missing tables...")
    
    if current_schema.get('otp_tokens') is None:
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
                conn.execute(db.text("CREATE INDEX idx_otp_tokens_token ON otp_tokens(token)"))
                conn.execute(db.text("CREATE INDEX idx_otp_tokens_user_purpose ON otp_tokens(user_id, purpose)"))
                conn.commit()
            
            print("✓ Created otp_tokens table with indexes")
            return True
            
        except Exception as e:
            print(f"✗ Error creating otp_tokens table: {e}")
            return False
    else:
        print("✓ otp_tokens table already exists")
        return True

def create_missing_indexes():
    """Create missing indexes for performance"""
    print("\nCreating missing indexes...")
    
    indexes = [
        ("idx_users_email", "users", "email"),
        ("idx_test_packages_azure_folder", "test_packages", "azure_folder_name"),
        ("idx_questions_test_package", "questions", "test_package_id"),
        ("idx_questions_domain", "questions", "domain"),
        ("idx_coupons_code", "coupons", "code"),
    ]
    
    for index_name, table_name, column_name in indexes:
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table_name}({column_name})
                """))
                conn.commit()
            print(f"✓ Created index {index_name}")
        except Exception as e:
            print(f"⚠ Warning: Could not create index {index_name}: {e}")

def verify_final_schema():
    """Verify the final schema is correct"""
    print("\nVerifying final schema...")
    
    expected_schema = get_expected_schema()
    current_schema = inspect_current_schema()
    
    all_good = True
    for table_name, expected_columns in expected_schema.items():
        if current_schema.get(table_name) is None:
            print(f"✗ Table {table_name} still missing")
            all_good = False
            continue
            
        current_columns = current_schema[table_name]
        
        for column_name in expected_columns:
            if column_name in current_columns:
                print(f"✓ {table_name}.{column_name} exists")
            else:
                print(f"✗ {table_name}.{column_name} missing")
                all_good = False
    
    return all_good

def main():
    """Main migration function"""
    print("Complete Database Schema Migration")
    print("=" * 50)
    print(f"Started at: {datetime.now()}")
    print()
    
    with app.app_context():
        # Step 1: Inspect current schema
        current_schema = inspect_current_schema()
        
        # Step 2: Add missing columns
        print("\n" + "="*50)
        success, migrations = add_missing_columns(current_schema, get_expected_schema())
        if not success:
            print("Migration failed while adding columns")
            sys.exit(1)
        
        # Step 3: Create missing tables
        print("\n" + "="*50)
        if not create_missing_tables(current_schema):
            print("Migration failed while creating tables")
            sys.exit(1)
        
        # Step 4: Create indexes
        print("\n" + "="*50)
        create_missing_indexes()
        
        # Step 5: Verify final schema
        print("\n" + "="*50)
        if verify_final_schema():
            print("\n✓ All schema verification checks passed!")
        else:
            print("\n⚠ Some schema verification checks failed (see above)")
    
    print("\n" + "="*50)
    print("✓ MIGRATION COMPLETED")
    print("="*50)
    
    if migrations:
        print(f"\nColumns added during migration:")
        for migration in migrations:
            print(f"  - {migration}")
    
    print("\nNext steps:")
    print("1. Restart your Flask application")
    print("2. Test that the application loads without errors")
    print("3. Use admin interface to set Azure folder names")
    print("4. Proceed with Phase 2 (Azure Storage integration)")

if __name__ == '__main__':
    main()