#!/usr/bin/env python3
"""
Command-line tool to process all existing questions and convert IMAGE: references to Azure URLs
"""

import sys
import logging
import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from app import app, db
from models import Question, AnswerOption, CourseAzureMapping, TestPackage
from image_processor import image_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_all_images():
    """Process all questions and answer options with IMAGE: references"""
    with app.app_context():
        logger.info("🔄 Starting bulk Azure image processing...")
        
        # Get all active mappings
        mappings = CourseAzureMapping.query.filter_by(is_active=True).all()
        
        if not mappings:
            logger.error("❌ No active Azure course mappings found. Please create mappings first.")
            return False
        
        logger.info(f"📋 Found {len(mappings)} active course mappings")
        
        total_processed = 0
        total_questions = 0
        total_options = 0
        
        for mapping in mappings:
            logger.info(f"\n📦 Processing: {mapping.test_package.title}")
            logger.info(f"   Azure folder: {mapping.azure_folder_name}/{mapping.practice_test_folder}")
            
            # Process questions for this mapping
            questions_processed = process_questions_for_mapping(mapping)
            options_processed = process_answer_options_for_mapping(mapping)
            
            total_questions += questions_processed
            total_options += options_processed
            total_processed += questions_processed + options_processed
            
            logger.info(f"   ✅ Processed {questions_processed} questions, {options_processed} answer options")
        
        logger.info(f"\n🎉 Bulk processing completed!")
        logger.info(f"   📊 Total items processed: {total_processed}")
        logger.info(f"   📝 Questions: {total_questions}")
        logger.info(f"   📋 Answer options: {total_options}")
        
        return True

def process_questions_for_mapping(mapping):
    """Process questions for a specific mapping"""
    processed_count = 0
    
    # Find questions with IMAGE: references that haven't been processed
    questions = Question.query.filter(
        Question.test_package_id == mapping.test_package_id,
        Question.question_text.like('%IMAGE:%')
    ).all()
    
    for question in questions:
        try:
            # Process question text
            if image_processor.has_image_references(question.question_text):
                if not question.processed_question_text:
                    question.processed_question_text = image_processor.process_text_for_azure(
                        question.question_text, mapping.test_package_id
                    )
                    processed_count += 1
                    logger.debug(f"   📝 Processed question {question.id}")
            
            # Process question explanation
            if question.overall_explanation and image_processor.has_image_references(question.overall_explanation):
                if not question.processed_explanation:
                    question.processed_explanation = image_processor.process_text_for_azure(
                        question.overall_explanation, mapping.test_package_id
                    )
                    logger.debug(f"   📖 Processed explanation for question {question.id}")
            
        except Exception as e:
            logger.error(f"   ❌ Error processing question {question.id}: {str(e)}")
            continue
    
    # Commit changes for this mapping
    try:
        db.session.commit()
        logger.debug(f"   💾 Committed {processed_count} question updates")
    except Exception as e:
        logger.error(f"   ❌ Error committing question updates: {str(e)}")
        db.session.rollback()
        return 0
    
    return processed_count

def process_answer_options_for_mapping(mapping):
    """Process answer options for a specific mapping"""
    processed_count = 0
    
    # Find answer options with IMAGE: references that haven't been processed
    answer_options = AnswerOption.query.join(Question).filter(
        Question.test_package_id == mapping.test_package_id,
        AnswerOption.option_text.like('%IMAGE:%')
    ).all()
    
    for option in answer_options:
        try:
            # Process option text
            if image_processor.has_image_references(option.option_text):
                if not option.processed_option_text:
                    option.processed_option_text = image_processor.process_text_for_azure(
                        option.option_text, mapping.test_package_id
                    )
                    processed_count += 1
                    logger.debug(f"   📋 Processed answer option {option.id}")
            
            # Process option explanation
            if option.explanation and image_processor.has_image_references(option.explanation):
                if not option.processed_explanation:
                    option.processed_explanation = image_processor.process_text_for_azure(
                        option.explanation, mapping.test_package_id
                    )
                    logger.debug(f"   📖 Processed explanation for option {option.id}")
            
        except Exception as e:
            logger.error(f"   ❌ Error processing answer option {option.id}: {str(e)}")
            continue
    
    # Commit changes for this mapping
    try:
        db.session.commit()
        logger.debug(f"   💾 Committed {processed_count} answer option updates")
    except Exception as e:
        logger.error(f"   ❌ Error committing answer option updates: {str(e)}")
        db.session.rollback()
        return 0
    
    return processed_count

