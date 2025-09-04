import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.INFO)

class Base(DeclarativeBase):
    pass

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or os.urandom(24)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Stripe configuration
app.config["STRIPE_PUBLISHABLE_KEY"] = os.environ.get("STRIPE_PUBLISHABLE_KEY")
app.config["STRIPE_SECRET_KEY"] = os.environ.get("STRIPE_SECRET_KEY")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    "pool_recycle": 300,
}

# Initialize extensions
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# CSRF error handler
@app.errorhandler(400)
def handle_csrf_error(e):
    from flask import render_template, request
    if 'CSRF token missing' in str(e) or 'CSRF token' in str(e):
        return render_template('auth/request_otp.html', 
                             error='Security token expired. Please try again.'), 400
    return str(e), 400

# Initialize rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"]
)
limiter.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'request_otp'  # Updated to use OTP-based auth
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Initialize email service
def init_email_service():
    """Initialize email service - called after app setup"""
    try:
        from email_service import init_mail
        init_mail(app)
        logging.info("Email service initialized")
    except Exception as e:
        logging.error(f"Failed to initialize email service: {e}")

# Database and admin setup function
def setup_database_and_admin():
    """Setup database tables and create initial admin user if specified"""
    try:
        with app.app_context():
            # Import models to register them with SQLAlchemy
            import models
            
            # Create all tables
            db.create_all()
            logging.info("Database tables created")
            
            # Auto-create admin user if specified in environment and no admin exists
            admin_email = os.environ.get('ADMIN_EMAIL')
            if admin_email:
                try:
                    existing_admin = models.User.query.filter_by(is_admin=True).first()
                    if not existing_admin:
                        admin_user = models.User.query.filter_by(email=admin_email).first()
                        if admin_user:
                            # Promote existing user to admin
                            admin_user.is_admin = True
                            admin_user.is_email_verified = True
                            db.session.commit()
                            logging.info(f"Promoted existing user {admin_email} to admin")
                        else:
                            # Create new admin user with default password
                            default_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
                            admin_user = models.User(
                                email=admin_email,
                                first_name='Admin',
                                last_name='User',
                                is_admin=True,
                                is_email_verified=True
                            )
                            admin_user.set_password(default_password)
                            db.session.add(admin_user)
                            db.session.commit()
                            logging.info(f"Created new admin user: {admin_email}")
                    else:
                        logging.info("Admin user already exists")
                except Exception as e:
                    logging.error(f"Error creating admin user: {e}")
                    
    except Exception as e:
        logging.error(f"Database setup failed: {e}")
        raise

# Function to initialize all services
def initialize_app():
    """Initialize all app services in the correct order"""
    init_email_service()
    setup_database_and_admin()

# Only run initialization if this is the main app (not during imports)
if __name__ != '__main__':
    # This is being imported, so initialize services
    try:
        initialize_app()
    except Exception as e:
        logging.error(f"App initialization failed: {e}")
        # Don't raise here to allow the app to start even if some services fail