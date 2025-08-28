"""
Complete Production Utils.py for PrepMyCert
Full implementation with pre-processing and zero runtime overhead.
"""

import pandas as pd
import re
import os
import json
from flask import current_app
from models import Question, AnswerOption, TestPackage
from app import db

# =============================================================================
# IMAGE PRE-PROCESSING FUNCTIONS (Core of the new system)
# =============================================================================

def preprocess_text_content(text, azure_folder_name=None):
    """
    PRE-PROCESS text content during CSV import (ONE-TIME processing).
    Converts image hashes to direct Azure URLs and stores ready-to-display HTML.
    
    This is the key function that eliminates runtime processing!
    
    Args:
        text (str): Raw text content with image hashes
        azure_folder_name (str): Azure folder name for this package
    
    Returns:
        str: Pre-processed HTML with direct image URLs
    """
    if not text or pd.isna(text):
        return ""
    
    text = str(text)
    processed_text = text
    images_processed = 0
    
    # Pattern 1: Direct image hashes (new format)
    # Matches: 74f7b4a1b01300dc94f2de0e704e2258 (32+ char hex strings)
    direct_image_pattern = r'\b([a-f0-9]{32,64})\b'
    
    def replace_image_hash(match):
        nonlocal images_processed
        image_hash = match.group(1)
        
        # Generate direct Azure URL (no API calls!)
        direct_url = generate_direct_azure_url(azure_folder_name, image_hash)
        
        if direct_url:
            images_processed += 1
            # Return ready-to-display HTML
            return f'''<div class="question-image-container">
    <img src="{direct_url}" 
         alt="Question Image" 
         class="img-fluid question-image azure-image" 
         style="max-width: 100%; height: auto; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);"
         loading="lazy"
         onclick="openImageModal(this.src)">
</div>'''
        else:
            # Fallback: keep the hash as text (shouldn't happen in production)
            return image_hash
    
    # Process direct image hashes
    processed_text = re.sub(direct_image_pattern, replace_image_hash, processed_text, flags=re.IGNORECASE)
    
    # Pattern 2: Old format compatibility [IMAGE: filename.png] or IMAGE: filename.png
    old_image_pattern = r'\[?IMAGE:\s*([^\s\[\]]+\.(png|jpg|jpeg|gif|svg))\]?'
    
    def replace_old_format_image(match):
        nonlocal images_processed
        image_filename = match.group(1)
        
        # Try Azure first, then local fallback
        direct_url = generate_direct_azure_url(azure_folder_name, image_filename)
        
        if direct_url:
            images_processed += 1
            return f'''<div class="question-image-container">
    <img src="{direct_url}" 
         alt="{image_filename}" 
         class="img-fluid question-image azure-image" 
         style="max-width: 100%; height: auto; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);"
         loading="lazy"
         onclick="openImageModal(this.src)">
</div>'''
        else:
            # Local fallback for development
            local_url = f"/static/images/questions/{image_filename}"
            images_processed += 1
            return f'''<div class="question-image-container">
    <img src="{local_url}" 
         alt="{image_filename}" 
         class="img-fluid question-image local-image" 
         style="max-width: 100%; height: auto; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);"
         loading="lazy"
         onclick="openImageModal(this.src)">
</div>'''
    
    # Process old format images
    processed_text = re.sub(old_image_pattern, replace_old_format_image, processed_text, flags=re.IGNORECASE)
    
    return processed_text

