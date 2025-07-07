import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-change-in-production")
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
