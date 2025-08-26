import pandas as pd
import re
import os
from app import db
from models import Question, AnswerOption, User
from werkzeug.security import generate_password_hash

def process_text_with_images(text, package_name=None, azure_folder_name=None):
    """
    Process text and replace image references with actual img tags.
    
    Supports two formats:
    1. NEW: Direct image names like "74f7b4a1b01300dc94f2de0e704e2258"
    2. OLD: IMAGE: references like "IMAGE: word-image-43535-354.png" or "[IMAGE: word-image-43535-354.png]"
    
    Args:
        text (str): The text to process
        package_name (str): Package name for local storage fallback
        azure_folder_name (str): Azure folder name for blob storage
    
    Returns:
        str: Processed text with img tags
    """
    if not text or pd.isna(text):
        return ""
    
    text = str(text)
    processed_text = text
    
    # Pattern 1: NEW FORMAT - Direct image names (32-character hex strings or similar)
    # Look for standalone image names that look like hashes
    direct_image_pattern = r'\b([a-f0-9]{32}|[a-f0-9]{16,64})\b'
    
    def replace_direct_image(match):
        image_name = match.group(1)
        return convert_image_to_html(image_name, package_name, azure_folder_name)
    
    # Replace direct image names first
    processed_text = re.sub(direct_image_pattern, replace_direct_image, processed_text, flags=re.IGNORECASE)
    
    # Pattern 2: OLD FORMAT - IMAGE: references (for backward compatibility)
    old_image_pattern = r'\[?IMAGE:\s*([^\s\[\]]+\.(png|jpg|jpeg|gif|svg))\]?'
    
    def replace_old_image(match):
        image_filename = match.group(1)
        return convert_image_to_html(image_filename, package_name, azure_folder_name)
    
    # Replace old format IMAGE: references
    processed_text = re.sub(old_image_pattern, replace_old_image, processed_text, flags=re.IGNORECASE)
    
    return processed_text

def convert_image_to_html(image_name, package_name=None, azure_folder_name=None):
    """
    Convert an image name to an HTML img tag with the appropriate URL.
    
    Priority order:
    1. Azure Blob Storage (if azure_folder_name provided)
    2. Local storage with package-specific folder
    3. Local storage in general folder
    
    Args:
        image_name (str): The image filename or hash
        package_name (str): Package name for local storage
        azure_folder_name (str): Azure folder name
    
    Returns:
        str: HTML img tag
    """
    image_url = None
    alt_text = f"Image: {image_name}"
    
    # Try Azure Blob Storage first
    if azure_folder_name:
        try:
            from azure_storage import get_blob_url
            image_url = get_blob_url(azure_folder_name, image_name)
            if image_url:
                # Add CSS classes for styling
                return f'<img src="{image_url}" alt="{alt_text}" class="question-image azure-image" style="max-width: 100%; height: auto; margin: 10px 0;" loading="lazy">'
        except ImportError:
            pass  # Azure not available, fall back to local
        except Exception as e:
            # Log error but don't break the page
            print(f"Warning: Failed to generate Azure URL for {image_name}: {e}")
    
    # Fallback to local storage
    if package_name:
        # Create a safe folder name from package title
        safe_package_name = re.sub(r'[^a-zA-Z0-9\-_]', '_', package_name.lower().replace(' ', '_'))
        image_url = f"/static/images/questions/{safe_package_name}/{image_name}"
    else:
        # General folder
        image_url = f"/static/images/questions/{image_name}"
    
    # Add CSS classes for styling
    return f'<img src="{image_url}" alt="{alt_text}" class="question-image local-image" style="max-width: 100%; height: auto; margin: 10px 0;" loading="lazy">'

