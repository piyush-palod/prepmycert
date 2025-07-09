
#!/usr/bin/env python3
"""
Database migration script to add new columns for OTP email system
"""

import os
import sys
from sqlalchemy import text
from app import app, db

def migrate_database():
    """Add missing columns to existing database tables"""
    
    with app.app_context():
        try:
            # Get database connection
            connection = db.engine.connect()
            trans = connection.begin()
            
            print("🔄 Starting database migration...")
            
            # Add new columns to users table if they don't exist
            migrations = [
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_email_verified BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_secret VARCHAR(32);",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_attempt TIMESTAMP;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS login_attempts INTEGER DEFAULT 0;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
            ]
            
            for migration in migrations:
                try:
                    connection.execute(text(migration))
                    print(f"✅ Executed: {migration}")
                except Exception as e:
                    print(f"⚠️  Migration already applied or error: {migration} - {e}")
            
            # Create OTP tokens table if it doesn't exist
            otp_table_sql = """
            CREATE TABLE IF NOT EXISTS otp_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token VARCHAR(6) NOT NULL,
                purpose VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_used BOOLEAN DEFAULT FALSE,
                attempts INTEGER DEFAULT 0,
                ip_address VARCHAR(45)
            );
            """
            
            try:
                connection.execute(text(otp_table_sql))
                print("✅ Created otp_tokens table")
            except Exception as e:
                print(f"⚠️  OTP tokens table already exists or error: {e}")
            
            # Create index on otp_tokens
            index_sql = "CREATE INDEX IF NOT EXISTS idx_otp_tokens_token ON otp_tokens(token);"
            try:
                connection.execute(text(index_sql))
                print("✅ Created index on otp_tokens.token")
            except Exception as e:
                print(f"⚠️  Index already exists or error: {e}")
            
            # Update existing users to have email verified as True (for backward compatibility)
            update_sql = "UPDATE users SET is_email_verified = TRUE WHERE is_email_verified IS NULL;"
            try:
                result = connection.execute(text(update_sql))
                print(f"✅ Updated {result.rowcount} existing users to have verified emails")
            except Exception as e:
                print(f"⚠️  Could not update existing users: {e}")
            
            trans.commit()
            print("🎉 Database migration completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"❌ Migration failed: {e}")
            return False
        finally:
            connection.close()
    
    return True

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)
