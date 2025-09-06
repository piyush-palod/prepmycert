import pandas as pd
import re
import os
from app import db
from models import Course, PracticeTest, Question, AnswerOption
from azure_service import azure_service
import logging

logger = logging.getLogger(__name__)

def normalize_question_type(question_type):
    """
    Normalize question type variations to standard format
    """
    if not question_type:
        return 'multiple-choice'  # default
    
    type_lower = str(question_type).lower().strip()
    
    # Mapping of variations to standard types
    type_mappings = {
        'multi-select': 'multiple-select',
        'multiselect': 'multiple-select',
        'multiple-selection': 'multiple-select',
        'multi-choice': 'multiple-choice',
        'multichoice': 'multiple-choice',
        'single-choice': 'multiple-choice',
        'single-select': 'multiple-choice',
        'true-false': 'true-false',
        'truefalse': 'true-false',
        't/f': 'true-false',
        'boolean': 'true-false',
        'fill-blank': 'fill-blank',
        'fill-in-blank': 'fill-blank',
        'fillblank': 'fill-blank',
        'text-input': 'fill-blank'
    }
    
    # Check if it's already a standard type
    standard_types = ['multiple-choice', 'multiple-select', 'true-false', 'fill-blank']
    if type_lower in standard_types:
        return type_lower
    
    # Try to find a mapping
    normalized = type_mappings.get(type_lower)
    if normalized:
        return normalized
    
    # If no mapping found, log warning and default to multiple-choice
    logger.warning(f"Unknown question type '{question_type}', defaulting to 'multiple-choice'. Supported types: {', '.join(standard_types)}")
    return 'multiple-choice'

def import_questions_from_csv(file, practice_test_id):
    """
    Import questions from CSV file format for the new Course → Practice Test → Question structure.
    Expected columns: Question, Question Type, Answer Option 1-6, Explanation 1-6, 
    Correct Answers, Overall Explanation, Domain
    
    Supported Question Types: multiple-choice, multiple-select, true-false, fill-blank
    """
    try:
        # Read CSV file
        df = pd.read_csv(file)
        
        # Get practice test and course info for Azure folder
        practice_test = PracticeTest.query.get(practice_test_id)
        if not practice_test:
            raise ValueError(f"Practice test with ID {practice_test_id} not found")
        
        course = practice_test.course
        azure_folder = course.azure_folder
        
        imported_count = 0
        skipped_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                question_text = row['Question']
                raw_question_type = row.get('Question Type', 'multiple-choice')
                question_type = normalize_question_type(raw_question_type)
                domain = row.get('Domain', 'General')
                overall_explanation = row.get('Overall Explanation', '')
                correct_answers = row.get('Correct Answers', '')
                
                # Skip if question already exists in this practice test
                existing_question = Question.query.filter_by(
                    practice_test_id=practice_test_id,
                    question_text=question_text
                ).first()
                
                if existing_question:
                    skipped_count += 1
                    continue
                
                # Process question text and explanation with Azure images
                processed_question_text = azure_service.process_text_with_images(
                    question_text, azure_folder
                )
                processed_explanation = azure_service.process_text_with_images(
                    overall_explanation, azure_folder
                ) if overall_explanation else ''
                
                # Create question
                question = Question(
                    practice_test_id=practice_test_id,
                    question_text=processed_question_text,
                    question_type=question_type,
                    domain=domain,
                    overall_explanation=processed_explanation,
                    order_index=imported_count + 1
                )
                db.session.add(question)
                db.session.flush()  # To get the question ID
                
                # Parse correct answers (can be multiple numbers like "1,3,5")
                correct_answer_nums = []
                if correct_answers:
                    # Handle different formats: "1", "1,3", "1 3", etc.
                    correct_answer_nums = re.findall(r'\d+', str(correct_answers))
                    correct_answer_nums = [int(num) for num in correct_answer_nums]
                
                # Validate question type and correct answers compatibility
                if question_type == 'multiple-choice' and len(correct_answer_nums) > 1:
                    logger.warning(f"Row {index + 1}: Multiple correct answers ({correct_answer_nums}) found for 'multiple-choice' question. Consider using 'multiple-select' type instead.")
                
                if question_type == 'multiple-select' and len(correct_answer_nums) <= 1:
                    logger.info(f"Row {index + 1}: Only one correct answer found for 'multiple-select' question. This is valid but consider if 'multiple-choice' would be more appropriate.")
                
                # Add answer options
                for i in range(1, 7):  # Up to 6 options
                    option_text = row.get(f'Answer Option {i}', '')
                    explanation = row.get(f'Explanation {i}', '')
                    
                    if option_text and str(option_text).strip() and str(option_text).strip().lower() != 'nan':
                        is_correct = i in correct_answer_nums
                        
                        # Process option text and explanation with Azure images
                        processed_option_text = azure_service.process_text_with_images(
                            str(option_text).strip(), azure_folder
                        )
                        processed_option_explanation = azure_service.process_text_with_images(
                            str(explanation).strip(), azure_folder
                        ) if explanation and str(explanation).strip().lower() != 'nan' else ''
                        
                        answer_option = AnswerOption(
                            question_id=question.id,
                            option_text=processed_option_text,
                            explanation=processed_option_explanation,
                            is_correct=is_correct,
                            option_order=i
                        )
                        db.session.add(answer_option)
                
                imported_count += 1
                
            except Exception as e:
                logger.error(f"Error importing row {index + 1}: {str(e)}")
                error_count += 1
                continue
        
        db.session.commit()
        
        result = {
            'imported': imported_count,
            'skipped': skipped_count,
            'errors': error_count
        }
        
        if error_count > 0:
            result['message'] = f"Imported {imported_count} questions, skipped {skipped_count} duplicates, {error_count} errors occurred"
        else:
            result['message'] = f"Successfully imported {imported_count} questions, skipped {skipped_count} duplicates"
        
        return result
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in CSV import: {str(e)}")
        raise e



