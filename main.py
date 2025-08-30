import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import app, db
import routes  # Import routes module
from routes import *  # Import all routes
import admin_coupon_routes  # Import coupon and bundle routes
import admin_email_routes  # Import email routes
import admin_course_mapping_routes  # Import Azure course mapping routes
import admin_course_routes  # Import new course and practice test management routes
import auth_routes  # Import auth routes
from auth_routes import *  # Import OTP authentication routes
from admin_email_routes import *  # Import admin email routes
from admin_coupon_routes import *  # Import admin coupon and bundle routes
from admin_course_mapping_routes import *  # Import Azure course mapping routes
from admin_course_routes import *  # Import course and practice test management routes

# Ensure all database tables are created
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)