def generate_direct_azure_url(folder_name, image_name):
    """
    Generate direct Azure Blob Storage URLs WITHOUT API calls.
    This is the key to zero runtime overhead!
    
    Format: https://{account}.blob.core.windows.net/{container}/{folder}/{image}.png
    
    Args:
        folder_name (str): Azure folder name (e.g., 'ai-102')
        image_name (str): Image name or hash
    
    Returns:
        str: Direct Azure URL or None if not configured
    """
    if not folder_name:
        return None
    
    try:
        # Get Azure configuration from environment
        connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        container_name = os.environ.get('AZURE_STORAGE_CONTAINER_NAME', 'certification-images')
        
        if not connection_string:
            return None
        
        # Extract account name from connection string
        account_match = re.search(r'AccountName=([^;]+)', connection_string)
        if not account_match:
            return None
        
        account_name = account_match.group(1)
        
        # Ensure image has .png extension (most common for certification images)
        if not re.search(r'\.(png|jpg|jpeg|gif|svg)$', image_name, re.IGNORECASE):
            image_name += '.png'
        
        # Generate direct URL
        direct_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{folder_name}/{image_name}"
        
        return direct_url
        
    except Exception as e:
        print(f"Warning: Failed to generate Azure URL for {image_name}: {e}")
        return None

def detect_and_count_images(text):
    """
    Detect and count images in text for statistics.
    Used during import for reporting purposes.
    
    Args:
        text (str): Text to analyze
    
    Returns:
        dict: Image detection results
    """
    if not text or pd.isna(text):
        return {"hashes": [], "old_format": [], "total": 0}
    
    text = str(text)
    
    # Detect direct image hashes
    hash_pattern = r'\b([a-f0-9]{32,64})\b'
    hashes = re.findall(hash_pattern, text, flags=re.IGNORECASE)
    
    # Detect old format images
    old_pattern = r'\[?IMAGE:\s*([^\s\[\]]+\.(png|jpg|jpeg|gif|svg))\]?'
    old_matches = re.findall(old_pattern, text, flags=re.IGNORECASE)
    old_format = [match[0] for match in old_matches]
    
    return {
        "hashes": hashes,
        "old_format": old_format,
        "total": len(hashes) + len(old_format)
    }

# =============================================================================
# ENHANCED CSV IMPORT SYSTEM (Multiple Question Types)
# =============================================================================

