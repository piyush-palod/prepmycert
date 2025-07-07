import pandas as pd
import re
import os
from app import db
from models import Question, AnswerOption, User
from werkzeug.security import generate_password_hash

def process_text_with_images(text):
    """
    Process text and replace IMAGE: references with actual img tags
    Example: "IMAGE: word-image-43535-354.png" or "[IMAGE: word-image-43535-354.png]" becomes an img tag
    """
    if not text or pd.isna(text):
        return ""
    
    text = str(text)
    
    # Pattern to match IMAGE: references with or without square brackets
    image_pattern = r'\[?IMAGE:\s*([^\s\[\]]+\.(png|jpg|jpeg|gif|svg))\]?'
    
    def replace_image(match):
        image_filename = match.group(1)
        image_path = f"/static/images/questions/{image_filename}"
        return f'<img src="{image_path}" alt="{image_filename}" class="question-image" style="max-width: 100%; height: auto; margin: 10px 0;">'
    
    # Replace all IMAGE: references with img tags
    processed_text = re.sub(image_pattern, replace_image, text, flags=re.IGNORECASE)
    
    return processed_text

def import_questions_from_csv(file, test_package_id):
    """
    Import questions from CSV file format matching the uploaded sample.
    Expected columns: Question, Question Type, Answer Option 1-6, Explanation 1-6, 
    Correct Answers, Overall Explanation, Domain
    """
    try:
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
            
            # Create question with image processing
            question = Question(
                test_package_id=test_package_id,
                question_text=process_text_with_images(question_text),
                question_type=question_type,
                domain=domain,
                overall_explanation=process_text_with_images(overall_explanation)
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
                    
                    answer_option = AnswerOption(
                        question_id=question.id,
                        option_text=process_text_with_images(str(option_text).strip()),
                        explanation=process_text_with_images(str(explanation).strip()) if explanation and str(explanation).strip().lower() != 'nan' else '',
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
