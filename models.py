"""
Complete Production Models for PrepMyCert
Full implementation with enhanced fields for multiple question types and performance tracking.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import re
import json

# Initialize db (imported from app.py)
from app import db

# =============================================================================
# USER MANAGEMENT MODELS
# =============================================================================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for OTP-only users
    
    # Account status
    is_admin = db.Column(db.Boolean, default=False, index=True)
    is_email_verified = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)
    
    # Security tracking
    failed_login_attempts = db.Column(db.Integer, default=0)
    last_failed_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Performance tracking
    total_test_attempts = db.Column(db.Integer, default=0)
    average_score = db.Column(db.Float, default=0.0)
    total_study_time = db.Column(db.Integer, default=0)  # in minutes
    
    # Relationships
    purchases = db.relationship('UserPurchase', backref='user', lazy=True, cascade='all, delete-orphan')
    test_attempts = db.relationship('TestAttempt', backref='user', lazy=True, cascade='all, delete-orphan')
    otp_tokens = db.relationship('OTPToken', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def update_performance_stats(self):
        """Update user's overall performance statistics"""
        completed_attempts = TestAttempt.query.filter_by(
            user_id=self.id, 
            is_completed=True
        ).all()
        
        if completed_attempts:
            self.total_test_attempts = len(completed_attempts)
            self.average_score = sum(attempt.score_percentage for attempt in completed_attempts) / len(completed_attempts)
            
            # Calculate total study time
            total_time = sum(
                (attempt.end_time - attempt.start_time).total_seconds() / 60 
                for attempt in completed_attempts 
                if attempt.end_time
            )
            self.total_study_time = int(total_time)
        
        db.session.commit()

