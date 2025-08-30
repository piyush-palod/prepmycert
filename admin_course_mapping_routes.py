"""
Admin routes for managing course-to-Azure folder mappings
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import app, db
from models import CourseAzureMapping, TestPackage, User
from azure_service import azure_service
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

@app.route('/admin/course-mappings')
@login_required
@admin_required
def manage_course_mappings():
    """Main page for managing course-to-Azure folder mappings"""
    # Get all existing mappings
    mappings = CourseAzureMapping.query.join(TestPackage).all()
    
    # Get packages without mappings
    mapped_package_ids = [m.test_package_id for m in mappings]
    unmapped_packages = TestPackage.query.filter(
        ~TestPackage.id.in_(mapped_package_ids),
        TestPackage.is_active == True
    ).all()
    
    # Check Azure configuration
    azure_configured = azure_service.validate_configuration()
    
    return render_template('admin/course_mappings.html', 
                         mappings=mappings,
                         unmapped_packages=unmapped_packages,
                         azure_configured=azure_configured)

@app.route('/admin/course-mappings/create', methods=['POST'])
@login_required
@admin_required
def create_course_mapping():
    """Create a new course-to-Azure folder mapping"""
    try:
        test_package_id = request.form.get('test_package_id', type=int)
        azure_folder_name = request.form.get('azure_folder_name', '').strip()
        practice_test_folder = request.form.get('practice_test_folder', 'practice-test-1').strip()
        
        # Validation
        if not test_package_id:
            flash('Please select a test package.', 'error')
            return redirect(url_for('manage_course_mappings'))
        
        if not azure_folder_name:
            flash('Azure folder name is required.', 'error')
            return redirect(url_for('manage_course_mappings'))
        
        # Check if package exists
        test_package = TestPackage.query.get(test_package_id)
        if not test_package:
            flash('Test package not found.', 'error')
            return redirect(url_for('manage_course_mappings'))
        
        # Check if mapping already exists
        existing_mapping = CourseAzureMapping.query.filter_by(
            test_package_id=test_package_id
        ).first()
        
        if existing_mapping:
            flash(f'Mapping already exists for {test_package.title}.', 'error')
            return redirect(url_for('manage_course_mappings'))
        
        # Create new mapping
        mapping = CourseAzureMapping(
            test_package_id=test_package_id,
            azure_folder_name=azure_folder_name,
            practice_test_folder=practice_test_folder,
            created_by=current_user.id
        )
        
        db.session.add(mapping)
        db.session.commit()
        
        flash(f'✅ Created mapping: {test_package.title} → {azure_folder_name}', 'success')
        logger.info(f"Created Azure mapping: {test_package.title} -> {azure_folder_name}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating course mapping: {str(e)}")
        flash(f'Error creating mapping: {str(e)}', 'error')
    
    return redirect(url_for('manage_course_mappings'))

@app.route('/admin/course-mappings/<int:mapping_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_course_mapping(mapping_id):
    """Edit an existing course mapping"""
    try:
        mapping = CourseAzureMapping.query.get_or_404(mapping_id)
        
        azure_folder_name = request.form.get('azure_folder_name', '').strip()
        practice_test_folder = request.form.get('practice_test_folder', 'practice-test-1').strip()
        is_active = request.form.get('is_active') == 'true'
        
        if not azure_folder_name:
            flash('Azure folder name is required.', 'error')
            return redirect(url_for('manage_course_mappings'))
        
        # Update mapping
        mapping.azure_folder_name = azure_folder_name
        mapping.practice_test_folder = practice_test_folder
        mapping.is_active = is_active
        
        db.session.commit()
        
        flash(f'✅ Updated mapping for {mapping.test_package.title}', 'success')
        logger.info(f"Updated Azure mapping: {mapping.test_package.title} -> {azure_folder_name}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating course mapping: {str(e)}")
        flash(f'Error updating mapping: {str(e)}', 'error')
    
    return redirect(url_for('manage_course_mappings'))

@app.route('/admin/course-mappings/<int:mapping_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_course_mapping(mapping_id):
    """Delete a course mapping"""
    try:
        mapping = CourseAzureMapping.query.get_or_404(mapping_id)
        package_title = mapping.test_package.title
        
        db.session.delete(mapping)
        db.session.commit()
        
        flash(f'✅ Deleted mapping for {package_title}', 'success')
        logger.info(f"Deleted Azure mapping for {package_title}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting course mapping: {str(e)}")
        flash(f'Error deleting mapping: {str(e)}', 'error')
    
    return redirect(url_for('manage_course_mappings'))

@app.route('/admin/course-mappings/test-url/<int:mapping_id>')
@login_required
@admin_required
def test_azure_url(mapping_id):
    """Test Azure URL generation for a mapping"""
    try:
        mapping = CourseAzureMapping.query.get_or_404(mapping_id)
        
        # Test with a sample image filename
        test_filename = 'test-image.png'
        test_url = azure_service.generate_image_url(mapping.test_package_id, test_filename)
        
        return jsonify({
            'success': True,
            'test_url': test_url,
            'package_title': mapping.test_package.title,
            'azure_folder': mapping.azure_folder_name,
            'practice_folder': mapping.practice_test_folder
        })
        
    except Exception as e:
        logger.error(f"Error testing Azure URL: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/admin/course-mappings/bulk-process')
@login_required
@admin_required
def bulk_process_images():
    """Page for bulk processing existing questions"""
    mappings = CourseAzureMapping.query.filter_by(is_active=True).all()
    
    # Get statistics for each mapping
    mapping_stats = []
    for mapping in mappings:
        from models import Question, AnswerOption
        
        # Count questions with IMAGE: references but no processed text
        unprocessed_questions = Question.query.filter(
            Question.test_package_id == mapping.test_package_id,
            Question.question_text.like('%IMAGE:%'),
            Question.processed_question_text.is_(None)
        ).count()
        
        # Count answer options with IMAGE: references but no processed text
        unprocessed_options = AnswerOption.query.join(Question).filter(
            Question.test_package_id == mapping.test_package_id,
            AnswerOption.option_text.like('%IMAGE:%'),
            AnswerOption.processed_option_text.is_(None)
        ).count()
        
        mapping_stats.append({
            'mapping': mapping,
            'unprocessed_questions': unprocessed_questions,
            'unprocessed_options': unprocessed_options
        })
    
    return render_template('admin/bulk_process_images.html', 
                         mapping_stats=mapping_stats)

@app.route('/admin/course-mappings/process/<int:mapping_id>', methods=['POST'])
@login_required
@admin_required
def process_mapping_images(mapping_id):
    """Process all unprocessed images for a specific mapping"""
    try:
        mapping = CourseAzureMapping.query.get_or_404(mapping_id)
        
        # Import here to avoid circular imports
        from image_processor import image_processor
        from models import Question, AnswerOption
        
        processed_count = 0
        
        # Process questions
        unprocessed_questions = Question.query.filter(
            Question.test_package_id == mapping.test_package_id,
            Question.question_text.like('%IMAGE:%'),
            Question.processed_question_text.is_(None)
        ).all()
        
        for question in unprocessed_questions:
            if image_processor.has_image_references(question.question_text):
                question.processed_question_text = image_processor.process_text_for_azure(
                    question.question_text, mapping.test_package_id
                )
                processed_count += 1
            
            if question.overall_explanation and image_processor.has_image_references(question.overall_explanation):
                question.processed_explanation = image_processor.process_text_for_azure(
                    question.overall_explanation, mapping.test_package_id
                )
        
        # Process answer options
        unprocessed_options = AnswerOption.query.join(Question).filter(
            Question.test_package_id == mapping.test_package_id,
            AnswerOption.option_text.like('%IMAGE:%'),
            AnswerOption.processed_option_text.is_(None)
        ).all()
        
        for option in unprocessed_options:
            if image_processor.has_image_references(option.option_text):
                option.processed_option_text = image_processor.process_text_for_azure(
                    option.option_text, mapping.test_package_id
                )
                processed_count += 1
            
            if option.explanation and image_processor.has_image_references(option.explanation):
                option.processed_explanation = image_processor.process_text_for_azure(
                    option.explanation, mapping.test_package_id
                )
        
        db.session.commit()
        
        flash(f'✅ Processed {processed_count} images for {mapping.test_package.title}', 'success')
        logger.info(f"Processed {processed_count} images for {mapping.test_package.title}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing images: {str(e)}")
        flash(f'Error processing images: {str(e)}', 'error')
    
    return redirect(url_for('bulk_process_images'))