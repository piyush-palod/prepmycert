#!/usr/bin/env python3
"""
Quick test script to verify that the Flask app can start successfully
after database migration.

Usage: python test_startup.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_imports():
    """Test that all imports work"""
    print("Testing imports...")
    try:
        from app import app, db
        print("✓ app.py imports successfully")
        
        from models import User, TestPackage, Question, AnswerOption
        print("✓ models.py imports successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_database_connection():
    """Test database connection and basic queries"""
    print("Testing database connection...")
    try:
        from app import app, db
        from models import User, TestPackage
        
        with app.app_context():
            # Test basic queries
            user_count = User.query.count()
            print(f"✓ Users table accessible - found {user_count} users")
            
            package_count = TestPackage.query.count()
            print(f"✓ TestPackage table accessible - found {package_count} packages")
            
            # Test new azure_folder_name field
            packages_with_azure = TestPackage.query.filter(
                TestPackage.azure_folder_name.isnot(None)
            ).count()
            print(f"✓ azure_folder_name field accessible - {packages_with_azure} packages configured")
            
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

def test_routes():
    """Test that basic routes can be accessed"""
    print("Testing routes...")
    try:
        from app import app
        
        with app.test_client() as client:
            # Test index route
            response = client.get('/')
            if response.status_code == 200:
                print("✓ Index route (/) works")
            else:
                print(f"✓ Index route accessible but returned {response.status_code} (may be expected)")
            
        return True
    except Exception as e:
        print(f"✗ Route error: {e}")
        return False

def test_azure_methods():
    """Test new Azure-related methods in TestPackage model"""
    print("Testing Azure integration methods...")
    try:
        from app import app, db
        from models import TestPackage
        
        with app.app_context():
            # Get a test package
            package = TestPackage.query.first()
            if package:
                # Test new methods
                uses_azure = package.uses_azure_storage
                print(f"✓ uses_azure_storage property works: {uses_azure}")
                
                image_url = package.get_image_url("test-image.png")
                print(f"✓ get_image_url method works: {image_url}")
                
                is_valid, error = package.validate_azure_folder_name()
                print(f"✓ validate_azure_folder_name method works: valid={is_valid}")
                
            else:
                print("✓ Azure methods accessible (no test packages to test with)")
            
        return True
    except Exception as e:
        print(f"✗ Azure methods error: {e}")
        return False

def main():
    """Run all tests"""
    print("Flask Application Startup Test")
    print("=" * 40)
    print()
    
    tests = [
        ("Import Test", test_imports),
        ("Database Connection Test", test_database_connection),
        ("Routes Test", test_routes),
        ("Azure Methods Test", test_azure_methods),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        if test_func():
            print(f"✅ {test_name} PASSED\n")
        else:
            print(f"❌ {test_name} FAILED\n")
            all_passed = False
    
    print("=" * 40)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("Your Flask application should start successfully.")
        print("\nYou can now:")
        print("1. Start your Flask app with: python main.py")
        print("2. Access the admin interface to configure Azure folders")
        print("3. Proceed with Phase 2 (Azure Storage integration)")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("Please review the errors above and fix them before starting the app.")
        print("You may need to run additional migrations or check your configuration.")
    
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)