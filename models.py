from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Import db from app to avoid circular import
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_email_verified = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)
    failed_login_attempts = db.Column(db.Integer, default=0)
    last_login_attempt = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def is_account_locked(self):
        """Check if account is locked due to failed login attempts"""
        from datetime import timedelta
        
        if not self.is_locked:
            return False
        
        # Auto-unlock after 1 hour if no recent failed attempts
        if self.last_login_attempt:
            lockout_duration = datetime.utcnow() - self.last_login_attempt
            if lockout_duration > timedelta(hours=1):
                self.is_locked = False
                self.failed_login_attempts = 0
                db.session.commit()
                return False
        
        return True
    
    def increment_login_attempts(self):
        """Increment failed login attempts and lock account if threshold reached"""
        self.failed_login_attempts += 1
        self.last_login_attempt = datetime.utcnow()
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.is_locked = True
        
        db.session.commit()
    
    def reset_login_attempts(self):
        """Reset failed login attempts and unlock account"""
        self.failed_login_attempts = 0
        self.is_locked = False
        self.last_login_attempt = None
        db.session.commit()

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    domain = db.Column(db.String(100), nullable=False)
    azure_folder = db.Column(db.String(100), nullable=False)  # Admin specified (e.g., "ai-102")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    practice_tests = db.relationship('PracticeTest', backref='course', lazy=True, cascade='all, delete-orphan')
    user_purchases = db.relationship('UserPurchase', backref='course', lazy=True)

    @property
    def question_count(self):
        """Total questions across all practice tests in this course"""
        return sum(len(pt.questions) for pt in self.practice_tests)
    
    @property 
    def practice_test_count(self):
        """Number of practice tests in this course"""
        return len(self.practice_tests)

    def get_azure_image_base_url(self):
        """Get base URL for images in this course's Azure folder"""
        import os
        base_url = os.environ.get('AZURE_BLOB_BASE_URL', 'https://prepmycertimages.blob.core.windows.net/certification-images')
        return f"{base_url}/{self.azure_folder}"

class PracticeTest(db.Model):
    __tablename__ = 'practice_tests'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    time_limit_minutes = db.Column(db.Integer, nullable=True)  # Optional time limit in minutes
    is_active = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)  # For ordering practice tests within course
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='practice_test', lazy=True, cascade='all, delete-orphan')
    test_attempts = db.relationship('TestAttempt', backref='practice_test', lazy=True)

    @property
    def question_count(self):
        """Number of questions in this practice test"""
        return len(self.questions)

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    practice_test_id = db.Column(db.Integer, db.ForeignKey('practice_tests.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)  # Stores processed HTML with Azure image URLs
    question_type = db.Column(db.String(50), default='multiple-choice')
    domain = db.Column(db.String(100), nullable=True)
    overall_explanation = db.Column(db.Text, nullable=True)  # Stores processed HTML with Azure image URLs
    order_index = db.Column(db.Integer, default=0)  # For ordering questions within practice test
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    answer_options = db.relationship('AnswerOption', backref='question', lazy=True, cascade='all, delete-orphan')
    user_answers = db.relationship('UserAnswer', backref='question', lazy=True)

class AnswerOption(db.Model):
    __tablename__ = 'answer_options'
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    option_text = db.Column(db.Text, nullable=False)  # Stores processed HTML with Azure image URLs
    explanation = db.Column(db.Text, nullable=True)  # Stores processed HTML with Azure image URLs
    is_correct = db.Column(db.Boolean, default=False)
    option_order = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserPurchase(db.Model):
    __tablename__ = 'user_purchases'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)  # Course purchase
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundles.id'), nullable=True)  # Bundle purchase
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    amount_paid = db.Column(db.Float, nullable=False)
    purchase_type = db.Column(db.String(50), default='course')  # 'course', 'bundle', 'bundle_item'
    stripe_session_id = db.Column(db.String(255), nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='purchases')

    @property
    def is_course_purchase(self):
        return self.purchase_type == 'course' and self.course_id is not None
    
    @property
    def is_bundle_purchase(self):
        return self.purchase_type == 'bundle' and self.bundle_id is not None
    
    @property
    def display_title(self):
        if self.is_bundle_purchase:
            return self.bundle.title
        return self.course.title if self.course else "Unknown Course"

class TestAttempt(db.Model):
    __tablename__ = 'test_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    practice_test_id = db.Column(db.Integer, db.ForeignKey('practice_tests.id'), nullable=False)  # Changed from test_package_id
    score = db.Column(db.Float, nullable=True)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False, default=0)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    time_taken_seconds = db.Column(db.Integer, nullable=True)  # Actual time taken
    
    # Relationships
    user = db.relationship('User', backref='test_attempts')
    user_answers = db.relationship('UserAnswer', backref='test_attempt', lazy=True, cascade='all, delete-orphan')

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

