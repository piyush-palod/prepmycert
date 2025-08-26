#!/usr/bin/env python3
"""
Migration script to add Azure folder support to TestPackage model.
This script adds the azure_folder_name column to existing test packages.

Usage: python migrate_azure_folders.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import app, db
from models import TestPackage

def add_azure_folder_column():
    """Add azure_folder_name column to test_packages table"""
    try:
        with app.app_context():
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [column['name'] for column in inspector.get_columns('test_packages')]
            
            if 'azure_folder_name' in columns:
                print("✓ azure_folder_name column already exists")
                return True
            
            print("Adding azure_folder_name column to test_packages table...")
            
            # Add the column using raw SQL (more reliable than SQLAlchemy DDL)
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
            
            print("✓ azure_folder_name column added successfully")
            return True
            
    except Exception as e:
        print(f"✗ Error adding column: {str(e)}")
        return False

def suggest_folder_names():
    """Suggest Azure folder names for existing packages"""
    try:
        with app.app_context():
            packages = TestPackage.query.all()
            
            if not packages:
                print("No test packages found")
                return
            
            print("\n" + "="*60)
            print("SUGGESTED AZURE FOLDER NAMES FOR EXISTING PACKAGES")
            print("="*60)
            print("You can use these suggestions to manually set folder names via admin interface:")
            print()
            
            for package in packages:
                # Generate suggested folder name from title
                suggested = package.title.lower()
                suggested = suggested.replace(' ', '-')
                suggested = ''.join(c for c in suggested if c.isalnum() or c == '-')
                suggested = '-'.join(filter(None, suggested.split('-')))  # Remove empty parts
                
                print(f"Package: {package.title}")
                print(f"Suggested folder: {suggested}")
                print(f"Admin can set this via: /admin/packages/{package.id}/edit")
                print("-" * 40)
            
            print("\nNOTE: These are suggestions only. You should:")
            print("1. Verify the folder names match your Azure Blob Storage structure")
            print("2. Set them via the admin interface after the migration")
            print("3. Test image loading after configuration")
            
    except Exception as e:
        print(f"✗ Error generating suggestions: {str(e)}")

def verify_migration():
    """Verify the migration was successful"""
    try:
        with app.app_context():
            # Test if we can query the new column
            test_query = db.session.query(TestPackage.azure_folder_name).first()
            
            # Check if column exists in schema
            inspector = db.inspect(db.engine)
            columns = [column['name'] for column in inspector.get_columns('test_packages')]
            
            if 'azure_folder_name' in columns:
                print("✓ Migration verification successful")
                
                # Show current status
                total_packages = TestPackage.query.count()
                configured_packages = TestPackage.query.filter(
                    TestPackage.azure_folder_name.isnot(None),
                    TestPackage.azure_folder_name != ''
                ).count()
                
                print(f"✓ Total packages: {total_packages}")
                print(f"✓ Packages with Azure folders configured: {configured_packages}")
                print(f"✓ Packages pending configuration: {total_packages - configured_packages}")
                
                return True
            else:
                print("✗ Migration verification failed - column not found")
                return False
                
    except Exception as e:
        print(f"✗ Migration verification error: {str(e)}")
        return False

def main():
    """Main migration function"""
    print("Azure Folder Migration Script")
    print("=" * 50)
    print(f"Started at: {datetime.now()}")
    print()
    
    # Step 1: Add the column
    print("Step 1: Adding azure_folder_name column...")
    if not add_azure_folder_column():
        print("Migration failed at Step 1")
        sys.exit(1)
    
    # Step 2: Verify migration
    print("\nStep 2: Verifying migration...")
    if not verify_migration():
        print("Migration verification failed")
        sys.exit(1)
    
    # Step 3: Provide suggestions
    print("\nStep 3: Generating folder name suggestions...")
    suggest_folder_names()
    
    print("\n" + "="*50)
    print("✓ MIGRATION COMPLETED SUCCESSFULLY")
    print("="*50)
    print("\nNext steps:")
    print("1. Use the admin interface to set Azure folder names for each package")
    print("2. Verify your Azure Blob Storage has the corresponding folders")
    print("3. Test image loading after configuration")
    print("4. Run Phase 2 of the Azure integration")

if __name__ == '__main__':
    main()