def detect_image_references(text):
    """
    Detect all image references in text (both new and old formats).
    Useful for validation and debugging.
    
    Args:
        text (str): Text to analyze
    
    Returns:
        dict: Dictionary with detected images
    """
    if not text or pd.isna(text):
        return {"direct_images": [], "old_format_images": []}
    
    text = str(text)
    
    # Detect direct image names (32+ character hex strings)
    direct_pattern = r'\b([a-f0-9]{32}|[a-f0-9]{16,64})\b'
    direct_images = re.findall(direct_pattern, text, flags=re.IGNORECASE)
    
    # Detect old format IMAGE: references
    old_pattern = r'\[?IMAGE:\s*([^\s\[\]]+\.(png|jpg|jpeg|gif|svg))\]?'
    old_format_matches = re.findall(old_pattern, text, flags=re.IGNORECASE)
    old_format_images = [match[0] for match in old_format_matches]  # Extract filename part
    
    return {
        "direct_images": direct_images,
        "old_format_images": old_format_images,
        "total_images": len(direct_images) + len(old_format_images)
    }

def import_questions_from_csv(file, test_package_id):
    """
    Import questions from CSV file format.
    Updated to work with both old and new image formats.
    
    Expected columns: Question, Question Type, Answer Option 1-6, Explanation 1-6, 
    Correct Answers, Overall Explanation, Domain
    """
    try:
        # Read CSV file
        df = pd.read_csv(file)
        
        imported_count = 0
        skipped_count = 0
        image_stats = {"direct_images": 0, "old_format_images": 0, "total_questions_with_images": 0}
        
        # Get package information for image processing
        from models import TestPackage
        package = TestPackage.query.get(test_package_id)
        package_name = package.title if package else None
        azure_folder_name = package.azure_folder_name if package else None
        
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
            
            # Analyze image references in question text
            question_images = detect_image_references(question_text)
            explanation_images = detect_image_references(overall_explanation)
            
            # Update image statistics
            if question_images["total_images"] > 0 or explanation_images["total_images"] > 0:
                image_stats["total_questions_with_images"] += 1
                image_stats["direct_images"] += question_images["direct_images"].__len__() + explanation_images["direct_images"].__len__()
                image_stats["old_format_images"] += question_images["old_format_images"].__len__() + explanation_images["old_format_images"].__len__()
            
            # Create question with image processing
            question = Question(
                test_package_id=test_package_id,
                question_text=process_text_with_images(question_text, package_name, azure_folder_name),
                question_type=question_type,
                domain=domain,
                overall_explanation=process_text_with_images(overall_explanation, package_name, azure_folder_name)
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
                    
                    # Process images in option text and explanation
                    processed_option_text = process_text_with_images(str(option_text).strip(), package_name, azure_folder_name)
                    processed_explanation = ""
                    if explanation and str(explanation).strip().lower() != 'nan':
                        processed_explanation = process_text_with_images(str(explanation).strip(), package_name, azure_folder_name)
                    
                    answer_option = AnswerOption(
                        question_id=question.id,
                        option_text=processed_option_text,
                        explanation=processed_explanation,
                        is_correct=is_correct,
                        option_order=i
                    )
                    db.session.add(answer_option)
            
            imported_count += 1
        
        db.session.commit()
        
        # Return statistics including image processing info
        return {
            'imported': imported_count,
            'skipped': skipped_count,
            'image_stats': image_stats,
            'package_info': {
                'package_name': package_name,
                'azure_folder_name': azure_folder_name,
                'uses_azure': bool(azure_folder_name)
            }
        }
        
    except Exception as e:
        db.session.rollback()
        raise e

def validate_image_processing(text, package_name=None, azure_folder_name=None):
    """
    Validate image processing for a given text.
    Useful for testing and debugging.
    
    Args:
        text (str): Text to validate
        package_name (str): Package name
        azure_folder_name (str): Azure folder name
    
    Returns:
        dict: Validation results
    """
    if not text:
        return {"valid": True, "images": [], "processed_text": ""}
    
    # Detect images
    detected_images = detect_image_references(text)
    
    # Process text
    processed_text = process_text_with_images(text, package_name, azure_folder_name)
    
    # Count img tags in processed text
    img_tags = re.findall(r'<img[^>]*>', processed_text)
    
    return {
        "valid": len(img_tags) == detected_images["total_images"],
        "detected_images": detected_images,
        "processed_text": processed_text,
        "img_tags_count": len(img_tags),
        "img_tags": img_tags
    }

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