# Bundle and Coupon models (keeping existing structure but updating relationships)
class Bundle(db.Model):
    __tablename__ = 'bundles'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    original_price = db.Column(db.Float, nullable=False)
    bundle_price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bundle_courses = db.relationship('BundleCourse', backref='bundle', lazy=True, cascade='all, delete-orphan')
    user_purchases = db.relationship('UserPurchase', backref='bundle', lazy=True)

    @property
    def courses(self):
        """Get all courses in this bundle"""
        return [bc.course for bc in self.bundle_courses]
    
    @property
    def savings_amount(self):
        """Calculate savings amount"""
        return self.original_price - self.bundle_price
    
    @property
    def savings_percentage(self):
        """Calculate savings percentage"""
        if self.original_price > 0:
            return round((self.savings_amount / self.original_price) * 100, 1)
        return 0

class BundleCourse(db.Model):
    __tablename__ = 'bundle_courses'
    
    id = db.Column(db.Integer, primary_key=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundles.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)  # Changed from test_package_id
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course', backref='bundle_courses')

class Coupon(db.Model):
    __tablename__ = 'coupons'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(200), nullable=True)
    discount_type = db.Column(db.String(20), nullable=False)  # 'percentage' or 'fixed'
    discount_value = db.Column(db.Float, nullable=False)  # percentage (0-100) or fixed amount
    minimum_purchase = db.Column(db.Float, nullable=True)  # minimum purchase amount required
    usage_limit = db.Column(db.Integer, nullable=True)  # maximum number of uses
    used_count = db.Column(db.Integer, default=0)  # current usage count
    valid_from = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def is_valid(self, user_id, amount):
        """Check if coupon is valid for use"""
        # Check if coupon is active
        if not self.is_active:
            return False, "Coupon is not active"
        
        # Check expiry date
        if self.valid_until and self.valid_until < datetime.utcnow():
            return False, "Coupon has expired"
        
        # Check usage limit
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, "Coupon usage limit exceeded"
        
        # Check minimum purchase amount
        if self.minimum_purchase and amount < self.minimum_purchase:
            return False, f"Minimum purchase amount of ${self.minimum_purchase:.2f} required"
        
        # Check if user has already used this coupon
        existing_usage = CouponUsage.query.filter_by(
            coupon_id=self.id,
            user_id=user_id
        ).first()
        
        if existing_usage:
            return False, "You have already used this coupon"
        
        return True, "Coupon is valid"
    
    def calculate_discount(self, amount):
        """Calculate discount amount for given purchase amount"""
        if self.discount_type == 'percentage':
            return min(amount * (self.discount_value / 100), amount)
        elif self.discount_type == 'fixed':
            return min(self.discount_value, amount)
        return 0

class CouponUsage(db.Model):
    __tablename__ = 'coupon_usages'
    
    id = db.Column(db.Integer, primary_key=True)
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupons.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    purchase_id = db.Column(db.Integer, db.ForeignKey('user_purchases.id'), nullable=False)
    discount_amount = db.Column(db.Float, nullable=False)
    used_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    coupon = db.relationship('Coupon', backref='usages')
    user = db.relationship('User', backref='coupon_usages')
    purchase = db.relationship('UserPurchase', backref='coupon_usage')

class OTPToken(db.Model):
    __tablename__ = 'otp_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for email-only tokens
    email = db.Column(db.String(120), nullable=False, index=True)
    token = db.Column(db.String(10), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)  # 'registration', 'login', 'password_reset', 'verification'
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)  # Support IPv6
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='otp_tokens')
    
    def __init__(self, email=None, user_id=None, purpose='login', duration_minutes=10, ip_address=None):
        import random
        import string
        from datetime import timedelta
        
        if user_id:
            user = User.query.get(user_id)
            if user:
                self.email = user.email
                self.user_id = user_id
            else:
                raise ValueError("User not found")
        else:
            self.email = email
        
        self.purpose = purpose
        self.token = ''.join(random.choices(string.digits, k=6))  # 6-digit code
        self.expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.ip_address = ip_address
    
    def verify_token(self, provided_token):
        """Verify the provided token and mark as used if correct"""
        if self.is_used:
            return False
        if self.expires_at < datetime.utcnow():
            return False
        if self.token == provided_token:
            self.is_used = True
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def cleanup_expired_tokens():
        """Remove expired OTP tokens"""
        expired_tokens = OTPToken.query.filter(OTPToken.expires_at < datetime.utcnow()).all()
        count = len(expired_tokens)
        for token in expired_tokens:
            db.session.delete(token)
        db.session.commit()
        return count