def import_questions_from_csv(file, test_package_id):
    """
    Complete CSV import system with pre-processing and multiple question types.
    This is where the magic happens - ONE-TIME processing during import!
    
    Supports:
    - Multiple Choice (existing)
    - Fill-in-the-Blanks (new)
    - True/False (new)
    - Code Completion (new)
    
    Args:
        file: CSV file object
        test_package_id (int): ID of the test package
    
    Returns:
        dict: Detailed import statistics
    """
    try:
        # Read CSV
        df = pd.read_csv(file)
        
        # Get package info
        test_package = TestPackage.query.get(test_package_id)
        if not test_package:
            raise ValueError("Test package not found")
        
        package_name = test_package.title
        azure_folder_name = test_package.azure_folder_name
        
        print(f"Starting import for package: {package_name}")
        print(f"Azure folder: {azure_folder_name or 'Not configured (using local storage)'}")
        
        # Import statistics
        stats = {
            'total_rows': len(df),
            'imported': 0,
            'skipped': 0,
            'errors': 0,
            'question_types': {},
            'images_processed': 0,
            'azure_enabled': bool(azure_folder_name)
        }
        
        question_types_used = set()
        
        for index, row in df.iterrows():
            try:
                # Skip empty rows
                if pd.isna(row.get('Question', '')) or str(row.get('Question', '')).strip() == '':
                    stats['skipped'] += 1
                    continue
                
                # Determine question type
                question_type = str(row.get('Question Type', 'multiple-choice')).lower().strip()
                if question_type == '':
                    question_type = 'multiple-choice'
                
                # Normalize question type names
                type_mapping = {
                    'multiple-choice': 'multiple-choice',
                    'multiple_choice': 'multiple-choice',
                    'mcq': 'multiple-choice',
                    'fill-in-blanks': 'fill-in-blanks',
                    'fill_in_blanks': 'fill-in-blanks',
                    'fill-in-the-blanks': 'fill-in-blanks',
                    'blanks': 'fill-in-blanks',
                    'true-false': 'true-false',
                    'true_false': 'true-false',
                    'tf': 'true-false',
                    'boolean': 'true-false',
                    'code-completion': 'code-completion',
                    'code_completion': 'code-completion',
                    'code': 'code-completion',
                    'programming': 'code-completion'
                }
                
                question_type = type_mapping.get(question_type, 'multiple-choice')
                question_types_used.add(question_type)
                
                # Count question types
                if question_type in stats['question_types']:
                    stats['question_types'][question_type] += 1
                else:
                    stats['question_types'][question_type] = 1
                
                # PRE-PROCESS question text (THE KEY IMPROVEMENT!)
                raw_question_text = str(row['Question']).strip()
                processed_question_text = preprocess_text_content(raw_question_text, azure_folder_name)
                
                # Count images in question
                question_images = detect_and_count_images(raw_question_text)
                stats['images_processed'] += question_images['total']
                
                # PRE-PROCESS explanation
                raw_explanation = str(row.get('Overall Explanation', '')).strip()
                processed_explanation = preprocess_text_content(raw_explanation, azure_folder_name) if raw_explanation and raw_explanation != 'nan' else ''
                
                # Count images in explanation
                explanation_images = detect_and_count_images(raw_explanation)
                stats['images_processed'] += explanation_images['total']
                
                # Create question with pre-processed content
                question = Question(
                    test_package_id=test_package_id,
                    question_text=processed_question_text,  # Pre-processed HTML!
                    overall_explanation=processed_explanation,  # Pre-processed HTML!
                    domain=str(row.get('Domain', 'General')).strip(),
                    question_type=question_type,
                    difficulty_level=str(row.get('Difficulty', 'medium')).lower(),
                    points=int(row.get('Points', 1)) if pd.notna(row.get('Points')) else 1,
                    is_processed=True,  # Mark as pre-processed
                    images_count=question_images['total'] + explanation_images['total']
                )
                
                # Handle different question types
                if question_type == 'fill-in-blanks':
                    # Process fill-in-the-blanks data
                    blanks_data = process_fill_in_blanks(row)
                    question.blanks_data = blanks_data
                
                elif question_type == 'code-completion':
                    # Process code completion data
                    question.code_language = str(row.get('Language', 'python')).lower()
                    question.starter_code = str(row.get('Starter Code', ''))
                    question.expected_solution = str(row.get('Expected Solution', ''))
                
                db.session.add(question)
                db.session.flush()  # Get question ID
                
                # Process answer options (different for each question type)
                if question_type == 'multiple-choice':
                    process_multiple_choice_options(question, row, azure_folder_name, stats)
                
                elif question_type == 'true-false':
                    process_true_false_options(question, row, azure_folder_name, stats)
                
                elif question_type == 'fill-in-blanks':
                    # Fill-in-blanks doesn't need traditional options
                    pass
                
                elif question_type == 'code-completion':
                    # Code completion uses the expected solution as the answer
                    pass
                
                stats['imported'] += 1
                
            except Exception as e:
                print(f"Error processing row {index}: {e}")
                stats['errors'] += 1
                continue
        
        # Update package metadata
        test_package.total_questions = stats['imported']
        test_package.question_types = list(question_types_used)
        test_package.last_updated = pd.Timestamp.now()
        
        db.session.commit()
        
        # Final statistics
        stats['package_info'] = {
            'id': test_package_id,
            'title': package_name,
            'azure_folder': azure_folder_name,
            'total_questions': stats['imported'],
            'question_types': list(question_types_used)
        }
        
        print(f"Import completed: {stats['imported']} questions, {stats['images_processed']} images processed")
        return stats
        
    except Exception as e:
        db.session.rollback()
        raise e

