#!/usr/bin/env python3
"""Setup script to create admin user"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import app, db
from models import User

def create_admin_user():
    """Create an admin user for the application"""
    with app.app_context():
        # Check if admin user already exists
        admin_user = User.query.filter_by(email='admin@prepmycert.com').first()
        
        if not admin_user:
            # Create new admin user
            admin_user = User(
                email='admin@prepmycert.com',
                first_name='Admin',
                last_name='User',
                is_admin=True,
                is_email_verified=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Admin user created successfully!")
            print("   Email: admin@prepmycert.com")
            print("   Password: admin123")
            print("   Please change the password after first login.")
        else:
            # Update existing user to ensure admin privileges
            admin_user.is_admin = True
            admin_user.is_email_verified = True
            db.session.commit()
            print("✅ Admin user already exists and has been updated with admin privileges")
            print("   Email: admin@prepmycert.com")

def create_custom_admin_user():
    """Create a custom admin user with environment variables"""
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    if not admin_email or not admin_password:
        print("ℹ️  To create a custom admin user, set ADMIN_EMAIL and ADMIN_PASSWORD environment variables")
        return
    
    with app.app_context():
        # Check if custom admin user already exists
        admin_user = User.query.filter_by(email=admin_email).first()
        
        if not admin_user:
            # Create new custom admin user
            admin_user = User(
                email=admin_email,
                first_name='Admin',
                last_name='User',
                is_admin=True,
                is_email_verified=True
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"✅ Custom admin user created successfully!")
            print(f"   Email: {admin_email}")
            print("   Password: [from environment variable]")
        else:
            # Update existing user to ensure admin privileges
            admin_user.is_admin = True
            admin_user.is_email_verified = True
            db.session.commit()
            print(f"✅ Custom admin user already exists: {admin_email}")

def validate_database_connection():
    """Validate database connection and create tables if needed"""
    try:
        with app.app_context():
            # Create all tables
            db.create_all()
            print("✅ Database connection successful and tables created/verified")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

if __name__ == '__main__':
    print("🚀 Setting up PrepMyCert Admin User...")
    
    # Validate database first
    if not validate_database_connection():
        print("❌ Cannot proceed without database connection")
        exit(1)
    
    # Create default admin user
    create_admin_user()
    
    # Try to create custom admin user from environment variables
    create_custom_admin_user()
    
    print("\n✅ Admin setup complete!")
    print("\n📋 Next steps:")
    print("   1. Start the application: python main.py")
    print("   2. Login with admin credentials")
    print("   3. Create your first course and practice tests")
    print("   4. Configure Azure storage settings if using images")