
from app import app, db
from models import *

def migrate_database():
    with app.app_context():
        print("Starting database migration...")
        
        # Drop all tables and recreate them
        print("Dropping all tables...")
        db.drop_all()
        
        print("Creating all tables...")
        db.create_all()
        
        print("Database migration completed successfully!")

if __name__ == "__main__":
    migrate_database()
