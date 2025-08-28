"""
Enhanced Routes for PrepMyCert - Compatible with existing system
"""

import os
import re
import stripe
import json
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import pandas as pd

from app import app, db
from models import (
    User, TestPackage, Question, AnswerOption, UserPurchase, 
    TestAttempt, UserAnswer, Bundle, Coupon
)
from utils import import_questions_from_csv

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# =============================================================================
# PUBLIC ROUTES
# =============================================================================

@app.route('/')
def index():
    """Homepage with active test packages and bundles"""
    test_packages = TestPackage.query.filter_by(is_active=True).all()
    bundles = Bundle.query.filter_by(is_active=True).limit(3).all()
    return render_template('index.html', test_packages=test_packages, bundles=bundles)

# Legacy routes - redirect to new OTP-based authentication
@app.route('/register', methods=['GET', 'POST'])
def register():
    flash('Please use our new secure registration system.', 'info')
    return redirect(url_for('register_otp'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    flash('Please use our new secure login system.', 'info')
    return redirect(url_for('request_otp'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# =============================================================================
# USER DASHBOARD
# =============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    # Get user's purchased packages (excluding bundle items)
    purchased_packages = db.session.query(TestPackage).join(UserPurchase).filter(
        UserPurchase.user_id == current_user.id,
        UserPurchase.test_package_id.isnot(None),
        UserPurchase.purchase_type != 'bundle_item'
    ).all()

    # Get user's purchased bundles
    purchased_bundles = db.session.query(Bundle).join(UserPurchase).filter(
        UserPurchase.user_id == current_user.id,
        UserPurchase.bundle_id.isnot(None)
    ).all()

    # Get all accessible packages (including from bundles)
    all_accessible_packages = db.session.query(TestPackage).join(UserPurchase).filter(
        UserPurchase.user_id == current_user.id,
        UserPurchase.test_package_id.isnot(None)
    ).all()

    # Get recent test attempts
    recent_attempts = TestAttempt.query.filter_by(
        user_id=current_user.id,
        is_completed=True
    ).order_by(TestAttempt.end_time.desc()).limit(5).all()

    return render_template('dashboard.html', 
                         purchased_packages=purchased_packages,
                         purchased_bundles=purchased_bundles,
                         all_accessible_packages=all_accessible_packages,
                         recent_attempts=recent_attempts)

# =============================================================================
# TEST PACKAGE ROUTES
# =============================================================================

@app.route('/test-packages')
def test_packages():
    """Browse all available test packages"""
    packages = TestPackage.query.filter_by(is_active=True).all()
    return render_template('test_packages.html', packages=packages)

@app.route('/test-package/<int:package_id>')
def test_package_detail(package_id):
    """Test package detail page"""
    package = TestPackage.query.get_or_404(package_id)
    
    # Check if user has access
    has_access = False
    if current_user.is_authenticated:
        purchase = UserPurchase.query.filter_by(
            user_id=current_user.id,
            test_package_id=package_id
        ).first()
        has_access = purchase is not None
    
    return render_template('test_package_detail.html', package=package, has_access=has_access)

# =============================================================================
# TEST TAKING SYSTEM (Enhanced with Zero Runtime Processing)
# =============================================================================

@app.route('/take-test/<int:package_id>')
@login_required
def take_test(package_id):
    """Enhanced test taking interface with pre-processed content"""
    package = TestPackage.query.get_or_404(package_id)
    
    # Verify user has access
    purchase = UserPurchase.query.filter_by(
        user_id=current_user.id,
        test_package_id=package_id
    ).first()
    
    if not purchase:
        flash('You need to purchase this test package first.', 'error')
        return redirect(url_for('test_package_detail', package_id=package_id))
    
    # Get all questions (content is already pre-processed)
    questions = Question.query.filter_by(test_package_id=package_id).all()
    
    if not questions:
        flash('This test package has no questions yet.', 'error')
        return redirect(url_for('dashboard'))
    
    # Create new test attempt
    test_attempt = TestAttempt(
        user_id=current_user.id,
        test_package_id=package_id,
        start_time=datetime.utcnow()
    )
    
    db.session.add(test_attempt)
    db.session.commit()
    
    # Store test attempt ID in session
    session['current_test_attempt'] = test_attempt.id
    
    return render_template('take_test.html', 
                         package=package,
                         questions=questions,
                         test_attempt=test_attempt)

@app.route('/submit-test', methods=['POST'])
@login_required
def submit_test():
    """Submit test with enhanced scoring"""
    test_attempt_id = session.get('current_test_attempt')
    
    if not test_attempt_id:
        flash('Invalid test session.', 'error')
        return redirect(url_for('dashboard'))
    
    test_attempt = TestAttempt.query.get_or_404(test_attempt_id)
    
    # Verify ownership
    if test_attempt.user_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    # Process answers
    total_questions = 0
    correct_answers = 0
    
    for key, value in request.form.items():
        if key.startswith('question_'):
            question_id = int(key.replace('question_', ''))
            question = Question.query.get(question_id)
            
            if not question:
                continue
            
            total_questions += 1
            
            # Handle different question types
            is_correct = False
            
            # Check if it's multiple choice or true/false
            if value.isdigit():
                selected_option_id = int(value)
                option = AnswerOption.query.get(selected_option_id)
                if option and option.is_correct:
                    is_correct = True
                
                # Create user answer record
                user_answer = UserAnswer(
                    test_attempt_id=test_attempt.id,
                    question_id=question_id,
                    answer_option_id=selected_option_id,
                    is_correct=is_correct
                )
            else:
                # Handle text-based answers (fill-in-blanks, code completion)
                # For now, simple text comparison (can be enhanced later)
                user_answer = UserAnswer(
                    test_attempt_id=test_attempt.id,
                    question_id=question_id,
                    is_correct=False  # Will be manually graded or enhanced later
                )
                
                # If question has text_answer field, store it
                if hasattr(user_answer, 'text_answer'):
                    user_answer.text_answer = value
            
            if is_correct:
                correct_answers += 1
            
            db.session.add(user_answer)
    
    # Complete the test attempt
    test_attempt.end_time = datetime.utcnow()
    test_attempt.is_completed = True
    
    # Calculate score
    if total_questions > 0:
        score_percentage = (correct_answers / total_questions) * 100
        test_attempt.score_percentage = score_percentage
        
        # Update enhanced fields if they exist
        if hasattr(test_attempt, 'total_questions'):
            test_attempt.total_questions = total_questions
        if hasattr(test_attempt, 'correct_answers'):
            test_attempt.correct_answers = correct_answers
    
    db.session.commit()
    
    # Clear session
    session.pop('current_test_attempt', None)
    
    return redirect(url_for('test_results', attempt_id=test_attempt.id))

@app.route('/test-results/<int:attempt_id>')
@login_required
def test_results(attempt_id):
    """Enhanced test results"""
    attempt = TestAttempt.query.get_or_404(attempt_id)
    
    # Verify ownership
    if attempt.user_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get detailed results
    user_answers = UserAnswer.query.filter_by(
        test_attempt_id=attempt_id
    ).join(Question).all()
    
    return render_template('test_results.html', 
                         attempt=attempt,
                         user_answers=user_answers)

# =============================================================================
# ADMIN INTERFACE
# =============================================================================

@app.route('/admin')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get basic statistics
    stats = {
        'total_users': User.query.count(),
        'total_packages': TestPackage.query.count(),
        'active_packages': TestPackage.query.filter_by(is_active=True).count(),
        'total_questions': Question.query.count(),
        'total_attempts': TestAttempt.query.filter_by(is_completed=True).count(),
    }
    
    # Get recent activity
    recent_packages = TestPackage.query.order_by(
        TestPackage.created_at.desc()
    ).limit(5).all()
    
    recent_attempts = TestAttempt.query.filter_by(
        is_completed=True
    ).order_by(TestAttempt.end_time.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_packages=recent_packages,
                         recent_attempts=recent_attempts)

@app.route('/admin/packages')
@login_required
def admin_packages():
    """Manage test packages"""
    if not current_user.is_admin:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    packages = TestPackage.query.order_by(TestPackage.created_at.desc()).all()
    
    return render_template('admin/packages.html', packages=packages)

@app.route('/admin/package/new', methods=['GET', 'POST'])
@login_required
def admin_package_new():
    """Create new test package"""
    if not current_user.is_admin:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Create basic package
            package = TestPackage(
                title=request.form['title'],
                description=request.form.get('description', ''),
                price=float(request.form.get('price', 0)),
                stripe_price_id=request.form.get('stripe_price_id', ''),
                created_by=current_user.id
            )
            
            # Add enhanced fields if they exist
            if hasattr(package, 'difficulty_level'):
                package.difficulty_level = request.form.get('difficulty_level', 'intermediate')
            if hasattr(package, 'estimated_duration'):
                package.estimated_duration = int(request.form.get('estimated_duration', 60))
            if hasattr(package, 'passing_score'):
                package.passing_score = int(request.form.get('passing_score', 70))
            if hasattr(package, 'azure_folder_name'):
                package.azure_folder_name = request.form.get('azure_folder_name', '')
            
            db.session.add(package)
            db.session.commit()
            
            flash(f'Test package "{package.title}" created successfully!', 'success')
            return redirect(url_for('admin_packages'))
            
        except Exception as e:
            flash(f'Error creating package: {str(e)}', 'error')
            db.session.rollback()
    
    return render_template('admin/package_form.html', package=None)

@app.route('/admin/package/<int:package_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_package_edit(package_id):
    """Edit test package"""
    if not current_user.is_admin:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    package = TestPackage.query.get_or_404(package_id)
    
    if request.method == 'POST':
        try:
            # Update basic fields
            package.title = request.form['title']
            package.description = request.form.get('description', '')
            package.price = float(request.form.get('price', 0))
            package.stripe_price_id = request.form.get('stripe_price_id', '')
            package.is_active = 'is_active' in request.form
            
            # Update enhanced fields if they exist
            if hasattr(package, 'difficulty_level'):
                package.difficulty_level = request.form.get('difficulty_level', 'intermediate')
            if hasattr(package, 'estimated_duration'):
                package.estimated_duration = int(request.form.get('estimated_duration', 60))
            if hasattr(package, 'passing_score'):
                package.passing_score = int(request.form.get('passing_score', 70))
            if hasattr(package, 'azure_folder_name'):
                package.azure_folder_name = request.form.get('azure_folder_name', '')
            
            db.session.commit()
            
            flash(f'Package "{package.title}" updated successfully!', 'success')
            return redirect(url_for('admin_packages'))
            
        except Exception as e:
            flash(f'Error updating package: {str(e)}', 'error')
            db.session.rollback()
    
    return render_template('admin/package_form.html', package=package)

@app.route('/admin/package/<int:package_id>/import', methods=['GET', 'POST'])
@login_required
def admin_import_questions(package_id):
    """Import questions from CSV with enhanced processing"""
    if not current_user.is_admin:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    package = TestPackage.query.get_or_404(package_id)
    
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file selected.', 'error')
            return render_template('admin/import_questions.html', package=package)
        
        file = request.files['csv_file']
        
        if file.filename == '' or not file.filename.endswith('.csv'):
            flash('Please select a valid CSV file.', 'error')
            return render_template('admin/import_questions.html', package=package)
        
        try:
            # Import questions using enhanced utils function
            result = import_questions_from_csv(file, package_id)
            
            if isinstance(result, dict):
                flash(f'Successfully imported {result["imported"]} questions!', 'success')
                if result.get("skipped", 0) > 0:
                    flash(f'{result["skipped"]} rows were skipped.', 'warning')
            else:
                flash(f'Successfully imported {result} questions!', 'success')
            
            return redirect(url_for('admin_package_questions', package_id=package_id))
            
        except Exception as e:
            flash(f'Import failed: {str(e)}', 'error')
    
    return render_template('admin/import_questions.html', package=package)

@app.route('/admin/package/<int:package_id>/questions')
@login_required
def admin_package_questions(package_id):
    """View package questions"""
    if not current_user.is_admin:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    package = TestPackage.query.get_or_404(package_id)
    questions = Question.query.filter_by(test_package_id=package_id).all()
    
    return render_template('admin/package_questions.html',
                         package=package,
                         questions=questions)

# =============================================================================
# PURCHASE ROUTES (Keep existing functionality)
# =============================================================================

@app.route('/purchase/<int:package_id>')
@login_required
def purchase_package(package_id):
    """Purchase a test package"""
    package = TestPackage.query.get_or_404(package_id)
    
    # Check if user already owns this package
    existing_purchase = UserPurchase.query.filter_by(
        user_id=current_user.id,
        test_package_id=package_id
    ).first()
    
    if existing_purchase:
        flash('You already own this test package!', 'info')
        return redirect(url_for('dashboard'))
    
    try:
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': package.title,
                        'description': package.description or 'PrepMyCert Test Package'
                    },
                    'unit_amount': int(package.price * 100),  # Amount in cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('purchase_success', package_id=package_id, _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('test_package_detail', package_id=package_id, _external=True),
            metadata={
                'package_id': str(package_id),
                'user_id': str(current_user.id)
            }
        )
        
        return redirect(checkout_session.url)
        
    except Exception as e:
        flash(f'Payment processing error: {str(e)}', 'error')
        return redirect(url_for('test_package_detail', package_id=package_id))

@app.route('/purchase/success/<int:package_id>')
@login_required
def purchase_success(package_id):
    """Handle successful purchase"""
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash('Invalid payment session.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Verify payment with Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        if checkout_session.payment_status == 'paid':
            # Create purchase record
            purchase = UserPurchase(
                user_id=current_user.id,
                test_package_id=package_id,
                purchase_type='package',
                amount_paid=checkout_session.amount_total / 100.0,
                stripe_payment_intent_id=checkout_session.payment_intent
            )
            
            db.session.add(purchase)
            db.session.commit()
            
            package = TestPackage.query.get(package_id)
            flash(f'Successfully purchased "{package.title}"!', 'success')
            
        else:
            flash('Payment was not completed successfully.', 'error')
    
    except Exception as e:
        flash(f'Error processing purchase: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500