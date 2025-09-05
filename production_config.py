"""
Production Configuration for PrepMyCert Azure Deployment
Enhanced security, performance, and monitoring settings
"""

import os
import logging
from datetime import timedelta


class ProductionConfig:
    """Production configuration class"""
    
    # Basic Flask Configuration
    SECRET_KEY = os.environ.get('SESSION_SECRET')
    DEBUG = False
    TESTING = False
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
    }
    
    # Security Configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Rate Limiting Configuration
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = "1000 per hour, 100 per minute"
    RATELIMIT_HEADERS_ENABLED = True
    
    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@prepmycert.com')
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', 'False').lower() == 'true'
    MAIL_MAX_EMAILS = 100
    
    # Stripe Configuration
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    # Azure Storage Configuration
    AZURE_STORAGE_CONNECTION_STRING = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
    AZURE_CONTAINER_NAME = os.environ.get('AZURE_CONTAINER_NAME', 'certification-images')
    AZURE_STORAGE_ACCOUNT_NAME = os.environ.get('AZURE_STORAGE_ACCOUNT_NAME')
    AZURE_BLOB_BASE_URL = os.environ.get('AZURE_BLOB_BASE_URL')
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s %(message)s'
    
    # Application Insights
    APPINSIGHTS_INSTRUMENTATIONKEY = os.environ.get('APPINSIGHTS_INSTRUMENTATIONKEY')
    APPLICATIONINSIGHTS_CONNECTION_STRING = os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING')
    
    # Performance Settings
    SEND_FILE_MAX_AGE_DEFAULT = timedelta(hours=24)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    
    # Session Configuration with Redis
    SESSION_TYPE = 'redis' if os.environ.get('REDIS_URL') else 'filesystem'
    SESSION_REDIS = os.environ.get('REDIS_URL') if os.environ.get('REDIS_URL') else None
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'prepmycert:'
    SESSION_FILE_DIR = '/tmp/flask_sessions'
    
    # Cache Configuration
    CACHE_TYPE = 'redis' if os.environ.get('REDIS_URL') else 'simple'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Admin Configuration
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
    
    @staticmethod
    def init_app(app):
        """Initialize application with production configuration"""
        
        # Configure logging
        if not app.debug and not app.testing:
            # File handler for application logs
            if not os.path.exists('logs'):
                os.mkdir('logs')
            
            file_handler = logging.FileHandler('logs/prepmycert.log')
            file_handler.setFormatter(logging.Formatter(ProductionConfig.LOG_FORMAT))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            # Stream handler for container logs
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter(ProductionConfig.LOG_FORMAT))
            stream_handler.setLevel(logging.INFO)
            app.logger.addHandler(stream_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('PrepMyCert startup in production mode')
        
        # Security headers
        @app.after_request
        def security_headers(response):
            """Add security headers to all responses"""
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Content Security Policy
            csp = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' https://js.stripe.com https://cdnjs.cloudflare.com",
                "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com",
                "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",
                "img-src 'self' data: https://*.blob.core.windows.net https://cdnjs.cloudflare.com",
                "connect-src 'self' https://api.stripe.com",
                "frame-src 'self' https://js.stripe.com",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'"
            ]
            response.headers['Content-Security-Policy'] = "; ".join(csp)
            
            return response
        
        # Error handlers for production
        @app.errorhandler(404)
        def not_found_error(error):
            from flask import render_template
            app.logger.warning(f'404 error: {error}')
            return render_template('404.html'), 404
        
        @app.errorhandler(500)
        def internal_error(error):
            from app import db
            from flask import render_template
            db.session.rollback()
            app.logger.error(f'500 error: {error}')
            return render_template('500.html'), 500
        
        @app.errorhandler(503)
        def service_unavailable(error):
            from flask import jsonify
            app.logger.error(f'503 error: {error}')
            return jsonify({'error': 'Service temporarily unavailable'}), 503


class DevelopmentConfig:
    """Development configuration (for local development)"""
    DEBUG = True
    TESTING = False
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    MAIL_SUPPRESS_SEND = True
    LOG_LEVEL = 'DEBUG'


class TestingConfig:
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    MAIL_SUPPRESS_SEND = True


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}