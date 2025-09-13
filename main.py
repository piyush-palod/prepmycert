import os
from dotenv import load_dotenv

# Load environment variables from .env file first
load_dotenv()

# Import Flask app and database
from app import app, db

# Import all route modules AFTER app initialization
try:
    import routes  # Main routes
    import auth_routes  # OTP authentication routes
    import admin_coupon_routes  # Admin coupon and bundle routes
    import admin_email_routes  # Admin email configuration routes
    import health_check  # Health check endpoints for monitoring
    print("✅ All route modules imported successfully")
except ImportError as e:
    print(f"❌ Error importing routes: {e}")
    exit(1)

def ensure_database_setup():
    """Ensure database is set up properly"""
    try:
        with app.app_context():
            # Import models to ensure they're registered
            import models
            # Create all tables if they don't exist
            db.create_all()
            print("✅ Database tables verified/created")
    except Exception as e:
        print(f"❌ Database setup error: {e}")
        return False
    return True

if __name__ == '__main__':
    print("🚀 Starting PrepMyCert application...")
    
    # Verify database setup
    if not ensure_database_setup():
        print("❌ Cannot start application due to database issues")
        exit(1)
    
    # Check for required environment variables
    required_vars = ['DATABASE_URL', 'SESSION_SECRET']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set up your .env file with the required variables")
        exit(1)
    
    # Optional environment variables check
    optional_vars = ['STRIPE_SECRET_KEY', 'ADMIN_EMAIL', 'AZURE_STORAGE_CONNECTION_STRING']
    for var in optional_vars:
        if not os.environ.get(var):
            print(f"⚠️  Optional environment variable not set: {var}")
    
    # Determine debug mode
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"✅ Starting server in {'DEBUG' if debug_mode else 'PRODUCTION'} mode")
    print("📡 Server will be available at: http://localhost:5000")
    print("🛑 Press Ctrl+C to stop the server")
    print("")
    
    try:
        app.run(host='0.0.0.0', port=8000, debug=debug_mode)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        exit(1)