def validate_azure_configuration():
    """Validate Azure configuration and connectivity"""
    try:
        # Check environment variables
        connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        container_name = os.environ.get('AZURE_CONTAINER_NAME', 'certification-images')
        
        if not connection_string:
            return {
                'success': False,
                'error': 'AZURE_STORAGE_CONNECTION_STRING environment variable not set'
            }
        
        # Test Azure connectivity
        test_result = azure_service.list_images('test')  # Try to list images in test folder
        
        return {
            'success': True,
            'message': 'Azure configuration is valid and accessible',
            'container': container_name
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Azure configuration error: {str(e)}'
        }

def generate_question_sample_csv():
    """Generate a sample CSV file format for question import"""
    import io
    
    sample_data = [
        {
            'Question': 'What is the primary benefit of using Azure Cognitive Services?',
            'Question Type': 'multiple-choice',
            'Answer Option 1': 'Reduced infrastructure costs',
            'Answer Option 2': 'Pre-built AI capabilities without deep ML expertise',
            'Answer Option 3': 'Unlimited storage capacity',
            'Answer Option 4': 'Faster network connectivity',
            'Explanation 1': 'While cost reduction can be a benefit, it is not the primary advantage.',
            'Explanation 2': 'Correct! Azure Cognitive Services provides ready-to-use AI APIs that allow developers to add intelligent features without requiring deep machine learning knowledge.',
            'Explanation 3': 'Storage capacity is not the main focus of Cognitive Services.',
            'Explanation 4': 'Network connectivity is not related to Cognitive Services functionality.',
            'Correct Answers': '2',
            'Overall Explanation': 'Azure Cognitive Services democratizes AI by providing pre-built, easy-to-integrate APIs for common AI scenarios like vision, speech, language, and decision-making.',
            'Domain': 'Azure AI Services'
        },
        {
            'Question': 'Which Azure service should you use for document analysis and form processing? IMAGE: form-recognizer-example.png',
            'Question Type': 'multiple-choice',
            'Answer Option 1': 'Azure Computer Vision',
            'Answer Option 2': 'Azure Form Recognizer',
            'Answer Option 3': 'Azure Text Analytics',
            'Answer Option 4': 'Azure Custom Vision',
            'Explanation 1': 'Computer Vision is for general image analysis, not specialized document processing.',
            'Explanation 2': 'Correct! Azure Form Recognizer is specifically designed for extracting text, key-value pairs, and tables from documents and forms.',
            'Explanation 3': 'Text Analytics is for analyzing text sentiment and entities, not document structure.',
            'Explanation 4': 'Custom Vision is for training custom image classification models.',
            'Correct Answers': '2',
            'Overall Explanation': 'Form Recognizer uses advanced machine learning to extract text, key-value pairs, selection marks, and table data from documents.',
            'Domain': 'Document Intelligence'
        },
        {
            'Question': 'Which Azure security features should you implement to protect against data breaches? Select all that apply.',
            'Question Type': 'multiple-select',
            'Answer Option 1': 'Azure Key Vault for secrets management',
            'Answer Option 2': 'Azure Security Center for threat protection',
            'Answer Option 3': 'Azure Active Directory for identity management',
            'Answer Option 4': 'Azure Storage for data backup',
            'Answer Option 5': 'Azure Monitor for logging and alerting',
            'Answer Option 6': '',
            'Explanation 1': 'Correct! Azure Key Vault helps protect cryptographic keys and secrets used by cloud applications and services.',
            'Explanation 2': 'Correct! Azure Security Center provides unified security management and advanced threat protection.',
            'Explanation 3': 'Correct! Azure AD provides identity and access management to help secure your resources.',
            'Explanation 4': 'While important for business continuity, Azure Storage alone does not protect against data breaches.',
            'Explanation 5': 'Correct! Azure Monitor helps detect and respond to security incidents through comprehensive logging and alerting.',
            'Explanation 6': '',
            'Correct Answers': '1,2,3,5',
            'Overall Explanation': 'A comprehensive security strategy requires multiple layers: identity management (Azure AD), secrets protection (Key Vault), threat detection (Security Center), and monitoring (Azure Monitor). Storage is primarily for availability, not breach prevention.',
            'Domain': 'Azure Security'
        }
    ]
    
    df = pd.DataFrame(sample_data)
    
    # Convert to CSV string
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue()