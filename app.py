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


try:
    from azure_storage import init_azure_storage, test_azure_connection
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logging.warning("Azure storage libraries not installed. Azure image storage disabled.")

# === ADD THIS SECTION AFTER YOUR EMAIL SERVICE INIT ===
# Initialize Azure Blob Storage
if AZURE_AVAILABLE:
    # Add Azure configuration to Flask config
    app.config['AZURE_STORAGE_CONNECTION_STRING'] = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
    app.config['AZURE_STORAGE_CONTAINER_NAME'] = os.environ.get('AZURE_STORAGE_CONTAINER_NAME', 'certification-images')
    
    # Initialize Azure storage
    init_azure_storage(app)
    
    # Test connection during startup (in development)
    if app.debug or os.environ.get('FLASK_ENV') == 'development':
        with app.app_context():
            success, message = test_azure_connection()
            if success:
                logging.info(f"Azure Storage: {message}")
            else:
                logging.warning(f"Azure Storage: {message}")
else:
    logging.info("Azure Storage integration disabled - missing azure-storage-blob library")

# === ADD THIS HELPER ROUTE FOR TESTING (OPTIONAL) ===
@app.route('/admin/test-azure')
@login_required
def test_azure_storage():
    """Admin route to test Azure storage connectivity"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if not AZURE_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Azure storage libraries not installed',
            'instructions': 'Run: pip install azure-storage-blob'
        })
    
    try:
        from azure_storage import test_azure_connection, get_cache_stats, list_blobs_in_folder
        
        # Test connection
        success, message = test_azure_connection()
        
        # Get cache stats
        cache_stats = get_cache_stats()
        
        # Try to list some blobs (if connection works)
        sample_blobs = {}
        if success:
            # Test with common folder names
            test_folders = ['ai-102', 'az-900', 'aws-clf-002']
            for folder in test_folders:
                blobs = list_blobs_in_folder(folder, max_results=3)
                if blobs:
                    sample_blobs[folder] = blobs
        
        return jsonify({
            'success': success,
            'message': message,
            'cache_stats': cache_stats,
            'sample_blobs': sample_blobs,
            'azure_configured': success
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
# Configure logging
logging.basicConfig(level=logging.DEBUG)

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
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Initialize email service
from email_service import init_mail
init_mail(app)

# Create tables and setup initial admin
with app.app_context():
    import models  # noqa: F401
    db.create_all()
    logging.info("Database tables created")
    
    # Auto-create admin user if specified in environment and no admin exists
    from models import User
    admin_email = os.environ.get('ADMIN_EMAIL')
    if admin_email:
        existing_admin = User.query.filter_by(is_admin=True).first()
        if not existing_admin:
            admin_user = User.query.filter_by(email=admin_email).first()
            if admin_user:
                # Promote existing user to admin
                admin_user.is_admin = True
                db.session.commit()
                logging.info(f"Promoted existing user {admin_email} to admin")
            else:
                # Create new admin user with default password
                default_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
                admin_user = User(
                    email=admin_email,
                    first_name='Admin',
                    last_name='User',
                    is_admin=True
                )
                admin_user.set_password(default_password)
                db.session.add(admin_user)
                db.session.commit()
                logging.info(f"Created new admin user: {admin_email}")