def process_multiple_choice_options(question, row, azure_folder_name, stats):
    """Process multiple choice answer options with pre-processing"""
    correct_answers = str(row.get('Correct Answers', '1')).strip()
    correct_answer_nums = []
    
    if correct_answers and correct_answers.lower() != 'nan':
        correct_answer_nums = [int(num) for num in re.findall(r'\d+', correct_answers)]
    else:
        correct_answer_nums = [1]  # Default to first option
    
    # Process up to 6 answer options
    for i in range(1, 7):
        option_text = row.get(f'Answer Option {i}', '')
        explanation = row.get(f'Explanation {i}', '')
        
        if option_text and str(option_text).strip() and str(option_text).strip().lower() != 'nan':
            is_correct = i in correct_answer_nums
            
            # PRE-PROCESS option text and explanation
            raw_option = str(option_text).strip()
            processed_option = preprocess_text_content(raw_option, azure_folder_name)
            
            processed_explanation = ''
            if explanation and str(explanation).strip().lower() != 'nan':
                raw_explanation = str(explanation).strip()
                processed_explanation = preprocess_text_content(raw_explanation, azure_folder_name)
            
            # Count images in options
            option_images = detect_and_count_images(raw_option)
            explanation_images = detect_and_count_images(str(explanation) if explanation else '')
            stats['images_processed'] += option_images['total'] + explanation_images['total']
            
            answer_option = AnswerOption(
                question_id=question.id,
                option_text=processed_option,  # Pre-processed HTML!
                explanation=processed_explanation,  # Pre-processed HTML!
                is_correct=is_correct,
                option_order=i,
                is_processed=True  # Mark as pre-processed
            )
            db.session.add(answer_option)

def process_true_false_options(question, row, azure_folder_name, stats):
    """Process true/false answer options"""
    correct_answer = str(row.get('Correct Answers', '1')).strip().lower()
    
    # Determine if True (1) or False (2) is correct
    true_is_correct = correct_answer in ['1', 'true', 'yes', 't', 'y']
    
    # Create True option
    true_option = AnswerOption(
        question_id=question.id,
        option_text="True",
        explanation="",
        is_correct=true_is_correct,
        option_order=1,
        is_processed=True
    )
    db.session.add(true_option)
    
    # Create False option
    false_option = AnswerOption(
        question_id=question.id,
        option_text="False",
        explanation="",
        is_correct=not true_is_correct,
        option_order=2,
        is_processed=True
    )
    db.session.add(false_option)

def process_fill_in_blanks(row):
    """Process fill-in-the-blanks question data"""
    blanks_data = {
        'blanks': [],
        'case_sensitive': False
    }
    
    # Extract blanks (up to 5)
    for i in range(1, 6):
        blank_answer = row.get(f'Blank {i}', '')
        if blank_answer and str(blank_answer).strip() and str(blank_answer).strip().lower() != 'nan':
            blanks_data['blanks'].append(str(blank_answer).strip())
    
    # Check case sensitivity
    case_sensitive = str(row.get('Case Sensitive', 'false')).lower()
    blanks_data['case_sensitive'] = case_sensitive in ['true', 'yes', '1', 'y']
    
    return blanks_data

# =============================================================================
# VALIDATION AND TESTING FUNCTIONS
# =============================================================================

