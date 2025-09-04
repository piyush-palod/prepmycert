
#!/usr/bin/env python3

import os
from app import app, db
from models import User, Course, Question, AnswerOption, UserPurchase, TestAttempt, UserAnswer, OTPToken
from models import Coupon, Bundle, BundleCourse, CouponUsage
from sqlalchemy import text

def migrate_database():
    """Migrate database to add coupon and bundle support"""
    
    with app.app_context():
        print("🔄 Starting database migration for coupons and bundles...")
        
        try:
            # Check if new columns exist in user_purchases table
            inspector = db.inspect(db.engine)
            user_purchases_columns = [col['name'] for col in inspector.get_columns('user_purchases')]
            
            # Add missing columns to user_purchases table
            missing_columns = []
            expected_columns = {
                'bundle_id': 'INTEGER',
                'original_amount': 'FLOAT',
                'discount_amount': 'FLOAT DEFAULT 0',
                'coupon_code': 'VARCHAR(50)',
                'purchase_type': 'VARCHAR(20) DEFAULT \'package\''
            }
            
            for column, column_type in expected_columns.items():
                if column not in user_purchases_columns:
                    missing_columns.append((column, column_type))
            
            # Add missing columns
            if missing_columns:
                print(f"📝 Adding {len(missing_columns)} missing columns to user_purchases table...")
                for column, column_type in missing_columns:
                    try:
                        db.session.execute(text(f'ALTER TABLE user_purchases ADD COLUMN {column} {column_type}'))
                        print(f"✅ Added column: {column}")
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            print(f"ℹ️ Column {column} already exists")
                        else:
                            print(f"❌ Error adding column {column}: {e}")
                
                db.session.commit()
            
            # Update existing purchases to have original_amount if null
            print("📝 Updating existing purchases...")
            db.session.execute(text("""
                UPDATE user_purchases 
                SET original_amount = amount_paid 
                WHERE original_amount IS NULL
            """))
            db.session.commit()
            
            # Create all new tables
            print("📝 Creating new tables...")
            db.create_all()
            
            # Add foreign key constraints if they don't exist
            try:
                # Check if foreign key constraints exist
                fk_constraints = inspector.get_foreign_keys('user_purchases')
                bundle_fk_exists = any(fk['referred_table'] == 'bundles' for fk in fk_constraints)
                
                if not bundle_fk_exists:
                    print("📝 Adding foreign key constraint for bundles...")
                    db.session.execute(text("""
                        ALTER TABLE user_purchases 
                        ADD CONSTRAINT fk_user_purchases_bundle_id 
                        FOREIGN KEY (bundle_id) REFERENCES bundles (id)
                    """))
                    db.session.commit()
                    
            except Exception as e:
                print(f"ℹ️ Foreign key constraint info: {e}")
            
            print("✅ Database migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration error: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_database()
