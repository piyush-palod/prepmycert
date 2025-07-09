
from app import app
import os
from routes import *  # Import all routes
from auth_routes import *  # Import OTP authentication routes
from admin_email_routes import *  # Import admin email routes

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