def validate_csv_format(file):
    """
    Validate CSV file format for all supported question types.
    
    Args:
        file: CSV file object
    
    Returns:
        tuple: (is_valid: bool, error_message: str, detected_types: list)
    """
    try:
        df = pd.read_csv(file)
        
        # Check required columns
        required_columns = ['Question']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}", []
        
        # Detect question types
        detected_types = set()
        validation_errors = []
        
        for index, row in df.head(10).iterrows():  # Check first 10 rows
            question_type = str(row.get('Question Type', 'multiple-choice')).lower()
            
            if question_type in ['', 'nan']:
                question_type = 'multiple-choice'
            
            # Normalize type
            if question_type in ['multiple-choice', 'multiple_choice', 'mcq']:
                detected_types.add('multiple-choice')
                # Check for answer options
                if not row.get('Answer Option 1'):
                    validation_errors.append(f"Row {index}: Multiple choice questions need Answer Option 1")
            
            elif question_type in ['fill-in-blanks', 'fill_in_blanks', 'blanks']:
                detected_types.add('fill-in-blanks')
                # Check for blank answers
                if not row.get('Blank 1'):
                    validation_errors.append(f"Row {index}: Fill-in-blanks questions need Blank 1")
            
            elif question_type in ['true-false', 'true_false', 'tf', 'boolean']:
                detected_types.add('true-false')
            
            elif question_type in ['code-completion', 'code_completion', 'code']:
                detected_types.add('code-completion')
                # Check for code fields
                if not row.get('Expected Solution'):
                    validation_errors.append(f"Row {index}: Code completion needs Expected Solution")
            
            else:
                detected_types.add('multiple-choice')  # Default fallback
        
        if validation_errors:
            return False, '\n'.join(validation_errors[:5]), list(detected_types)  # Show first 5 errors
        
        return True, None, list(detected_types)
        
    except Exception as e:
        return False, f"Error reading CSV file: {str(e)}", []

def test_azure_connection(azure_folder_name=None):
    """
    Test Azure Blob Storage connection and URL generation.
    
    Args:
        azure_folder_name (str): Optional folder to test
    
    Returns:
        dict: Test results
    """
    results = {
        'connection_configured': False,
        'url_generation_working': False,
        'test_urls': [],
        'errors': []
    }
    
    try:
        # Check environment variables
        connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        container_name = os.environ.get('AZURE_STORAGE_CONTAINER_NAME')
        
        if not connection_string:
            results['errors'].append("AZURE_STORAGE_CONNECTION_STRING not configured")
            return results
        
        if not container_name:
            results['errors'].append("AZURE_STORAGE_CONTAINER_NAME not configured")
            return results
        
        results['connection_configured'] = True
        
        # Test URL generation
        test_folder = azure_folder_name or 'test-folder'
        test_images = ['test-image.png', '74f7b4a1b01300dc94f2de0e704e2258', 'sample-diagram.jpg']
        
        for image in test_images:
            url = generate_direct_azure_url(test_folder, image)
            if url:
                results['test_urls'].append({
                    'image': image,
                    'url': url
                })
            else:
                results['errors'].append(f"Failed to generate URL for {image}")
        
        results['url_generation_working'] = len(results['test_urls']) > 0
        
    except Exception as e:
        results['errors'].append(f"Test failed: {str(e)}")
    
    return results

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_import_statistics():
    """Get overall import statistics for monitoring"""
    try:
        stats = {
            'total_packages': TestPackage.query.count(),
            'active_packages': TestPackage.query.filter_by(is_active=True).count(),
            'total_questions': Question.query.count(),
            'processed_questions': Question.query.filter_by(is_processed=True).count(),
            'total_options': AnswerOption.query.count(),
        }
        
        # Question type breakdown
        type_counts = db.session.query(
            Question.question_type, 
            db.func.count(Question.id)
        ).group_by(Question.question_type).all()
        
        stats['question_types'] = {qtype: count for qtype, count in type_counts}
        
        # Azure-enabled packages
        azure_packages = TestPackage.query.filter(
            TestPackage.azure_folder_name.isnot(None),
            TestPackage.azure_folder_name != ''
        ).count()
        stats['azure_packages'] = azure_packages
        
        return stats
        
    except Exception as e:
        return {'error': str(e)}

def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    return name + ext

def get_safe_package_folder_name(package_title):
    """Generate a safe folder name from package title"""
    safe_name = package_title.lower().replace(' ', '-')
    safe_name = re.sub(r'[^a-zA-Z0-9\-_]', '-', safe_name)
    safe_name = re.sub(r'-+', '-', safe_name)
    return safe_name.strip('-')