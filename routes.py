import os
import re
import stripe
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db, csrf
from models import User, Course, PracticeTest, Question, AnswerOption, UserPurchase, TestAttempt, UserAnswer, Bundle, Coupon
from utils import import_questions_from_csv, validate_azure_configuration, generate_question_sample_csv
from azure_service import azure_service
from datetime import datetime
from werkzeug.utils import secure_filename

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

@app.route('/')
def index():
    courses = Course.query.filter_by(is_active=True).all()
    bundles = Bundle.query.filter_by(is_active=True).limit(3).all()
    return render_template('index.html', courses=courses, bundles=bundles)

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

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's purchased courses (excluding bundle items)
    purchased_courses = db.session.query(Course).join(UserPurchase).filter(
        UserPurchase.user_id == current_user.id,
        UserPurchase.course_id.isnot(None),
        UserPurchase.purchase_type != 'bundle_item'
    ).all()

    # Get user's purchased bundles
    purchased_bundles = db.session.query(Bundle).join(UserPurchase).filter(
        UserPurchase.user_id == current_user.id,
        UserPurchase.bundle_id.isnot(None)
    ).all()

    # Get all accessible courses (including from bundles)
    all_accessible_courses = db.session.query(Course).join(UserPurchase).filter(
        UserPurchase.user_id == current_user.id,
        UserPurchase.course_id.isnot(None)
    ).all()

    # Get recent test attempts
    recent_attempts = TestAttempt.query.filter_by(
        user_id=current_user.id,
        is_completed=True
    ).order_by(TestAttempt.end_time.desc()).limit(5).all()

    return render_template('dashboard.html', 
                         purchased_courses=purchased_courses,
                         purchased_bundles=purchased_bundles,
                         all_accessible_courses=all_accessible_courses,
                         recent_attempts=recent_attempts)

@app.route('/courses')
def courses():
    """Display all available courses"""
    courses = Course.query.filter_by(is_active=True).all()
    bundles = Bundle.query.filter_by(is_active=True).all()
    return render_template('courses.html', courses=courses, bundles=bundles)

# Legacy route - redirect to courses
@app.route('/test-packages')
def test_packages():
    """Legacy route - redirect to courses"""
    return redirect(url_for('courses'))

@app.route('/course/<int:course_id>')
def course_detail(course_id):
    """Display course details and practice tests"""
    course = Course.query.get_or_404(course_id)
    
    # Check if user has already purchased this course
    has_purchased = False
    if current_user.is_authenticated:
        purchase = UserPurchase.query.filter_by(
            user_id=current_user.id,
            course_id=course_id
        ).first()
        has_purchased = purchase is not None

    # Get practice tests for this course
    practice_tests = PracticeTest.query.filter_by(
        course_id=course_id, 
        is_active=True
    ).order_by(PracticeTest.order_index).all()

    return render_template('course_detail.html', 
                         course=course, 
                         practice_tests=practice_tests,
                         has_purchased=has_purchased)

