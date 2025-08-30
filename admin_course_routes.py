"""
Admin routes for managing courses and practice tests in the new architecture
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import app, db
from models import Course, PracticeTest, Question, AnswerOption, User
from utils import import_questions_from_csv
import logging

logger = logging.getLogger(__name__)

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ========================
# Course Management Routes
# ========================

@app.route('/admin/courses')
@login_required
@admin_required
def admin_courses():
    """Main page for managing courses"""
    courses = Course.query.order_by(Course.created_at.desc()).all()
    
    # Get statistics for each course
    course_stats = []
    for course in courses:
        total_questions = 0
        for practice_test in course.practice_tests:
            total_questions += practice_test.question_count
        
        course_stats.append({
            'course': course,
            'practice_test_count': course.practice_test_count,
            'total_questions': total_questions
        })
    
    return render_template('admin/courses.html', course_stats=course_stats)

@app.route('/admin/courses/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_course():
    """Create a new course"""
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            price = float(request.form.get('price', 0))
            domain = request.form.get('domain', '').strip()
            
            # Validation
            if not title:
                flash('Course title is required.', 'error')
                return render_template('admin/create_course.html')
            
            if not description:
                flash('Course description is required.', 'error')
                return render_template('admin/create_course.html')
            
            if price <= 0:
                flash('Course price must be greater than 0.', 'error')
                return render_template('admin/create_course.html')
            
            if not domain:
                flash('Course domain is required.', 'error')
                return render_template('admin/create_course.html')
            
            # Check if course with same title exists
            existing_course = Course.query.filter_by(title=title).first()
            if existing_course:
                flash('A course with this title already exists.', 'error')
                return render_template('admin/create_course.html')
            
            # Create new course
            course = Course(
                title=title,
                description=description,
                price=price,
                domain=domain,
                is_active=True
            )
            
            db.session.add(course)
            db.session.flush()  # Get the ID
            
            # Create default "Practice Test 1"
            default_practice_test = PracticeTest(
                course_id=course.id,
                title="Practice Test 1",
                description=f"Practice test for {course.title}",
                order=1,
                is_active=True
            )
            
            db.session.add(default_practice_test)
            db.session.commit()
            
            flash(f'✅ Course "{title}" created successfully with default practice test!', 'success')
            logger.info(f"Created new course: {title}")
            
            return redirect(url_for('admin_courses'))
            
        except ValueError:
            flash('Invalid price format.', 'error')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating course: {str(e)}")
            flash(f'Error creating course: {str(e)}', 'error')
    
    return render_template('admin/create_course.html')

@app.route('/admin/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_course(course_id):
    """Edit an existing course"""
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        try:
            course.title = request.form.get('title', '').strip()
            course.description = request.form.get('description', '').strip()
            course.price = float(request.form.get('price', 0))
            course.domain = request.form.get('domain', '').strip()
            course.is_active = request.form.get('is_active') == 'true'
            
            # Validation
            if not course.title:
                flash('Course title is required.', 'error')
                return render_template('admin/edit_course.html', course=course)
            
            if not course.description:
                flash('Course description is required.', 'error')
                return render_template('admin/edit_course.html', course=course)
            
            if course.price <= 0:
                flash('Course price must be greater than 0.', 'error')
                return render_template('admin/edit_course.html', course=course)
            
            db.session.commit()
            
            flash(f'✅ Course "{course.title}" updated successfully!', 'success')
            logger.info(f"Updated course: {course.title}")
            
            return redirect(url_for('admin_courses'))
            
        except ValueError:
            flash('Invalid price format.', 'error')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating course: {str(e)}")
            flash(f'Error updating course: {str(e)}', 'error')
    
    return render_template('admin/edit_course.html', course=course)

@app.route('/admin/courses/<int:course_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_course(course_id):
    """Delete a course (and all its practice tests)"""
    try:
        course = Course.query.get_or_404(course_id)
        course_title = course.title
        
        # This will cascade delete practice tests and questions
        db.session.delete(course)
        db.session.commit()
        
        flash(f'✅ Course "{course_title}" deleted successfully!', 'success')
        logger.info(f"Deleted course: {course_title}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting course: {str(e)}")
        flash(f'Error deleting course: {str(e)}', 'error')
    
    return redirect(url_for('admin_courses'))

# =============================
# Practice Test Management Routes
# =============================

@app.route('/admin/courses/<int:course_id>/practice-tests')
@login_required
@admin_required
def manage_practice_tests(course_id):
    """Manage practice tests within a course"""
    course = Course.query.get_or_404(course_id)
    practice_tests = PracticeTest.query.filter_by(course_id=course_id).order_by(PracticeTest.order).all()
    
    return render_template('admin/manage_practice_tests.html', 
                         course=course, 
                         practice_tests=practice_tests)

@app.route('/admin/courses/<int:course_id>/practice-tests/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_practice_test(course_id):
    """Create a new practice test within a course"""
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            order = int(request.form.get('order', 1))
            
            # Validation
            if not title:
                flash('Practice test title is required.', 'error')
                return render_template('admin/create_practice_test.html', course=course)
            
            # Check if practice test with same order exists
            existing_test = PracticeTest.query.filter_by(
                course_id=course_id,
                order=order
            ).first()
            
            if existing_test:
                flash(f'A practice test with order {order} already exists for this course.', 'error')
                return render_template('admin/create_practice_test.html', course=course)
            
            # Create new practice test
            practice_test = PracticeTest(
                course_id=course_id,
                title=title,
                description=description,
                order=order,
                is_active=True
            )
            
            db.session.add(practice_test)
            db.session.commit()
            
            flash(f'✅ Practice test "{title}" created successfully!', 'success')
            logger.info(f"Created practice test: {title} for course: {course.title}")
            
            return redirect(url_for('manage_practice_tests', course_id=course_id))
            
        except ValueError:
            flash('Invalid order number.', 'error')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating practice test: {str(e)}")
            flash(f'Error creating practice test: {str(e)}', 'error')
    
    # Get next available order number
    max_order = db.session.query(db.func.max(PracticeTest.order)).filter_by(course_id=course_id).scalar() or 0
    next_order = max_order + 1
    
    return render_template('admin/create_practice_test.html', course=course, next_order=next_order)

@app.route('/admin/practice-tests/<int:practice_test_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_practice_test(practice_test_id):
    """Edit an existing practice test"""
    practice_test = PracticeTest.query.get_or_404(practice_test_id)
    
    if request.method == 'POST':
        try:
            practice_test.title = request.form.get('title', '').strip()
            practice_test.description = request.form.get('description', '').strip()
            new_order = int(request.form.get('order', 1))
            practice_test.is_active = request.form.get('is_active') == 'true'
            
            # Validation
            if not practice_test.title:
                flash('Practice test title is required.', 'error')
                return render_template('admin/edit_practice_test.html', practice_test=practice_test)
            
            # Check if order conflict exists (excluding current test)
            existing_test = PracticeTest.query.filter_by(
                course_id=practice_test.course_id,
                order=new_order
            ).filter(PracticeTest.id != practice_test_id).first()
            
            if existing_test:
                flash(f'A practice test with order {new_order} already exists for this course.', 'error')
                return render_template('admin/edit_practice_test.html', practice_test=practice_test)
            
            practice_test.order = new_order
            db.session.commit()
            
            flash(f'✅ Practice test "{practice_test.title}" updated successfully!', 'success')
            logger.info(f"Updated practice test: {practice_test.title}")
            
            return redirect(url_for('manage_practice_tests', course_id=practice_test.course_id))
            
        except ValueError:
            flash('Invalid order number.', 'error')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating practice test: {str(e)}")
            flash(f'Error updating practice test: {str(e)}', 'error')
    
    return render_template('admin/edit_practice_test.html', practice_test=practice_test)

@app.route('/admin/practice-tests/<int:practice_test_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_practice_test(practice_test_id):
    """Delete a practice test (and all its questions)"""
    try:
        practice_test = PracticeTest.query.get_or_404(practice_test_id)
        course_id = practice_test.course_id
        practice_test_title = practice_test.title
        
        # This will cascade delete questions and answer options
        db.session.delete(practice_test)
        db.session.commit()
        
        flash(f'✅ Practice test "{practice_test_title}" deleted successfully!', 'success')
        logger.info(f"Deleted practice test: {practice_test_title}")
        
        return redirect(url_for('manage_practice_tests', course_id=course_id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting practice test: {str(e)}")
        flash(f'Error deleting practice test: {str(e)}', 'error')
        return redirect(url_for('admin_courses'))

# =============================
# Question Management Routes
# =============================

@app.route('/admin/practice-tests/<int:practice_test_id>/questions')
@login_required
@admin_required
def manage_practice_test_questions(practice_test_id):
    """Manage questions within a practice test"""
    practice_test = PracticeTest.query.get_or_404(practice_test_id)
    questions = Question.query.filter_by(practice_test_id=practice_test_id).all()
    
    return render_template('admin/manage_practice_test_questions.html', 
                         practice_test=practice_test, 
                         questions=questions)

@app.route('/admin/practice-tests/<int:practice_test_id>/questions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_practice_test_question(practice_test_id):
    """Add a question to a practice test"""
    practice_test = PracticeTest.query.get_or_404(practice_test_id)
    
    if request.method == 'POST':
        try:
            # Import image processor for handling images
            from image_processor import image_processor
            
            question_text = request.form.get('question_text', '').strip()
            question_type = request.form.get('question_type', 'multiple-choice')
            domain = request.form.get('domain', '').strip()
            overall_explanation = request.form.get('overall_explanation', '').strip()
            
            # Create question
            question = Question(
                practice_test_id=practice_test_id,
                question_text=question_text,
                question_type=question_type,
                domain=domain,
                overall_explanation=overall_explanation
            )
            
            # Process images if present
            if image_processor.has_image_references(question_text):
                question.processed_question_text = image_processor.process_text_for_azure(
                    question_text, practice_test.course_id
                )
            
            if overall_explanation and image_processor.has_image_references(overall_explanation):
                question.processed_explanation = image_processor.process_text_for_azure(
                    overall_explanation, practice_test.course_id
                )
            
            db.session.add(question)
            db.session.flush()  # Get the question ID
            
            # Add answer options
            option_count = int(request.form.get('option_count', 4))
            for i in range(1, option_count + 1):
                option_text = request.form.get(f'option_text_{i}', '').strip()
                option_explanation = request.form.get(f'option_explanation_{i}', '').strip()
                is_correct = request.form.get(f'option_correct_{i}') == 'on'
                
                if option_text:
                    answer_option = AnswerOption(
                        question_id=question.id,
                        option_text=option_text,
                        explanation=option_explanation,
                        is_correct=is_correct,
                        option_order=i
                    )
                    
                    # Process images in options
                    if image_processor.has_image_references(option_text):
                        answer_option.processed_option_text = image_processor.process_text_for_azure(
                            option_text, practice_test.course_id
                        )
                    
                    if option_explanation and image_processor.has_image_references(option_explanation):
                        answer_option.processed_explanation = image_processor.process_text_for_azure(
                            option_explanation, practice_test.course_id
                        )
                    
                    db.session.add(answer_option)
            
            db.session.commit()
            
            flash('✅ Question added successfully!', 'success')
            logger.info(f"Added question to practice test: {practice_test.title}")
            
            return redirect(url_for('manage_practice_test_questions', practice_test_id=practice_test_id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding question: {str(e)}")
            flash(f'Error adding question: {str(e)}', 'error')
    
    return render_template('admin/add_practice_test_question.html', practice_test=practice_test)

@app.route('/admin/questions/<int:question_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_practice_test_question(question_id):
    """Delete a question from a practice test"""
    try:
        question = Question.query.get_or_404(question_id)
        practice_test_id = question.practice_test_id
        
        db.session.delete(question)
        db.session.commit()
        
        flash('✅ Question deleted successfully!', 'success')
        logger.info(f"Deleted question {question_id}")
        
        return redirect(url_for('manage_practice_test_questions', practice_test_id=practice_test_id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting question: {str(e)}")
        flash(f'Error deleting question: {str(e)}', 'error')
        return redirect(url_for('admin_courses'))

# =============================
# Import/Export Routes
# =============================

@app.route('/admin/practice-tests/<int:practice_test_id>/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_practice_test_questions(practice_test_id):
    """Import questions from CSV into a practice test"""
    practice_test = PracticeTest.query.get_or_404(practice_test_id)
    
    if request.method == 'POST':
        try:
            if 'csv_file' not in request.files:
                flash('No file uploaded.', 'error')
                return render_template('admin/import_practice_test_questions.html', practice_test=practice_test)
            
            csv_file = request.files['csv_file']
            
            if csv_file.filename == '':
                flash('No file selected.', 'error')
                return render_template('admin/import_practice_test_questions.html', practice_test=practice_test)
            
            # Import questions using updated utils function
            success_count, error_count, errors = import_questions_from_csv(
                csv_file,
                practice_test_id,
                import_type='practice_test'  # New parameter to specify import type
            )
            
            if success_count > 0:
                flash(f'✅ Successfully imported {success_count} questions!', 'success')
                logger.info(f"Imported {success_count} questions to practice test: {practice_test.title}")
            
            if error_count > 0:
                flash(f'⚠️ {error_count} questions had errors during import.', 'warning')
                for error in errors[:5]:  # Show first 5 errors
                    flash(f'Error: {error}', 'error')
            
            return redirect(url_for('manage_practice_test_questions', practice_test_id=practice_test_id))
            
        except Exception as e:
            logger.error(f"Error importing questions: {str(e)}")
            flash(f'Error importing questions: {str(e)}', 'error')
    
    return render_template('admin/import_practice_test_questions.html', practice_test=practice_test)