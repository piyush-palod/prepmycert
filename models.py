import re
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import secrets
import string

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Optional for OTP-only users
    is_admin = db.Column(db.Boolean, default=False)
    is_email_verified = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)
    failed_login_attempts = db.Column(db.Integer, default=0)
    last_failed_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    purchases = db.relationship('UserPurchase', backref='user', lazy=True)
    test_attempts = db.relationship('TestAttempt', backref='user', lazy=True)
    otp_tokens = db.relationship('OTPToken', backref='user', lazy=True)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def is_account_locked(self):
        """Check if account is locked due to failed attempts"""
        if not self.is_locked:
            return False
        
        # Auto unlock after 30 minutes
        if self.last_failed_login:
            unlock_time = self.last_failed_login + timedelta(minutes=30)
            if datetime.utcnow() > unlock_time:
                self.is_locked = False
                self.failed_login_attempts = 0
                db.session.commit()
                return False
        
        return True
    
    def record_failed_login(self):
        """Record a failed login attempt"""
        self.failed_login_attempts += 1
        self.last_failed_login = datetime.utcnow()
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.is_locked = True
        
        db.session.commit()
    
    def reset_failed_attempts(self):
        """Reset failed login attempts after successful login"""
        self.failed_login_attempts = 0
        self.is_locked = False
        self.last_failed_login = None
        db.session.commit()

