import pandas as pd
import re
import os
from app import db
from models import Question, AnswerOption, User
from werkzeug.security import generate_password_hash

def process_text_with_images(text, package_name=None):
    """
    Legacy function for backward compatibility.
    Now returns processed text from database if available, otherwise falls back to Azure processing.
    
    For new implementations, use image_processor.get_display_text() directly.
    """
    if not text or pd.isna(text):
        return ""
    
    # For legacy compatibility, just return the text as-is
    # New Azure processing is handled in image_processor.py
    return str(text)

def import_questions_from_csv(file, test_package_id):
    """
    Import questions from CSV file format and process images for Azure.
    Expected columns: Question, Question Type, Answer Option 1-6, Explanation 1-6, 
    Correct Answers, Overall Explanation, Domain
    """
    try:
        # Import image processor
        from image_processor import image_processor
        
        # Read CSV file
        df = pd.read_csv(file)
        
        imported_count = 0
        skipped_count = 0
        
        for _, row in df.iterrows():
            question_text = row['Question']
            question_type = row.get('Question Type', 'multiple-choice')
            domain = row.get('Domain', 'General')
            overall_explanation = row.get('Overall Explanation', '')
            correct_answers = row.get('Correct Answers', '')
            
            # Skip if question already exists
            existing_question = Question.query.filter_by(
                test_package_id=test_package_id,
                question_text=question_text
            ).first()
            
            if existing_question:
                skipped_count += 1
                continue
            
            # Process images for Azure URLs
            processed_question_text = None
            processed_explanation = None
            
            if image_processor.has_image_references(question_text):
                processed_question_text = image_processor.process_text_for_azure(
                    question_text, test_package_id
                )
            
            if overall_explanation and image_processor.has_image_references(overall_explanation):
                processed_explanation = image_processor.process_text_for_azure(
                    overall_explanation, test_package_id
                )
            
            # Create question with both original and processed text
            question = Question(
                test_package_id=test_package_id,
                question_text=question_text,
                question_type=question_type,
                domain=domain,
                overall_explanation=overall_explanation,
                processed_question_text=processed_question_text,
                processed_explanation=processed_explanation
            )
            db.session.add(question)
            db.session.flush()  # To get the question ID
            
            # Parse correct answers (can be multiple numbers like "1,3,5")
            correct_answer_nums = []
            if correct_answers:
                # Handle different formats: "1", "1,3", "1 3", etc.
                correct_answer_nums = re.findall(r'\d+', str(correct_answers))
                correct_answer_nums = [int(num) for num in correct_answer_nums]
            
            # Add answer options
            for i in range(1, 7):  # Up to 6 options
                option_text = row.get(f'Answer Option {i}', '')
                explanation = row.get(f'Explanation {i}', '')
                
                if option_text and str(option_text).strip() and str(option_text).strip().lower() != 'nan':
                    is_correct = i in correct_answer_nums
                    option_text_clean = str(option_text).strip()
                    explanation_clean = str(explanation).strip() if explanation and str(explanation).strip().lower() != 'nan' else ''
                    
                    # Process images for Azure URLs
                    processed_option_text = None
                    processed_option_explanation = None
                    
                    if image_processor.has_image_references(option_text_clean):
                        processed_option_text = image_processor.process_text_for_azure(
                            option_text_clean, test_package_id
                        )
                    
                    if explanation_clean and image_processor.has_image_references(explanation_clean):
                        processed_option_explanation = image_processor.process_text_for_azure(
                            explanation_clean, test_package_id
                        )
                    
                    answer_option = AnswerOption(
                        question_id=question.id,
                        option_text=option_text_clean,
                        explanation=explanation_clean,
                        processed_option_text=processed_option_text,
                        processed_explanation=processed_option_explanation,
                        is_correct=is_correct,
                        option_order=i
                    )
                    db.session.add(answer_option)
            
            imported_count += 1
        
        db.session.commit()
        
        return {
            'imported': imported_count,
            'skipped': skipped_count
        }
        
    except Exception as e:
        db.session.rollback()
        raise e

def create_admin_user():
    """Create an admin user for testing purposes"""
    from models import User
    
    admin_user = User.query.filter_by(email='admin@prepmycert.com').first()
    if not admin_user:
        admin_user = User(
            email='admin@prepmycert.com',
            first_name='Admin',
            last_name='User',
            is_admin=True
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created: admin@prepmycert.com / admin123")
    else:
        print("Admin user already exists")

if __name__ == '__main__':
    from app import app
    with app.app_context():
        create_admin_user()