class OTPToken(db.Model):
    __tablename__ = 'otp_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(255), nullable=False)
    purpose = db.Column(db.String(50), nullable=False, index=True)  # 'login', 'register', 'reset'
    is_used = db.Column(db.Boolean, default=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# =============================================================================
# ENHANCED TEST PACKAGE MODEL (Production Ready)
# =============================================================================

class TestPackage(db.Model):
    __tablename__ = 'test_packages'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False, default=0.0)
    stripe_price_id = db.Column(db.String(100), index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # AZURE STORAGE CONFIGURATION (Core Feature)
    azure_folder_name = db.Column(db.String(100), nullable=True, index=True)
    
    # PACKAGE METADATA (Enhanced)
    difficulty_level = db.Column(db.String(20), default='intermediate', index=True)  # beginner, intermediate, advanced
    estimated_duration = db.Column(db.Integer, default=60)  # minutes
    passing_score = db.Column(db.Integer, default=70)  # percentage
    total_questions = db.Column(db.Integer, default=0)
    
    # QUESTION TYPE TRACKING (JSON for flexibility)
    question_types = db.Column(db.JSON, default=list)  # ['multiple-choice', 'fill-in-blanks', 'true-false', 'code-completion']
    
    # CATEGORIZATION (Enhanced)
    category = db.Column(db.String(100), nullable=True, index=True)  # 'Cloud Computing', 'Cybersecurity', 'Networking'
    certification_provider = db.Column(db.String(100), nullable=True, index=True)  # 'Microsoft', 'AWS', 'CompTIA'
    certification_code = db.Column(db.String(50), nullable=True, index=True)  # 'AZ-900', 'AWS-CLF-C02', 'Security+'
    
    # PERFORMANCE TRACKING (Analytics)
    average_score = db.Column(db.Float, default=0.0)
    total_attempts = db.Column(db.Integer, default=0)
    total_completions = db.Column(db.Integer, default=0)
    pass_rate = db.Column(db.Float, default=0.0)  # percentage of attempts that passed
    
    # CONTENT STATUS (Workflow)
    content_status = db.Column(db.String(20), default='draft', index=True)  # draft, review, published, archived
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    version = db.Column(db.String(10), default='1.0')
    
    # IMAGE PROCESSING STATUS (Production Feature)
    images_processed = db.Column(db.Boolean, default=False)  # True if all images are pre-processed
    total_images = db.Column(db.Integer, default=0)  # Count of images in this package
    
    # Relationships
    questions = db.relationship('Question', backref='test_package', lazy=True, cascade='all, delete-orphan')
    purchases = db.relationship('UserPurchase', backref='test_package', lazy=True)
    test_attempts = db.relationship('TestAttempt', backref='test_package', lazy=True)
    creator = db.relationship('User', backref='created_packages', lazy=True)
    
    def __repr__(self):
        return f'<TestPackage {self.title}>'
    
    # AZURE STORAGE METHODS (Production Core)
    # =======================================
    
    @property
    def uses_azure_storage(self):
        """Check if this package uses Azure storage for images"""
        return bool(self.azure_folder_name and self.azure_folder_name.strip())
    
    def get_azure_base_url(self):
        """Get the base URL for images in this package's Azure folder"""
        if not self.uses_azure_storage:
            return None
            
        try:
            import os
            connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
            container_name = os.environ.get('AZURE_STORAGE_CONTAINER_NAME', 'certification-images')
            
            if not connection_string:
                return None
            
            # Extract account name from connection string
            account_match = re.search(r'AccountName=([^;]+)', connection_string)
            if not account_match:
                return None
            
            account_name = account_match.group(1)
            return f"https://{account_name}.blob.core.windows.net/{container_name}/{self.azure_folder_name}"
            
        except Exception:
            return None
    
    def validate_azure_folder_name(self):
        """
        Validate the Azure folder name format.
        Returns tuple (is_valid, error_message)
        """
        if not self.azure_folder_name:
            return True, None  # Optional field
            
        folder_name = self.azure_folder_name.strip()
        
        if len(folder_name) < 1:
            return False, "Folder name cannot be empty"
        
        if len(folder_name) > 100:
            return False, "Folder name too long (max 100 characters)"
        
        # Check for valid characters (Azure-safe)
        if not re.match(r'^[a-zA-Z0-9\-_]+$', folder_name):
            return False, "Folder name can only contain letters, numbers, hyphens, and underscores"
        
        if folder_name.startswith('-') or folder_name.endswith('-'):
            return False, "Folder name cannot start or end with hyphen"
        
        return True, None
    
    # STATISTICS AND ANALYTICS METHODS
    # ================================
    
    def update_statistics(self):
        """Update package statistics based on test attempts"""
        attempts = TestAttempt.query.filter_by(
            test_package_id=self.id, 
            is_completed=True
        ).all()
        
        if attempts:
            self.total_attempts = len(attempts)
            self.total_completions = len([a for a in attempts if a.score_percentage >= self.passing_score])
            self.average_score = sum(a.score_percentage for a in attempts) / len(attempts)
            self.pass_rate = (self.total_completions / self.total_attempts) * 100 if self.total_attempts > 0 else 0
        
        # Update question count and types
        self.total_questions = len(self.questions)
        question_types = set(q.question_type for q in self.questions if q.question_type)
        self.question_types = list(question_types)
        
        # Update image processing status
        processed_questions = [q for q in self.questions if q.is_processed]
        self.images_processed = len(processed_questions) == len(self.questions) if self.questions else True
        self.total_images = sum(q.images_count for q in self.questions if q.images_count)
        
        self.last_updated = datetime.utcnow()
        db.session.commit()
    
    def get_difficulty_distribution(self):
        """Get distribution of questions by difficulty"""
        from sqlalchemy import func
        distribution = db.session.query(
            Question.difficulty_level,
            func.count(Question.id)
        ).filter(
            Question.test_package_id == self.id
        ).group_by(Question.difficulty_level).all()
        
        return {level: count for level, count in distribution}
    
    def get_performance_by_domain(self):
        """Get performance statistics by domain"""
        from sqlalchemy import func
        domain_stats = db.session.query(
            Question.domain,
            func.avg(Question.correct_attempts * 1.0 / Question.total_attempts).label('success_rate'),
            func.count(Question.id).label('question_count')
        ).filter(
            Question.test_package_id == self.id,
            Question.total_attempts > 0
        ).group_by(Question.domain).all()
        
        return [
            {
                'domain': domain,
                'success_rate': round(success_rate * 100, 1) if success_rate else 0,
                'question_count': question_count
            }
            for domain, success_rate, question_count in domain_stats
        ]

# =============================================================================
# ENHANCED QUESTION MODEL (Multiple Types Support)
# =============================================================================

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    test_package_id = db.Column(db.Integer, db.ForeignKey('test_packages.id'), nullable=False, index=True)
    
    # CORE CONTENT (Pre-processed HTML)
    question_text = db.Column(db.Text, nullable=False)  # Pre-processed HTML with direct URLs
    overall_explanation = db.Column(db.Text)  # Pre-processed HTML
    domain = db.Column(db.String(200), index=True)
    
    # QUESTION TYPE SYSTEM (Core Feature)
    question_type = db.Column(db.String(50), default='multiple-choice', index=True)  # multiple-choice, fill-in-blanks, true-false, code-completion
    
    # DIFFICULTY AND SCORING
    difficulty_level = db.Column(db.String(20), default='medium', index=True)  # easy, medium, hard
    points = db.Column(db.Integer, default=1)
    time_limit = db.Column(db.Integer, nullable=True)  # seconds per question (optional)
    
    # FILL-IN-THE-BLANKS SUPPORT (JSON Data)
    blanks_data = db.Column(db.JSON, nullable=True)  # {"blanks": ["answer1", "answer2"], "case_sensitive": false}
    
    # CODE COMPLETION SUPPORT
    code_language = db.Column(db.String(50), nullable=True)  # python, javascript, sql, java, etc.
    starter_code = db.Column(db.Text, nullable=True)
    expected_solution = db.Column(db.Text, nullable=True)
    
    # IMAGE PROCESSING STATUS (Production Feature)
    is_processed = db.Column(db.Boolean, default=False, index=True)  # True if images are pre-processed
    images_count = db.Column(db.Integer, default=0)  # Number of images in this question
    
    # PERFORMANCE TRACKING (Analytics)
    correct_attempts = db.Column(db.Integer, default=0)
    total_attempts = db.Column(db.Integer, default=0)
    average_time_seconds = db.Column(db.Integer, default=0)  # Average time taken to answer
    
    # METADATA
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    order_index = db.Column(db.Integer, default=0)  # For custom question ordering
    
    # Relationships
    answer_options = db.relationship('AnswerOption', backref='question', lazy=True, cascade='all, delete-orphan')
    user_answers = db.relationship('UserAnswer', backref='question', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Question {self.id}: {self.question_type}>'
    
    # PERFORMANCE ANALYTICS
    # ====================
    
    @property
    def success_rate(self):
        """Calculate success rate percentage for this question"""
        if self.total_attempts == 0:
            return 0
        return round((self.correct_attempts / self.total_attempts) * 100, 1)
    
    @property
    def difficulty_score(self):
        """Calculate actual difficulty based on success rate"""
        if self.total_attempts < 5:
            return self.difficulty_level  # Not enough data
        
        success_rate = self.success_rate
        if success_rate >= 80:
            return 'easy'
        elif success_rate >= 50:
            return 'medium'
        else:
            return 'hard'
    
    def update_performance(self, is_correct, time_taken_seconds=0):
        """Update performance statistics when question is answered"""
        self.total_attempts += 1
        if is_correct:
            self.correct_attempts += 1
        
        # Update average time
        if time_taken_seconds > 0:
            total_time = (self.average_time_seconds * (self.total_attempts - 1)) + time_taken_seconds
            self.average_time_seconds = int(total_time / self.total_attempts)
        
        db.session.commit()
    
    # QUESTION TYPE VALIDATION
    # =======================
    
    def validate_question_data(self):
        """Validate question data based on question type"""
        errors = []
        
        if self.question_type == 'fill-in-blanks':
            if not self.blanks_data or not self.blanks_data.get('blanks'):
                errors.append("Fill-in-blanks questions require blanks_data with answers")
            
        elif self.question_type == 'code-completion':
            if not self.code_language:
                errors.append("Code completion questions require code_language")
            if not self.expected_solution:
                errors.append("Code completion questions require expected_solution")
            
        elif self.question_type == 'true-false':
            correct_options = len([opt for opt in self.answer_options if opt.is_correct])
            if correct_options != 1:
                errors.append("True/false questions must have exactly one correct answer")
        
        elif self.question_type == 'multiple-choice':
            if len(self.answer_options) < 2:
                errors.append("Multiple choice questions need at least 2 options")
            correct_options = len([opt for opt in self.answer_options if opt.is_correct])
            if correct_options == 0:
                errors.append("Multiple choice questions must have at least one correct answer")
        
        return errors
    
    def get_correct_answers(self):
        """Get list of correct answer options"""
        return [opt for opt in self.answer_options if opt.is_correct]
    
    def check_fill_in_blanks_answer(self, user_answers):
        """Check fill-in-the-blanks answer correctness"""
        if self.question_type != 'fill-in-blanks' or not self.blanks_data:
            return False
        
        expected_blanks = self.blanks_data.get('blanks', [])
        case_sensitive = self.blanks_data.get('case_sensitive', False)
        
        if len(user_answers) != len(expected_blanks):
            return False
        
        for user_answer, expected in zip(user_answers, expected_blanks):
            if case_sensitive:
                if user_answer.strip() != expected.strip():
                    return False
            else:
                if user_answer.strip().lower() != expected.strip().lower():
                    return False
        
        return True
    
    def check_code_completion_answer(self, user_code):
        """Check code completion answer (basic implementation)"""
        if self.question_type != 'code-completion' or not self.expected_solution:
            return False
        
        # Simple implementation - exact match after stripping whitespace
        # In production, you might want to use more sophisticated code comparison
        user_code_clean = re.sub(r'\s+', ' ', user_code.strip())
        expected_clean = re.sub(r'\s+', ' ', self.expected_solution.strip())
        
        return user_code_clean.lower() == expected_clean.lower()

# =============================================================================
# ENHANCED ANSWER OPTION MODEL
# =============================================================================

class AnswerOption(db.Model):
    __tablename__ = 'answer_options'
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False, index=True)
    option_text = db.Column(db.Text, nullable=False)  # Pre-processed HTML with direct URLs
    explanation = db.Column(db.Text)  # Pre-processed HTML
    is_correct = db.Column(db.Boolean, default=False, index=True)
    option_order = db.Column(db.Integer, default=1)
    
    # IMAGE PROCESSING STATUS
    is_processed = db.Column(db.Boolean, default=False)  # True if images are pre-processed
    
    # PERFORMANCE TRACKING
    selected_count = db.Column(db.Integer, default=0)  # How many times this option was selected
    
    # METADATA
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user_answers = db.relationship('UserAnswer', backref='answer_option', lazy=True)
    
    def __repr__(self):
        return f'<AnswerOption {self.id}: {"✓" if self.is_correct else "✗"}>'
    
    def update_selection_count(self):
        """Update how many times this option was selected"""
        self.selected_count += 1
        db.session.commit()
    
    @property
    def selection_percentage(self):
        """Calculate what percentage of users selected this option"""
        total_answers = sum(opt.selected_count for opt in self.question.answer_options)
        if total_answers == 0:
            return 0
        return round((self.selected_count / total_answers) * 100, 1)

# =============================================================================
# ENHANCED TEST ATTEMPT AND USER ANSWER MODELS
# =============================================================================

class TestAttempt(db.Model):
    __tablename__ = 'test_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    test_package_id = db.Column(db.Integer, db.ForeignKey('test_packages.id'), nullable=False, index=True)
    
    # ATTEMPT TRACKING
    start_time = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    end_time = db.Column(db.DateTime, index=True)
    is_completed = db.Column(db.Boolean, default=False, index=True)
    
    # ENHANCED SCORING SYSTEM
    score_percentage = db.Column(db.Float, default=0.0)
    total_points = db.Column(db.Integer, default=0)  # Sum of all question points
    earned_points = db.Column(db.Integer, default=0)  # Points earned by user
    
    # PERFORMANCE BREAKDOWN
    correct_answers = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    time_taken_seconds = db.Column(db.Integer, default=0)
    
    # QUESTION TYPE PERFORMANCE (JSON for flexibility)
    performance_by_type = db.Column(db.JSON, default=dict)  # {"multiple-choice": 0.8, "fill-in-blanks": 0.6}
    performance_by_difficulty = db.Column(db.JSON, default=dict)  # {"easy": 0.9, "medium": 0.7, "hard": 0.5}
    performance_by_domain = db.Column(db.JSON, default=dict)  # {"Domain 1": 0.8, "Domain 2": 0.6}
    
    # ATTEMPT METADATA
    ip_address = db.Column(db.String(45), nullable=True)  # For security tracking
    user_agent = db.Column(db.String(500), nullable=True)  # Browser info
    
    # Relationships
    user_answers = db.relationship('UserAnswer', backref='test_attempt', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<TestAttempt {self.id}: {self.score_percentage}%>'
    
    # SCORING AND ANALYTICS
    # ====================
    
    def calculate_comprehensive_score(self):
        """Calculate detailed score with analytics"""
        if not self.user_answers:
            return
        
        # Basic scoring
        total_points = 0
        earned_points = 0
        correct_count = 0
        
        # Performance tracking by category
        type_stats = {}
        difficulty_stats = {}
        domain_stats = {}
        
        for user_answer in self.user_answers:
            question = user_answer.question
            question_points = question.points or 1
            total_points += question_points
            
            # Initialize category stats
            q_type = question.question_type or 'multiple-choice'
            q_difficulty = question.difficulty_level or 'medium'
            q_domain = question.domain or 'General'
            
            for category, key in [(type_stats, q_type), (difficulty_stats, q_difficulty), (domain_stats, q_domain)]:
                if key not in category:
                    category[key] = {'correct': 0, 'total': 0, 'points_earned': 0, 'points_total': 0}
                category[key]['total'] += 1
                category[key]['points_total'] += question_points
            
            if user_answer.is_correct:
                earned_points += question_points
                correct_count += 1
                type_stats[q_type]['correct'] += 1
                type_stats[q_type]['points_earned'] += question_points
                difficulty_stats[q_difficulty]['correct'] += 1
                difficulty_stats[q_difficulty]['points_earned'] += question_points
                domain_stats[q_domain]['correct'] += 1
                domain_stats[q_domain]['points_earned'] += question_points
        
        # Update basic scores
        self.total_points = total_points
        self.earned_points = earned_points
        self.correct_answers = correct_count
        self.total_questions = len(self.user_answers)
        self.score_percentage = (earned_points / total_points * 100) if total_points > 0 else 0
        
        # Update performance breakdowns
        self.performance_by_type = {
            q_type: round(stats['points_earned'] / stats['points_total'], 3) if stats['points_total'] > 0 else 0
            for q_type, stats in type_stats.items()
        }
        
        self.performance_by_difficulty = {
            difficulty: round(stats['points_earned'] / stats['points_total'], 3) if stats['points_total'] > 0 else 0
            for difficulty, stats in difficulty_stats.items()
        }
        
        self.performance_by_domain = {
            domain: round(stats['points_earned'] / stats['points_total'], 3) if stats['points_total'] > 0 else 0
            for domain, stats in domain_stats.items()
        }
        
        # Calculate time taken
        if self.end_time and self.start_time:
            self.time_taken_seconds = int((self.end_time - self.start_time).total_seconds())
        
        db.session.commit()
        
        # Update question performance
        for user_answer in self.user_answers:
            user_answer.question.update_performance(
                user_answer.is_correct, 
                user_answer.answer_time_seconds
            )
    
    @property
    def passed(self):
        """Check if the attempt passed based on package passing score"""
        package = TestPackage.query.get(self.test_package_id)
        if package:
            return self.score_percentage >= package.passing_score
        return False
    
    @property
    def duration_minutes(self):
        """Get duration in minutes"""
        if self.end_time and self.start_time:
            duration_seconds = (self.end_time - self.start_time).total_seconds()
            return round(duration_seconds / 60, 1)
        return 0
    
    @property
    def grade_letter(self):
        """Get letter grade based on score"""
        score = self.score_percentage
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'

class UserAnswer(db.Model):
    __tablename__ = 'user_answers'
    
    id = db.Column(db.Integer, primary_key=True)
    test_attempt_id = db.Column(db.Integer, db.ForeignKey('test_attempts.id'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False, index=True)
    answer_option_id = db.Column(db.Integer, db.ForeignKey('answer_options.id'), nullable=True, index=True)  # Nullable for fill-in-blanks
    
    # ANSWER CONTENT (For different question types)
    selected_option_text = db.Column(db.Text)  # For multiple choice display
    text_answer = db.Column(db.Text)  # For fill-in-blanks, code completion
    blanks_answers = db.Column(db.JSON)  # For multiple blanks: ["answer1", "answer2"]
    
    # ANSWER STATUS
    is_correct = db.Column(db.Boolean, default=False, index=True)
    answer_time_seconds = db.Column(db.Integer, default=0)  # Time taken for this question
    
    # METADATA
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserAnswer {self.id}: {"✓" if self.is_correct else "✗"}>'
    
    def check_answer_correctness(self):
        """Check if the user's answer is correct based on question type"""
        question = self.question
        
        if question.question_type == 'multiple-choice' or question.question_type == 'true-false':
            # Check if selected option is correct
            if self.answer_option:
                return self.answer_option.is_correct
            return False
        
        elif question.question_type == 'fill-in-blanks':
            # Check fill-in-the-blanks answers
            if self.blanks_answers:
                return question.check_fill_in_blanks_answer(self.blanks_answers)
            return False
        
        elif question.question_type == 'code-completion':
            # Check code completion answer
            if self.text_answer:
                return question.check_code_completion_answer(self.text_answer)
            return False
        
        return False

# =============================================================================
# BUNDLE, COUPON, AND PURCHASE MODELS (Enhanced)
# =============================================================================

class Bundle(db.Model):
    __tablename__ = 'bundles'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    original_price = db.Column(db.Float, nullable=False)
    bundle_price = db.Column(db.Float, nullable=False)
    discount_percentage = db.Column(db.Float, default=0.0)
    stripe_price_id = db.Column(db.String(100), index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # ENHANCED BUNDLE FEATURES
    category = db.Column(db.String(100), nullable=True, index=True)  # Group bundles by category
    validity_days = db.Column(db.Integer, nullable=True)  # Optional validity period
    max_purchases = db.Column(db.Integer, nullable=True)  # Limit number of purchases
    current_purchases = db.Column(db.Integer, default=0)  # Track current purchases
    
    # Relationships
    bundle_packages = db.relationship('BundlePackage', backref='bundle', lazy=True, cascade='all, delete-orphan')
    purchases = db.relationship('UserPurchase', backref='bundle', lazy=True)
    
    def __repr__(self):
        return f'<Bundle {self.title}>'
    
    @property
    def savings_amount(self):
        """Calculate savings amount"""
        return self.original_price - self.bundle_price
    
    @property
    def packages(self):
        """Get all test packages in this bundle"""
        return [bp.test_package for bp in self.bundle_packages]
    
    def update_pricing(self):
        """Update bundle pricing based on included packages"""
        total_price = sum(bp.test_package.price for bp in self.bundle_packages if bp.test_package)
        self.original_price = total_price
        if total_price > 0:
            self.discount_percentage = ((total_price - self.bundle_price) / total_price) * 100
        db.session.commit()

class BundlePackage(db.Model):
    __tablename__ = 'bundle_packages'
    
    id = db.Column(db.Integer, primary_key=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundles.id'), nullable=False, index=True)
    test_package_id = db.Column(db.Integer, db.ForeignKey('test_packages.id'), nullable=False, index=True)
    
    # ENHANCED FEATURES
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)  # Allow temporary disable of packages in bundle
    
    # Relationships
    test_package = db.relationship('TestPackage', backref='bundle_packages', lazy=True)

class Coupon(db.Model):
    __tablename__ = 'coupons'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    discount_type = db.Column(db.String(20), nullable=False, index=True)  # 'percentage' or 'fixed'
    discount_value = db.Column(db.Float, nullable=False)
    max_uses = db.Column(db.Integer, nullable=True)
    current_uses = db.Column(db.Integer, default=0)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # ENHANCED COUPON FEATURES
    minimum_purchase_amount = db.Column(db.Float, nullable=True)  # Minimum cart value
    applicable_categories = db.Column(db.JSON, nullable=True)  # Limit to specific categories
    first_time_users_only = db.Column(db.Boolean, default=False)  # Limit to new users
    description = db.Column(db.String(200), nullable=True)  # Public description
    
    # Relationships
    usages = db.relationship('CouponUsage', backref='coupon', lazy=True)
    
    def __repr__(self):
        return f'<Coupon {self.code}>'
    
    @property
    def is_valid(self):
        """Check if coupon is currently valid"""
        if not self.is_active:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        
        return True
    
    def calculate_discount(self, amount):
        """Calculate discount amount for given purchase amount"""
        if not self.is_valid:
            return 0
        
        if self.minimum_purchase_amount and amount < self.minimum_purchase_amount:
            return 0
        
        if self.discount_type == 'percentage':
            discount = amount * (self.discount_value / 100)
        else:  # fixed amount
            discount = min(self.discount_value, amount)  # Don't exceed purchase amount
        
        return round(discount, 2)
    
    def can_be_used_by_user(self, user_id):
        """Check if coupon can be used by specific user"""
        if not self.is_valid:
            return False, "Coupon is not valid"
        
        if self.first_time_users_only:
            # Check if user has made previous purchases
            previous_purchases = UserPurchase.query.filter_by(user_id=user_id).count()
            if previous_purchases > 0:
                return False, "This coupon is for first-time users only"
        
        # Check if user already used this coupon
        user_usage = CouponUsage.query.filter_by(
            coupon_id=self.id, 
            user_id=user_id
        ).first()
        if user_usage:
            return False, "You have already used this coupon"
        
        return True, None

class CouponUsage(db.Model):
    __tablename__ = 'coupon_usages'
    
    id = db.Column(db.Integer, primary_key=True)
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupons.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    used_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    discount_amount = db.Column(db.Float, nullable=False)
    
    # ENHANCED TRACKING
    original_amount = db.Column(db.Float, nullable=False)  # Amount before discount
    purchase_id = db.Column(db.Integer, db.ForeignKey('user_purchases.id'), nullable=True)  # Link to purchase
    
    # Relationships
    user = db.relationship('User', backref='coupon_usages', lazy=True)
    purchase = db.relationship('UserPurchase', backref='coupon_usage', lazy=True)

class UserPurchase(db.Model):
    __tablename__ = 'user_purchases'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    test_package_id = db.Column(db.Integer, db.ForeignKey('test_packages.id'), nullable=True, index=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundles.id'), nullable=True, index=True)
    
    purchase_type = db.Column(db.String(20), nullable=False, index=True)  # 'package', 'bundle', 'bundle_item'
    amount_paid = db.Column(db.Float, nullable=False)
    stripe_payment_intent_id = db.Column(db.String(255), index=True)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # ENHANCED PURCHASE TRACKING
    original_amount = db.Column(db.Float, nullable=True)  # Amount before discounts
    discount_amount = db.Column(db.Float, default=0.0)  # Total discount applied
    coupon_code = db.Column(db.String(50), nullable=True)  # Coupon used
    payment_status = db.Column(db.String(20), default='completed', index=True)  # completed, pending, failed, refunded
    
    # ACCESS TRACKING
    access_granted_at = db.Column(db.DateTime, nullable=True)
    access_expires_at = db.Column(db.DateTime, nullable=True)  # For time-limited access
    is_lifetime_access = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<UserPurchase {self.id}: ${self.amount_paid}>'
    
    @property
    def is_active(self):
        """Check if purchase provides active access"""
        if self.payment_status != 'completed':
            return False
        
        if not self.is_lifetime_access and self.access_expires_at:
            return datetime.utcnow() < self.access_expires_at
        
        return True
    
    def grant_access(self):
        """Grant access to purchased content"""
        self.access_granted_at = datetime.utcnow()
        self.payment_status = 'completed'
        
        # If bundle purchase, create individual package access records
        if self.purchase_type == 'bundle' and self.bundle:
            for bundle_package in self.bundle.bundle_packages:
                if bundle_package.is_active:
                    # Create individual package access
                    package_purchase = UserPurchase(
                        user_id=self.user_id,
                        test_package_id=bundle_package.test_package_id,
                        purchase_type='bundle_item',
                        amount_paid=0.0,  # Included in bundle price
                        payment_status='completed',
                        access_granted_at=datetime.utcnow(),
                        is_lifetime_access=self.is_lifetime_access,
                        access_expires_at=self.access_expires_at
                    )
                    db.session.add(package_purchase)
        
        db.session.commit()

# =============================================================================
# UTILITY FUNCTIONS AND ANALYTICS
# =============================================================================

def get_comprehensive_statistics():
    """Get comprehensive system statistics for admin dashboard"""
    stats = {
        # Basic counts
        'users': User.query.count(),
        'admin_users': User.query.filter_by(is_admin=True).count(),
        'test_packages': TestPackage.query.count(),
        'active_packages': TestPackage.query.filter_by(is_active=True).count(),
        'questions': Question.query.count(),
        'answer_options': AnswerOption.query.count(),
        'bundles': Bundle.query.count(),
        'coupons': Coupon.query.count(),
        
        # Test attempts
        'test_attempts': TestAttempt.query.count(),
        'completed_attempts': TestAttempt.query.filter_by(is_completed=True).count(),
        'user_answers': UserAnswer.query.count(),
        
        # Purchases and revenue
        'total_purchases': UserPurchase.query.filter_by(payment_status='completed').count(),
        'total_revenue': db.session.query(db.func.sum(UserPurchase.amount_paid)).filter_by(payment_status='completed').scalar() or 0,
        'bundle_purchases': UserPurchase.query.filter_by(purchase_type='bundle', payment_status='completed').count(),
        'package_purchases': UserPurchase.query.filter_by(purchase_type='package', payment_status='completed').count(),
        
        # Content processing
        'processed_questions': Question.query.filter_by(is_processed=True).count(),
        'azure_packages': TestPackage.query.filter(TestPackage.azure_folder_name.isnot(None)).count(),
        'total_images': db.session.query(db.func.sum(Question.images_count)).scalar() or 0,
    }
    
    # Question type breakdown
    type_counts = db.session.query(
        Question.question_type, 
        db.func.count(Question.id)
    ).group_by(Question.question_type).all()
    stats['question_types'] = {qtype or 'multiple-choice': count for qtype, count in type_counts}
    
    # Average scores and performance
    avg_score = db.session.query(db.func.avg(TestAttempt.score_percentage)).filter_by(is_completed=True).scalar()
    stats['average_score'] = round(avg_score, 1) if avg_score else 0
    
    # Pass rate
    total_completed = stats['completed_attempts']
    if total_completed > 0:
        passed_attempts = db.session.query(TestAttempt).join(TestPackage).filter(
            TestAttempt.is_completed == True,
            TestAttempt.score_percentage >= TestPackage.passing_score
        ).count()
        stats['pass_rate'] = round((passed_attempts / total_completed) * 100, 1)
    else:
        stats['pass_rate'] = 0
    
    return stats

def validate_all_packages():
    """Validate all test packages for data integrity"""
    packages = TestPackage.query.all()
    results = []
    
    for package in packages:
        validation_result = {
            'package_id': package.id,
            'title': package.title,
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'question_count': len(package.questions),
            'question_types': list(set(q.question_type for q in package.questions)),
            'uses_azure': package.uses_azure_storage,
            'images_processed': package.images_processed
        }
        
        # Validate Azure folder name
        if package.azure_folder_name:
            is_valid, error = package.validate_azure_folder_name()
            if not is_valid:
                validation_result['errors'].append(f"Azure folder name error: {error}")
                validation_result['is_valid'] = False
        
        # Validate questions
        for question in package.questions:
            question_errors = question.validate_question_data()
            if question_errors:
                validation_result['errors'].extend([f"Question {question.id}: {error}" for error in question_errors])
                validation_result['is_valid'] = False
        
        # Check for missing content
        if len(package.questions) == 0:
            validation_result['warnings'].append("Package has no questions")
        
        if not package.description:
            validation_result['warnings'].append("Package has no description")
        
        results.append(validation_result)
    
    return results

def cleanup_expired_otp_tokens():
    """Clean up expired OTP tokens (maintenance function)"""
    expired_tokens = OTPToken.query.filter(
        OTPToken.expires_at < datetime.utcnow()
    ).all()
    
    count = len(expired_tokens)
    for token in expired_tokens:
        db.session.delete(token)
    
    db.session.commit()
    return count

def update_all_package_statistics():
    """Update statistics for all packages (maintenance function)"""
    packages = TestPackage.query.all()
    updated_count = 0
    
    for package in packages:
        try:
            package.update_statistics()
            updated_count += 1
        except Exception as e:
            print(f"Error updating package {package.id}: {e}")
            continue
    
    return updated_count

# =============================================================================
# INITIALIZATION AND SETUP
# =============================================================================

def create_all_tables():
    """Create all database tables"""
    db.create_all()
    print("All database tables created successfully!")

def initialize_default_data():
    """Initialize default data for new installations"""
    # Create default question types if they don't exist
    default_types = ['multiple-choice', 'fill-in-blanks', 'true-false', 'code-completion']
    
    # You could create sample data here if needed
    print("Default data initialization completed!")

# Auto-run when models are imported (but not during migrations)
if __name__ != '__main__':
    import sys
    if 'migrate' not in ' '.join(sys.argv) and 'flask' not in ' '.join(sys.argv):
        print("✅ Production Models Loaded Successfully!")
        print("📊 Features: Multiple question types, Azure storage, performance tracking")
        print("🚀 Ready for zero-runtime processing!")