def process_specific_package(package_id):
    """Process images for a specific test package"""
    with app.app_context():
        package = TestPackage.query.get(package_id)
        if not package:
            logger.error(f"❌ Test package {package_id} not found")
            return False
        
        mapping = CourseAzureMapping.query.filter_by(
            test_package_id=package_id,
            is_active=True
        ).first()
        
        if not mapping:
            logger.error(f"❌ No active Azure mapping found for {package.title}")
            return False
        
        logger.info(f"🔄 Processing images for: {package.title}")
        
        questions_processed = process_questions_for_mapping(mapping)
        options_processed = process_answer_options_for_mapping(mapping)
        
        total_processed = questions_processed + options_processed
        
        logger.info(f"✅ Processing completed!")
        logger.info(f"   📝 Questions processed: {questions_processed}")
        logger.info(f"   📋 Answer options processed: {options_processed}")
        logger.info(f"   📊 Total items processed: {total_processed}")
        
        return True

def show_statistics():
    """Show statistics about processable images"""
    with app.app_context():
        logger.info("📊 Azure Image Processing Statistics")
        logger.info("=" * 50)
        
        mappings = CourseAzureMapping.query.filter_by(is_active=True).all()
        
        if not mappings:
            logger.info("❌ No active Azure course mappings found")
            return
        
        total_unprocessed_questions = 0
        total_unprocessed_options = 0
        
        for mapping in mappings:
            # Count unprocessed questions
            unprocessed_questions = Question.query.filter(
                Question.test_package_id == mapping.test_package_id,
                Question.question_text.like('%IMAGE:%'),
                Question.processed_question_text.is_(None)
            ).count()
            
            # Count unprocessed answer options
            unprocessed_options = AnswerOption.query.join(Question).filter(
                Question.test_package_id == mapping.test_package_id,
                AnswerOption.option_text.like('%IMAGE:%'),
                AnswerOption.processed_option_text.is_(None)
            ).count()
            
            total_unprocessed_questions += unprocessed_questions
            total_unprocessed_options += unprocessed_options
            
            logger.info(f"\n📦 {mapping.test_package.title}")
            logger.info(f"   Azure folder: {mapping.azure_folder_name}/{mapping.practice_test_folder}")
            logger.info(f"   Unprocessed questions: {unprocessed_questions}")
            logger.info(f"   Unprocessed options: {unprocessed_options}")
        
        logger.info(f"\n📈 Summary:")
        logger.info(f"   Active mappings: {len(mappings)}")
        logger.info(f"   Total unprocessed questions: {total_unprocessed_questions}")
        logger.info(f"   Total unprocessed options: {total_unprocessed_options}")
        logger.info(f"   Total items to process: {total_unprocessed_questions + total_unprocessed_options}")

def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("Azure Image Processor")
        print("Usage:")
        print("  python process_azure_images.py all           - Process all packages")
        print("  python process_azure_images.py package <id>  - Process specific package")
        print("  python process_azure_images.py stats         - Show statistics")
        return
    
    command = sys.argv[1].lower()
    
    if command == "all":
        success = process_all_images()
        sys.exit(0 if success else 1)
    
    elif command == "package":
        if len(sys.argv) < 3:
            logger.error("❌ Package ID required. Usage: python process_azure_images.py package <id>")
            sys.exit(1)
        
        try:
            package_id = int(sys.argv[2])
            success = process_specific_package(package_id)
            sys.exit(0 if success else 1)
        except ValueError:
            logger.error("❌ Invalid package ID. Must be a number.")
            sys.exit(1)
    
    elif command == "stats":
        show_statistics()
    
    else:
        logger.error(f"❌ Unknown command: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main()