class OTPToken(db.Model):
    __tablename__ = 'otp_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(10), nullable=False, index=True)
    purpose = db.Column(db.String(50), nullable=False)  # login, verification, password_reset
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4/IPv6 support
    
    def __init__(self, user_id, purpose, duration_minutes=10, ip_address=None):
        self.user_id = user_id
        self.purpose = purpose
        self.token = self.generate_token()
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(minutes=duration_minutes)
        self.ip_address = ip_address
    
    def generate_token(self):
        """Generate a 6-digit numeric OTP"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    def is_valid(self):
        """Check if token is valid (not used and not expired)"""
        return not self.is_used and datetime.utcnow() < self.expires_at
    
    def mark_as_used(self):
        """Mark token as used"""
        self.is_used = True
        db.session.commit()
    
    @classmethod
    def cleanup_expired_tokens(cls):
        """Remove expired tokens from database"""
        expired_tokens = cls.query.filter(cls.expires_at < datetime.utcnow()).all()
        count = len(expired_tokens)
        
        for token in expired_tokens:
            db.session.delete(token)
        
        db.session.commit()
        return count

class TestPackage(db.Model):
    __tablename__ = 'test_packages'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    domain = db.Column(db.String(100), nullable=False)  # ADD THIS LINE
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # NEW FIELD - Azure folder configuration
    azure_folder_name = db.Column(db.String(100), nullable=True, index=True)
    
    # Relationships
    questions = db.relationship('Question', backref='test_package', lazy=True)
    purchases = db.relationship('UserPurchase', backref='test_package', lazy=True)
    test_attempts = db.relationship('TestAttempt', backref='test_package', lazy=True)
    creator = db.relationship('User', backref='created_packages', lazy=True)
    
    @property
    def question_count(self):
        return len(self.questions)
    
    @property
    def azure_image_base_url(self):
        """
        Generate the base URL for images in this package's Azure folder
        Returns None if no Azure folder is configured
        """
        if not self.azure_folder_name:
            return None
            
        try:
            from azure_storage import get_container_base_url
            return get_container_base_url(self.azure_folder_name)
        except ImportError:
            # Azure storage not yet implemented
            return None
    
    @property
    def uses_azure_storage(self):
        """Check if this package uses Azure storage for images"""
        return bool(self.azure_folder_name and self.azure_folder_name.strip())
    
    def get_image_url(self, image_name):
        """
        Get the full URL for a specific image in this package
        Falls back to local storage if Azure is not configured
        """
        if self.uses_azure_storage:
            try:
                from azure_storage import get_blob_url
                return get_blob_url(self.azure_folder_name, image_name)
            except ImportError:
                # Azure storage not yet implemented, fall back to local
                pass
        
        # Fallback to existing local storage logic
        safe_package_name = re.sub(r'[^a-zA-Z0-9\-_]', '_', self.title.lower().replace(' ', '_'))
        return f"/static/images/questions/{safe_package_name}/{image_name}"
    
    def validate_azure_folder_name(self):
        """
        Validate the Azure folder name format
        Returns tuple (is_valid, error_message)
        """
        if not self.azure_folder_name:
            return True, None
            
        folder_name = self.azure_folder_name.strip()
        
        # Check for valid characters (lowercase letters, numbers, hyphens)
        if not re.match(r'^[a-z0-9\-]+$', folder_name):
            return False, "Folder name must contain only lowercase letters, numbers, and hyphens"
        
        # Check length
        if len(folder_name) < 2 or len(folder_name) > 63:
            return False, "Folder name must be between 2 and 63 characters"
        
        # Check for consecutive hyphens
        if '--' in folder_name:
            return False, "Folder name cannot contain consecutive hyphens"
        
        # Check start/end characters
        if folder_name.startswith('-') or folder_name.endswith('-'):
            return False, "Folder name cannot start or end with hyphen"
            
        return True, None

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    test_package_id = db.Column(db.Integer, db.ForeignKey('test_packages.id'), nullable=False, index=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False, default='multiple-choice')
    domain = db.Column(db.String(100), nullable=False, index=True)
    overall_explanation = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    answer_options = db.relationship('AnswerOption', backref='question', lazy=True, cascade='all, delete-orphan')
    user_answers = db.relationship('UserAnswer', backref='question', lazy=True)

class AnswerOption(db.Model):
    __tablename__ = 'answer_options'
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    option_text = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, default=False)
    option_order = db.Column(db.Integer, nullable=False)

class UserPurchase(db.Model):
    __tablename__ = 'user_purchases'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    test_package_id = db.Column(db.Integer, db.ForeignKey('test_packages.id'), nullable=True)  # nullable for bundles
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundles.id'), nullable=True)  # for bundle purchases
    stripe_payment_intent_id = db.Column(db.String(100), nullable=True)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    amount_paid = db.Column(db.Float, nullable=False)
    original_amount = db.Column(db.Float, nullable=False)  # amount before discount
    discount_amount = db.Column(db.Float, default=0)  # discount applied
    coupon_code = db.Column(db.String(50), nullable=True)  # coupon used
    purchase_type = db.Column(db.String(20), default='package')  # 'package' or 'bundle'
    
    @property
    def is_bundle_purchase(self):
        return self.purchase_type == 'bundle' and self.bundle_id is not None
    
    @property
    def display_title(self):
        if self.is_bundle_purchase:
            return self.bundle.title
        return self.test_package.title if self.test_package else "Unknown Package"

class TestAttempt(db.Model):
    __tablename__ = 'test_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    test_package_id = db.Column(db.Integer, db.ForeignKey('test_packages.id'), nullable=False)
    score = db.Column(db.Float, nullable=True)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False, default=0)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    
    # Relationships
    user_answers = db.relationship('UserAnswer', backref='test_attempt', lazy=True)

class UserAnswer(db.Model):
    __tablename__ = 'user_answers'
    
    id = db.Column(db.Integer, primary_key=True)
    test_attempt_id = db.Column(db.Integer, db.ForeignKey('test_attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('answer_options.id'), nullable=True)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    selected_option = db.relationship('AnswerOption', lazy=True)

class Coupon(db.Model):
    __tablename__ = 'coupons'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(200), nullable=True)
    discount_type = db.Column(db.String(20), nullable=False)  # 'percentage' or 'fixed'
    discount_value = db.Column(db.Float, nullable=False)  # percentage (0-100) or fixed amount
    minimum_purchase = db.Column(db.Float, nullable=True)  # minimum purchase amount required
    usage_limit = db.Column(db.Integer, nullable=True)  # max number of uses (null = unlimited)
    current_uses = db.Column(db.Integer, default=0)  # current number of uses
    valid_from = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime, nullable=True)  # null = no expiration
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_coupons', lazy=True)
    usage_records = db.relationship('CouponUsage', backref='coupon', lazy=True)
    
    def is_valid_for_use(self, purchase_amount=None):
        """Check if coupon is valid for use"""
        now = datetime.utcnow()
        
        # Basic validity checks
        if not self.is_active:
            return False, "Coupon is not active"
        
        if now < self.valid_from:
            return False, "Coupon is not yet valid"
        
        if self.valid_until and now > self.valid_until:
            return False, "Coupon has expired"
        
        # Usage limit check
        if self.usage_limit and self.current_uses >= self.usage_limit:
            return False, "Coupon usage limit reached"
        
        # Minimum purchase check
        if purchase_amount and self.minimum_purchase and purchase_amount < self.minimum_purchase:
            return False, f"Minimum purchase of ${self.minimum_purchase:.2f} required"
        
        return True, None
    
    def calculate_discount(self, amount):
        """Calculate discount amount for given purchase amount"""
        if self.discount_type == 'percentage':
            return min(amount * (self.discount_value / 100), amount)
        else:  # fixed amount
            return min(self.discount_value, amount)

class Bundle(db.Model):
    __tablename__ = 'bundles'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    original_price = db.Column(db.Float, nullable=False)  # sum of individual package prices
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    bundle_packages = db.relationship('BundlePackage', backref='bundle', lazy=True, cascade='all, delete-orphan')
    purchases = db.relationship('UserPurchase', backref='bundle', lazy=True)
    creator = db.relationship('User', backref='created_bundles', lazy=True)
    
    @property
    def savings(self):
        """Calculate savings amount"""
        return self.original_price - self.price
    
    @property
    def savings_percentage(self):
        """Calculate savings percentage"""
        if self.original_price > 0:
            return (self.savings / self.original_price) * 100
        return 0
    
    @property
    def package_count(self):
        """Get number of packages in bundle"""
        return len(self.bundle_packages)

class BundlePackage(db.Model):
    __tablename__ = 'bundle_packages'
    
    id = db.Column(db.Integer, primary_key=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundles.id'), nullable=False)
    test_package_id = db.Column(db.Integer, db.ForeignKey('test_packages.id'), nullable=False)
    
    # Relationships
    test_package = db.relationship('TestPackage', lazy=True)
    
    # Ensure unique combinations
    __table_args__ = (db.UniqueConstraint('bundle_id', 'test_package_id'),)

class CouponUsage(db.Model):
    __tablename__ = 'coupon_usages'
    
    id = db.Column(db.Integer, primary_key=True)
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupons.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    purchase_id = db.Column(db.Integer, db.ForeignKey('user_purchases.id'), nullable=False)
    discount_amount = db.Column(db.Float, nullable=False)
    used_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='coupon_uses', lazy=True)
    purchase = db.relationship('UserPurchase', backref='coupon_usage', lazy=True)