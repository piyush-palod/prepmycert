from datetime import datetime, timedelta
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import pyotp
import secrets

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)  # Made nullable for OTP-only users
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_email_verified = db.Column(db.Boolean, default=False)
    otp_secret = db.Column(db.String(32), nullable=True)  # For TOTP
    last_login_attempt = db.Column(db.DateTime, nullable=True)
    login_attempts = db.Column(db.Integer, default=0)
    is_locked = db.Column(db.Boolean, default=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    purchases = db.relationship('UserPurchase', backref='user', lazy=True)
    test_attempts = db.relationship('TestAttempt', backref='user', lazy=True)
    otp_tokens = db.relationship('OTPToken', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        if password:
            self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def generate_otp_secret(self):
        """Generate a new OTP secret for the user"""
        self.otp_secret = pyotp.random_base32()
        return self.otp_secret
    
    def get_totp_uri(self):
        """Get TOTP URI for QR code generation"""
        if not self.otp_secret:
            self.generate_otp_secret()
        
        totp = pyotp.TOTP(self.otp_secret)
        return totp.provisioning_uri(
            name=self.email,
            issuer_name="PrepMyCert"
        )
    
    def verify_totp(self, token):
        """Verify TOTP token"""
        if not self.otp_secret:
            return False
        
        totp = pyotp.TOTP(self.otp_secret)
        return totp.verify(token, valid_window=1)
    
    def is_account_locked(self):
        """Check if account is locked due to too many failed attempts"""
        if self.is_locked and self.locked_until:
            if datetime.utcnow() < self.locked_until:
                return True
            else:
                # Unlock account if lock period has expired
                self.is_locked = False
                self.locked_until = None
                self.login_attempts = 0
                db.session.commit()
        return False
    
    def increment_login_attempts(self):
        """Increment failed login attempts and lock account if necessary"""
        self.login_attempts += 1
        self.last_login_attempt = datetime.utcnow()
        
        # Lock account after 5 failed attempts for 30 minutes
        if self.login_attempts >= 5:
            self.is_locked = True
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)
        
        db.session.commit()
    
    def reset_login_attempts(self):
        """Reset login attempts after successful login"""
        self.login_attempts = 0
        self.last_login_attempt = datetime.utcnow()
        self.is_locked = False
        self.locked_until = None
        db.session.commit()
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class TestPackage(db.Model):
    __tablename__ = 'test_packages'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    stripe_price_id = db.Column(db.String(100), nullable=True)
    domain = db.Column(db.String(100), nullable=False)  # e.g., "Cloud Computing", "Cybersecurity"
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='test_package', lazy=True)
    purchases = db.relationship('UserPurchase', backref='test_package', lazy=True)
    test_attempts = db.relationship('TestAttempt', backref='test_package', lazy=True)
    
    @property
    def question_count(self):
        return len(self.questions)

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
    usage_limit = db.Column(db.Integer, nullable=True)  # null = unlimited
    used_count = db.Column(db.Integer, default=0)
    valid_from = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    coupon_usages = db.relationship('CouponUsage', backref='coupon', lazy=True)
    creator = db.relationship('User', backref='created_coupons', lazy=True)
    
    def is_valid(self, user_id=None, purchase_amount=0):
        """Check if coupon is valid for use"""
        # Check if coupon is active
        if not self.is_active:
            return False, "Coupon is not active"
        
        # Check expiry date
        if self.valid_until and datetime.utcnow() > self.valid_until:
            return False, "Coupon has expired"
        
        # Check if coupon is valid yet
        if datetime.utcnow() < self.valid_from:
            return False, "Coupon is not yet valid"
        
        # Check usage limit
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, "Coupon usage limit reached"
        
        # Check minimum purchase amount
        if self.minimum_purchase and purchase_amount < self.minimum_purchase:
            return False, f"Minimum purchase amount of ${self.minimum_purchase:.2f} required"
        
        # Check if user has already used this coupon
        if user_id:
            existing_usage = CouponUsage.query.filter_by(
                coupon_id=self.id, 
                user_id=user_id
            ).first()
            if existing_usage:
                return False, "You have already used this coupon"
        
        return True, "Coupon is valid"
    
    def calculate_discount(self, amount):
        """Calculate discount amount based on coupon type"""
        if self.discount_type == 'percentage':
            return min(amount * (self.discount_value / 100), amount)
        else:  # fixed
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
    user = db.relationship('User', backref='coupon_usages', lazy=True)
    purchase = db.relationship('UserPurchase', backref='coupon_usage', lazy=True)

class OTPToken(db.Model):
    __tablename__ = 'otp_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(6), nullable=False, index=True)
    purpose = db.Column(db.String(20), nullable=False)  # 'login', 'password_reset', 'verification'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    attempts = db.Column(db.Integer, default=0)
    ip_address = db.Column(db.String(45), nullable=True)
    
    def __init__(self, user_id, purpose, duration_minutes=10, ip_address=None):
        self.user_id = user_id
        self.purpose = purpose
        self.token = self.generate_token()
        self.expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.ip_address = ip_address
    
    @staticmethod
    def generate_token():
        """Generate a 6-digit OTP token"""
        return f"{secrets.randbelow(1000000):06d}"
    
    def is_expired(self):
        """Check if token has expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Check if token is valid (not expired, not used, not too many attempts)"""
        return not self.is_expired() and not self.is_used and self.attempts < 3
    
    def verify_token(self, provided_token):
        """Verify the provided token against this OTP"""
        self.attempts += 1
        db.session.commit()
        
        if not self.is_valid():
            return False
        
        if self.token == provided_token:
            self.is_used = True
            db.session.commit()
            return True
        
        return False
    
    @classmethod
    def cleanup_expired_tokens(cls):
        """Remove expired tokens from database"""
        expired_tokens = cls.query.filter(cls.expires_at < datetime.utcnow()).all()
        for token in expired_tokens:
            db.session.delete(token)
        db.session.commit()
        return len(expired_tokens)
