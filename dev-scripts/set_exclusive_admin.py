#!/usr/bin/env python3
"""
🚨 DEVELOPMENT ONLY SCRIPT 🚨
One-time script to set zeus0091@gmail.com as the ONLY admin user

This script will:
1. Remove admin privileges from ALL existing users
2. Find or create user with zeus0091@gmail.com
3. Grant admin privileges ONLY to zeus0091@gmail.com

⚠️ DELETE THIS ENTIRE dev-scripts/ FOLDER BEFORE PRODUCTION DEPLOYMENT ⚠️
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import from main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from app import app, db
from models import User
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TARGET_ADMIN_EMAIL = "zeus0091@gmail.com"

def set_exclusive_admin():
    """Set zeus0091@gmail.com as the ONLY admin user in the system"""
    
    with app.app_context():
        logger.info("🔄 Starting exclusive admin setup...")
        logger.info(f"🎯 Target admin email: {TARGET_ADMIN_EMAIL}")
        
        try:
            # Step 1: Get all current admin users
            current_admins = User.query.filter_by(is_admin=True).all()
            logger.info(f"📋 Found {len(current_admins)} current admin users:")
            
            removed_admins = []
            for admin in current_admins:
                logger.info(f"   - {admin.email} (ID: {admin.id})")
                if admin.email != TARGET_ADMIN_EMAIL:
                    removed_admins.append(admin.email)
            
            # Step 2: Remove admin privileges from ALL users
            logger.info("\n🚮 Removing admin privileges from all users...")
            removed_count = User.query.filter_by(is_admin=True).update({User.is_admin: False})
            
            if removed_count > 0:
                logger.info(f"✅ Removed admin privileges from {removed_count} users")
                for email in removed_admins:
                    logger.info(f"   - Removed admin: {email}")
            else:
                logger.info("ℹ️ No admin users found to remove")
            
            # Step 3: Find or create target user
            logger.info(f"\n👤 Looking for user: {TARGET_ADMIN_EMAIL}")
            target_user = User.query.filter_by(email=TARGET_ADMIN_EMAIL).first()
            
            if target_user:
                logger.info(f"✅ Found existing user: {TARGET_ADMIN_EMAIL} (ID: {target_user.id})")
                logger.info(f"   Name: {target_user.full_name}")
                logger.info(f"   Created: {target_user.created_at}")
                logger.info(f"   Email verified: {target_user.is_email_verified}")
            else:
                logger.info(f"❌ User {TARGET_ADMIN_EMAIL} not found!")
                logger.error("🚨 Cannot promote non-existent user to admin")
                logger.error("💡 Please ensure the user has registered first")
                return False
            
            # Step 4: Promote target user to admin
            logger.info(f"\n👑 Promoting {TARGET_ADMIN_EMAIL} to admin...")
            target_user.is_admin = True
            
            # Step 5: Commit all changes
            db.session.commit()
            
            # Step 6: Verify the changes
            logger.info("\n🔍 Verifying changes...")
            final_admins = User.query.filter_by(is_admin=True).all()
            
            logger.info(f"📊 Final admin count: {len(final_admins)}")
            for admin in final_admins:
                logger.info(f"   👑 Admin: {admin.email} (ID: {admin.id})")
            
            if len(final_admins) == 1 and final_admins[0].email == TARGET_ADMIN_EMAIL:
                logger.info(f"\n🎉 SUCCESS! {TARGET_ADMIN_EMAIL} is now the ONLY admin user")
                logger.info(f"✅ Admin setup completed successfully")
                
                logger.info(f"\n📝 Next steps:")
                logger.info(f"1. Test admin login with {TARGET_ADMIN_EMAIL}")
                logger.info(f"2. Verify admin features work correctly")
                logger.info(f"3. Delete dev-scripts/ folder before production")
                
                return True
            else:
                logger.error(f"❌ Something went wrong! Expected 1 admin, found {len(final_admins)}")
                return False
                
        except Exception as e:
            logger.error(f"💥 Error during admin setup: {str(e)}")
            db.session.rollback()
            return False

def show_current_admins():
    """Display current admin users for verification"""
    
    with app.app_context():
        admins = User.query.filter_by(is_admin=True).all()
        
        print(f"\n📋 Current Admin Users ({len(admins)}):")
        if admins:
            for admin in admins:
                print(f"   👑 {admin.email} (ID: {admin.id}) - {admin.full_name}")
                print(f"      Created: {admin.created_at}")
                print(f"      Email verified: {admin.is_email_verified}")
                print()
        else:
            print("   No admin users found")

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--show':
        show_current_admins()
        return
    
    print("="*60)
    print("🚨 EXCLUSIVE ADMIN SETUP SCRIPT 🚨")
    print("="*60)
    print(f"Target admin email: {TARGET_ADMIN_EMAIL}")
    print("\nThis script will:")
    print("1. Remove ALL existing admin privileges")
    print(f"2. Make {TARGET_ADMIN_EMAIL} the ONLY admin")
    print("\n⚠️ This action is IRREVERSIBLE!")
    
    # Show current state
    show_current_admins()
    
    # Ask for confirmation
    response = input(f"\nProceed with making {TARGET_ADMIN_EMAIL} the only admin? (type 'YES' to confirm): ")
    
    if response.strip() != 'YES':
        print("❌ Operation cancelled")
        return
    
    # Execute the setup
    success = set_exclusive_admin()
    
    if success:
        print("\n" + "="*60)
        print("🎉 ADMIN SETUP COMPLETED SUCCESSFULLY!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ ADMIN SETUP FAILED!")
        print("="*60)

if __name__ == '__main__':
    main()