@app.route('/purchase/<int:course_id>')
@login_required
def purchase_course(course_id):
    """Purchase a course"""
    course = Course.query.get_or_404(course_id)
    
    # Check if user already owns this course
    existing_purchase = UserPurchase.query.filter_by(
        user_id=current_user.id,
        course_id=course_id
    ).first()
    
    if existing_purchase:
        flash('You already have access to this course.', 'info')
        return redirect(url_for('course_detail', course_id=course_id))
    
    try:
        # Create Stripe checkout session
        session_data = {
            'payment_method_types': ['card'],
            'line_items': [{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': course.title,
                        'description': course.description,
                    },
                    'unit_amount': int(course.price * 100),
                },
                'quantity': 1,
            }],
            'mode': 'payment',
            'success_url': url_for('payment_success', course_id=course.id, _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': url_for('payment_cancel', course_id=course.id, _external=True),
            'client_reference_id': f"{current_user.id}|{course.id}|course",
        }

        checkout_session = stripe.checkout.Session.create(**session_data)
        return redirect(checkout_session.url, code=303)
        
    except Exception as e:
        flash(f'Error creating payment session: {str(e)}', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

@app.route('/payment-success')
@login_required
def payment_success():
    session_id = request.args.get('session_id')
    course_id = request.args.get('course_id')
    
    try:
        if session_id:
            # Verify the payment session
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            
            if checkout_session.payment_status == 'paid':
                # Parse client_reference_id to get user_id, item_id, and type
                if checkout_session.client_reference_id:
                    ref_parts = checkout_session.client_reference_id.split('|')
                    user_id, item_id, purchase_type = int(ref_parts[0]), int(ref_parts[1]), ref_parts[2]
                    
                    if purchase_type == 'course':
                        # Check if purchase already exists
                        existing_purchase = UserPurchase.query.filter_by(
                            user_id=user_id,
                            course_id=item_id
                        ).first()
                        
                        if not existing_purchase:
                            course = Course.query.get(item_id)
                            purchase = UserPurchase(
                                user_id=user_id,
                                course_id=item_id,
                                purchase_date=datetime.utcnow(),
                                amount_paid=course.price,
                                purchase_type='course'
                            )
                            db.session.add(purchase)
                            db.session.commit()
                            flash(f'Purchase successful! You now have lifetime access to {course.title}.', 'success')
                        else:
                            flash('You already have access to this course.', 'info')
            else:
                flash('Payment was not completed successfully.', 'error')

    except Exception as e:
        flash(f'Error processing payment: {str(e)}', 'error')

    return render_template('payment_success.html')

@app.route('/payment-cancel')
def payment_cancel():
    course_id = request.args.get('course_id')
    flash('Payment was cancelled.', 'info')
    return render_template('payment_cancel.html', course_id=course_id)

@app.route('/take-test/<int:practice_test_id>')
@login_required
def take_test(practice_test_id):
    """Start taking a practice test"""
    practice_test = PracticeTest.query.get_or_404(practice_test_id)
    course = practice_test.course
    
    # Check if user has purchased this course or is an admin
    purchase = UserPurchase.query.filter_by(
        user_id=current_user.id,
        course_id=course.id
    ).first()

    if not purchase and not current_user.is_admin:
        flash('You must purchase this course before taking the practice test.', 'error')
        return redirect(url_for('course_detail', course_id=course.id))

    # Get questions for this practice test
    questions = Question.query.filter_by(
        practice_test_id=practice_test_id
    ).order_by(Question.order_index).all()

    if not questions:
        flash('This practice test does not have any questions yet.', 'warning')
        return redirect(url_for('course_detail', course_id=course.id))

    # Convert questions to serializable format (questions already have processed HTML with Azure URLs)
    questions_data = []
    for question in questions:
        options_data = []
        for option in question.answer_options:
            options_data.append({
                'id': option.id,
                'text': option.option_text,  # Already processed HTML with Azure URLs
                'order': option.option_order
            })

        # Sort options by order
        options_data.sort(key=lambda x: x['order'])

        questions_data.append({
            'id': question.id,
            'text': question.question_text,  # Already processed HTML with Azure URLs
            'type': question.question_type,
            'domain': question.domain,
            'options': options_data
        })

    # Create new test attempt
    test_attempt = TestAttempt(
        user_id=current_user.id,
        practice_test_id=practice_test_id,
        total_questions=len(questions)
    )
    db.session.add(test_attempt)
    db.session.commit()

    session['test_attempt_id'] = test_attempt.id
    session['current_question_index'] = 0

    return render_template('test_taking.html', 
                         course=course,
                         practice_test=practice_test,
                         questions=questions_data,
                         test_attempt=test_attempt)

@app.route('/submit-answer', methods=['POST'])
@csrf.exempt
@login_required
def submit_answer():
    test_attempt_id = session.get('test_attempt_id')
    if not test_attempt_id:
        return jsonify({'error': 'No active test session'}), 400

    question_id = request.json.get('question_id')
    selected_option_id = request.json.get('selected_option_id')

    test_attempt = TestAttempt.query.get(test_attempt_id)
    if not test_attempt or test_attempt.user_id != current_user.id:
        return jsonify({'error': 'Invalid test attempt'}), 400

    # Check if answer already exists
    existing_answer = UserAnswer.query.filter_by(
        test_attempt_id=test_attempt_id,
        question_id=question_id
    ).first()

    if existing_answer:
        # Update existing answer
        existing_answer.selected_option_id = selected_option_id
        selected_option = AnswerOption.query.get(selected_option_id)
        existing_answer.is_correct = selected_option.is_correct if selected_option else False
        existing_answer.answered_at = datetime.utcnow()
    else:
        # Create new answer
        selected_option = AnswerOption.query.get(selected_option_id)
        user_answer = UserAnswer(
            test_attempt_id=test_attempt_id,
            question_id=question_id,
            selected_option_id=selected_option_id,
            is_correct=selected_option.is_correct if selected_option else False
        )
        db.session.add(user_answer)

    db.session.commit()

    return jsonify({'success': True})

@app.route('/complete-test', methods=['POST'])
@csrf.exempt
@login_required
def complete_test():
    test_attempt_id = session.get('test_attempt_id')
    if not test_attempt_id:
        return jsonify({'error': 'No active test session'}), 400

    test_attempt = TestAttempt.query.get(test_attempt_id)
    if not test_attempt or test_attempt.user_id != current_user.id:
        return jsonify({'error': 'Invalid test attempt'}), 400

    # Calculate score
    correct_answers = UserAnswer.query.filter_by(
        test_attempt_id=test_attempt_id,
        is_correct=True
    ).count()

    total_questions = test_attempt.total_questions
    score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

    # Calculate time taken
    time_taken = int((datetime.utcnow() - test_attempt.start_time).total_seconds())

    # Update test attempt
    test_attempt.correct_answers = correct_answers
    test_attempt.score = score
    test_attempt.end_time = datetime.utcnow()
    test_attempt.time_taken_seconds = time_taken
    test_attempt.is_completed = True

    db.session.commit()

    # Clear session
    session.pop('test_attempt_id', None)
    session.pop('current_question_index', None)

    return redirect(url_for('test_results', attempt_id=test_attempt_id))

@app.route('/test-results/<int:attempt_id>')
@login_required
def test_results(attempt_id):
    test_attempt = TestAttempt.query.get_or_404(attempt_id)

    if test_attempt.user_id != current_user.id:
        flash('You can only view your own test results.', 'error')
        return redirect(url_for('dashboard'))

    # Get user answers with question details (no need for image processing - already stored)
    user_answers = db.session.query(UserAnswer, Question, AnswerOption).join(
        Question, UserAnswer.question_id == Question.id
    ).outerjoin(
        AnswerOption, UserAnswer.selected_option_id == AnswerOption.id
    ).filter(
        UserAnswer.test_attempt_id == attempt_id
    ).all()

    return render_template('test_results.html', 
                         test_attempt=test_attempt,
                         user_answers=user_answers)

# ===============================
# ADMIN ROUTES - COURSE MANAGEMENT
# ===============================

@app.route('/admin/courses')
@login_required
def admin_courses():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('admin/courses.html', courses=courses)

@app.route('/admin/create-course', methods=['GET', 'POST'])
@login_required
def create_course():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price')
        domain = request.form.get('domain', '').strip()
        azure_folder = request.form.get('azure_folder', '').strip()

        if not all([title, description, price, domain, azure_folder]):
            flash('All fields are required.', 'error')
            return render_template('admin/create_course.html')

        try:
            course = Course(
                title=title,
                description=description,
                price=float(price),
                domain=domain,
                azure_folder=azure_folder
            )
            db.session.add(course)
            db.session.commit()

            flash(f'Course "{title}" created successfully!', 'success')
            return redirect(url_for('admin_courses'))

        except ValueError:
            flash('Invalid price format.', 'error')
        except Exception as e:
            flash(f'Error creating course: {str(e)}', 'error')

    return render_template('admin/create_course.html')

@app.route('/admin/edit-course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    course = Course.query.get_or_404(course_id)

    if request.method == 'POST':
        course.title = request.form.get('title', '').strip()
        course.description = request.form.get('description', '').strip()
        course.domain = request.form.get('domain', '').strip()
        course.azure_folder = request.form.get('azure_folder', '').strip()
        
        price = request.form.get('price')
        if price:
            try:
                course.price = float(price)
            except ValueError:
                flash('Invalid price format.', 'error')
                return render_template('admin/edit_course.html', course=course)

        course.is_active = request.form.get('is_active') == 'on'

        try:
            db.session.commit()
            flash('Course updated successfully!', 'success')
            return redirect(url_for('admin_courses'))
        except Exception as e:
            flash(f'Error updating course: {str(e)}', 'error')

    return render_template('admin/edit_course.html', course=course)

@app.route('/admin/toggle-course-status/<int:course_id>', methods=['POST'])
@login_required
def toggle_course_status(course_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    course = Course.query.get_or_404(course_id)
    course.is_active = not course.is_active
    db.session.commit()

    action = 'activated' if course.is_active else 'deactivated'
    flash(f'Course "{course.title}" has been {action}.', 'success')
    return redirect(url_for('admin_courses'))

# ===============================
# ADMIN ROUTES - PRACTICE TEST MANAGEMENT
# ===============================

@app.route('/admin/course/<int:course_id>/practice-tests')
@login_required
def manage_practice_tests(course_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    course = Course.query.get_or_404(course_id)
    practice_tests = PracticeTest.query.filter_by(course_id=course_id).order_by(PracticeTest.order_index).all()
    
    return render_template('admin/practice_test.html', course=course, practice_tests=practice_tests)

@app.route('/admin/course/<int:course_id>/create-practice-test', methods=['POST'])
@login_required
def create_practice_test(course_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    course = Course.query.get_or_404(course_id)
    
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    time_limit_minutes = request.form.get('time_limit_minutes')

    if not title:
        flash('Practice test title is required.', 'error')
        return redirect(url_for('manage_practice_tests', course_id=course_id))

    # Get next order index
    max_order = db.session.query(db.func.max(PracticeTest.order_index)).filter_by(course_id=course_id).scalar()
    next_order = (max_order or 0) + 1

    try:
        practice_test = PracticeTest(
            course_id=course_id,
            title=title,
            description=description,
            time_limit_minutes=int(time_limit_minutes) if time_limit_minutes else None,
            order_index=next_order
        )
        db.session.add(practice_test)
        db.session.commit()

        flash(f'Practice test "{title}" created successfully!', 'success')
    except Exception as e:
        flash(f'Error creating practice test: {str(e)}', 'error')

    return redirect(url_for('manage_practice_tests', course_id=course_id))

@app.route('/admin/edit-practice-test/<int:practice_test_id>', methods=['POST'])
@login_required
def edit_practice_test(practice_test_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    practice_test = PracticeTest.query.get_or_404(practice_test_id)
    course_id = practice_test.course_id

    practice_test.title = request.form.get('title', '').strip()
    practice_test.description = request.form.get('description', '').strip()
    
    time_limit = request.form.get('time_limit_minutes')
    practice_test.time_limit_minutes = int(time_limit) if time_limit else None
    
    practice_test.is_active = request.form.get('is_active') == 'on'

    try:
        db.session.commit()
        flash(f'Practice test "{practice_test.title}" updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating practice test: {str(e)}', 'error')

    return redirect(url_for('manage_practice_tests', course_id=course_id))

@app.route('/admin/toggle-practice-test-status/<int:practice_test_id>', methods=['POST'])
@login_required
def toggle_practice_test_status(practice_test_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    practice_test = PracticeTest.query.get_or_404(practice_test_id)
    course_id = practice_test.course_id
    
    practice_test.is_active = not practice_test.is_active
    db.session.commit()

    action = 'activated' if practice_test.is_active else 'deactivated'
    flash(f'Practice test "{practice_test.title}" has been {action}.', 'success')
    return redirect(url_for('manage_practice_tests', course_id=course_id))

@app.route('/admin/delete-practice-test/<int:practice_test_id>', methods=['POST'])
@login_required
def delete_practice_test(practice_test_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    practice_test = PracticeTest.query.get_or_404(practice_test_id)
    course_id = practice_test.course_id
    test_title = practice_test.title

    try:
        # First, manually delete related test attempts to handle any data inconsistencies
        test_attempts = TestAttempt.query.filter_by(practice_test_id=practice_test_id).all()
        for attempt in test_attempts:
            # Delete user answers for this test attempt
            UserAnswer.query.filter_by(test_attempt_id=attempt.id).delete()
            # Delete the test attempt
            db.session.delete(attempt)
        
        # Delete all questions (which will cascade to delete answer options)
        questions = Question.query.filter_by(practice_test_id=practice_test_id).all()
        for question in questions:
            db.session.delete(question)
        
        # Finally, delete the practice test itself
        db.session.delete(practice_test)
        db.session.commit()
        
        flash(f'Practice test "{test_title}" and all its questions have been deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting practice test: {str(e)}', 'error')
    
    return redirect(url_for('manage_practice_tests', course_id=course_id))

@app.route('/admin/practice-test/<int:practice_test_id>/questions')
@login_required
def manage_questions(practice_test_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    practice_test = PracticeTest.query.get_or_404(practice_test_id)
    questions = Question.query.filter_by(practice_test_id=practice_test_id).order_by(Question.order_index).all()
    
    return render_template('admin/manage_questions.html', practice_test=practice_test, questions=questions)

# ===============================
# ADMIN ROUTES - QUESTION MANAGEMENT
# ===============================

@app.route('/admin/practice-test/<int:practice_test_id>/add-question', methods=['GET', 'POST'])
@login_required 
def add_question(practice_test_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    practice_test = PracticeTest.query.get_or_404(practice_test_id)
    course = practice_test.course

    if request.method == 'POST':
        # Get next order index
        max_order = db.session.query(db.func.max(Question.order_index)).filter_by(practice_test_id=practice_test_id).scalar()
        next_order = (max_order or 0) + 1

        # Process question text with Azure images
        question_text = request.form.get('question_text', '').strip()
        processed_question_text = azure_service.process_text_with_images(question_text, course.azure_folder)

        overall_explanation = request.form.get('overall_explanation', '').strip()
        processed_explanation = azure_service.process_text_with_images(overall_explanation, course.azure_folder) if overall_explanation else ''

        question = Question(
            practice_test_id=practice_test_id,
            question_text=processed_question_text,
            question_type=request.form.get('question_type', 'multiple-choice'),
            domain=request.form.get('domain', ''),
            overall_explanation=processed_explanation,
            order_index=next_order
        )
        db.session.add(question)
        db.session.flush()

        # Validate and add answer options
        option_count = int(request.form.get('option_count', 4))
        valid_options = []
        has_correct_answer = False
        
        # First, collect valid options
        for i in range(1, option_count + 1):
            option_text = request.form.get(f'option_text_{i}')
            option_explanation = request.form.get(f'option_explanation_{i}')
            option_correct = request.form.get(f'option_correct_{i}') == 'on'

            if option_text and option_text.strip():
                valid_options.append({
                    'text': option_text.strip(),
                    'explanation': option_explanation.strip() if option_explanation else '',
                    'is_correct': option_correct,
                    'order': i
                })
                if option_correct:
                    has_correct_answer = True
        
        # Validate minimum requirements
        if len(valid_options) < 2:
            flash('Please provide at least 2 answer options.', 'error')
            return render_template('admin/add_question.html', practice_test=practice_test)
        
        if not has_correct_answer:
            flash('Please select at least one correct answer.', 'error')
            return render_template('admin/add_question.html', practice_test=practice_test)
        
        # Add valid options to the database
        for option_data in valid_options:
            # Process option text with Azure images
            processed_option_text = azure_service.process_text_with_images(option_data['text'], course.azure_folder)
            processed_option_explanation = azure_service.process_text_with_images(option_data['explanation'], course.azure_folder) if option_data['explanation'] else ''

            option = AnswerOption(
                question_id=question.id,
                option_text=processed_option_text,
                explanation=processed_option_explanation,
                is_correct=option_data['is_correct'],
                option_order=option_data['order']
            )
            db.session.add(option)

        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('manage_questions', practice_test_id=practice_test_id))

    return render_template('admin/add_question.html', practice_test=practice_test)

@app.route('/admin/edit-question/<int:question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    question = Question.query.get_or_404(question_id)
    course = question.practice_test.course

    if request.method == 'POST':
        try:
            # Update question details with Azure image processing
            question_text = request.form.get('question_text', '')
            domain = request.form.get('domain', '')
            overall_explanation = request.form.get('overall_explanation', '')

            if question_text:
                question.question_text = azure_service.process_text_with_images(question_text.strip(), course.azure_folder)
            if domain:
                question.domain = domain
            if overall_explanation:
                question.overall_explanation = azure_service.process_text_with_images(overall_explanation.strip(), course.azure_folder)

            # Update answer options
            for option in question.answer_options:
                option_text = request.form.get(f'option_text_{option.id}')
                option_explanation = request.form.get(f'option_explanation_{option.id}', '')
                option_correct = request.form.get(f'option_correct_{option.id}') == 'on'

                if option_text:
                    option.option_text = azure_service.process_text_with_images(option_text.strip(), course.azure_folder)
                    option.explanation = azure_service.process_text_with_images(option_explanation.strip(), course.azure_folder) if option_explanation else ''
                    option.is_correct = option_correct

            db.session.commit()
            flash('Question updated successfully!', 'success')
            return redirect(url_for('manage_questions', practice_test_id=question.practice_test_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating question: {str(e)}', 'error')

    return render_template('admin/edit_question.html', question=question)

@app.route('/admin/delete-question/<int:question_id>', methods=['POST'])
@login_required
def delete_question(question_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    question = Question.query.get_or_404(question_id)
    practice_test_id = question.practice_test_id

    db.session.delete(question)
    db.session.commit()

    flash('Question deleted successfully!', 'success')
    return redirect(url_for('manage_questions', practice_test_id=practice_test_id))

# ===============================
# ADMIN ROUTES - CSV IMPORT
# ===============================

@app.route('/admin/import-questions', methods=['GET', 'POST'])
@login_required
def import_questions():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)

        if file and file.filename.endswith('.csv'):
            practice_test_id = request.form.get('practice_test_id')

            if not practice_test_id:
                flash('Please select a practice test.', 'error')
                return redirect(request.url)

            try:
                result = import_questions_from_csv(file, int(practice_test_id))
                flash(result['message'], 'success' if result['errors'] == 0 else 'warning')
            except Exception as e:
                flash(f'Error importing questions: {str(e)}', 'error')
        else:
            flash('Please upload a CSV file.', 'error')

    # Get all courses and their practice tests for the dropdown
    courses = Course.query.order_by(Course.title).all()
    return render_template('admin/import_questions.html', courses=courses)

# ===============================
# ADMIN ROUTES - AZURE IMAGE MANAGEMENT
# ===============================

@app.route('/admin/course/<int:course_id>/images')
@login_required
def manage_images(course_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    course = Course.query.get_or_404(course_id)
    
    # Get images from Azure
    images_result = azure_service.list_images(course.azure_folder)
    
    if images_result['success']:
        images = images_result['images']
    else:
        images = []
        flash(f'Error loading images: {images_result.get("error", "Unknown error")}', 'error')

    return render_template('admin/manage_images.html', course=course, images=images)

@app.route('/admin/course/<int:course_id>/upload-image', methods=['POST'])
@login_required
def upload_image(course_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    course = Course.query.get_or_404(course_id)

    if 'image' not in request.files:
        flash('No image file selected.', 'error')
        return redirect(request.referrer)

    file = request.files['image']
    if file.filename == '':
        flash('No image file selected.', 'error')
        return redirect(request.referrer)

    # Upload to Azure
    result = azure_service.upload_image(file, course.azure_folder)
    
    if result['success']:
        flash(f'Image "{result["filename"]}" uploaded successfully!', 'success')
    else:
        flash(f'Upload failed: {result["error"]}', 'error')

    return redirect(request.referrer)

@app.route('/admin/course/<int:course_id>/delete-image/<filename>', methods=['POST'])
@login_required
def delete_image(course_id, filename):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    course = Course.query.get_or_404(course_id)
    
    # Delete from Azure
    result = azure_service.delete_image(course.azure_folder, filename)
    
    if result['success']:
        flash(f'Image "{filename}" deleted successfully!', 'success')
    else:
        flash(f'Delete failed: {result["error"]}', 'error')

    return redirect(url_for('manage_images', course_id=course_id))

# ===============================
# ADMIN ROUTES - USER MANAGEMENT
# ===============================

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/toggle-admin/<int:user_id>', methods=['POST'])
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)

    # Prevent removing admin from the environment-specified admin
    admin_email = os.environ.get('ADMIN_EMAIL')
    if admin_email and user.email == admin_email and user.is_admin:
        flash('Cannot remove admin privileges from the environment-specified admin user.', 'error')
        return redirect(url_for('admin_users'))

    # Prevent user from removing their own admin privileges
    if user.id == current_user.id:
        flash('You cannot remove your own admin privileges.', 'error')
        return redirect(url_for('admin_users'))

    user.is_admin = not user.is_admin
    db.session.commit()

    action = 'granted' if user.is_admin else 'removed'
    flash(f'Admin privileges {action} for {user.email}.', 'success')
    return redirect(url_for('admin_users'))

# ===============================
# API ROUTES
# ===============================

@app.route('/api/practice-tests/<int:course_id>')
@login_required
def api_get_practice_tests(course_id):
    """API endpoint to get practice tests for a course (for dropdowns)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403

    practice_tests = PracticeTest.query.filter_by(course_id=course_id, is_active=True).order_by(PracticeTest.order_index).all()
    
    return jsonify({
        'practice_tests': [{
            'id': pt.id,
            'title': pt.title,
            'question_count': len(pt.questions)
        } for pt in practice_tests]
    })

@app.route('/api/sample-csv')
@login_required
def api_sample_csv():
    """Generate and download sample CSV for question import"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    csv_content = generate_question_sample_csv()
    
    from flask import Response
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=sample_questions.csv'}
    )

# ===============================
# ERROR HANDLERS
# ===============================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500