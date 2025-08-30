#!/usr/bin/env python3
"""
Validation tool for Azure image integration
Checks URLs, validates mappings, and reports issues
"""

import sys
import logging
import requests
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables first
load_dotenv()

from app import app, db
from models import Question, AnswerOption, CourseAzureMapping, TestPackage
from azure_service import azure_service
from image_processor import image_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_azure_configuration():
    """Validate Azure service configuration"""
    logger.info("🔧 Validating Azure configuration...")
    
    if not azure_service.validate_configuration():
        logger.error("❌ Azure configuration is invalid")
        logger.error("   Required environment variables:")
        logger.error("   - AZURE_STORAGE_ACCOUNT_NAME")
        logger.error("   - AZURE_CONTAINER_NAME (optional, defaults to 'certification-images')")
        return False
    
    logger.info("✅ Azure configuration is valid")
    logger.info(f"   Storage Account: {azure_service.storage_account_name}")
    logger.info(f"   Container: {azure_service.container_name}")
    return True

def validate_course_mappings():
    """Validate all course mappings"""
    logger.info("\n📋 Validating course mappings...")
    
    mappings = CourseAzureMapping.query.all()
    
    if not mappings:
        logger.warning("⚠️ No course mappings found")
        return True
    
    valid_mappings = 0
    invalid_mappings = 0
    
    for mapping in mappings:
        logger.info(f"\n📦 {mapping.test_package.title}")
        logger.info(f"   Mapping ID: {mapping.id}")
        logger.info(f"   Azure folder: {mapping.azure_folder_name}")
        logger.info(f"   Practice folder: {mapping.practice_test_folder}")
        logger.info(f"   Status: {'Active' if mapping.is_active else 'Inactive'}")
        
        # Test URL generation
        test_url = azure_service.generate_image_url(mapping.test_package_id, "test-image.png")
        
        if test_url:
            logger.info(f"   ✅ URL generation works: {test_url}")
            valid_mappings += 1
        else:
            logger.error(f"   ❌ URL generation failed")
            invalid_mappings += 1
    
    logger.info(f"\n📊 Mapping validation summary:")
    logger.info(f"   Total mappings: {len(mappings)}")
    logger.info(f"   Valid: {valid_mappings}")
    logger.info(f"   Invalid: {invalid_mappings}")
    
    return invalid_mappings == 0

def validate_image_urls(check_accessibility=False, sample_size=None):
    """Validate processed image URLs"""
    logger.info(f"\n🔗 Validating image URLs (accessibility check: {'ON' if check_accessibility else 'OFF'})...")
    
    if sample_size:
        logger.info(f"   Checking sample of {sample_size} URLs")
    
    # Count processed questions and options
    processed_questions = Question.query.filter(
        Question.processed_question_text.isnot(None)
    ).all()
    
    processed_options = AnswerOption.query.filter(
        AnswerOption.processed_option_text.isnot(None)
    ).all()
    
    logger.info(f"   Processed questions: {len(processed_questions)}")
    logger.info(f"   Processed answer options: {len(processed_options)}")
    
    # Extract and validate URLs
    all_urls = set()
    
    # Extract from questions
    for question in processed_questions[:sample_size] if sample_size else processed_questions:
        urls = extract_urls_from_html(question.processed_question_text)
        all_urls.update(urls)
        
        if question.processed_explanation:
            urls = extract_urls_from_html(question.processed_explanation)
            all_urls.update(urls)
    
    # Extract from answer options
    for option in processed_options[:sample_size] if sample_size else processed_options:
        urls = extract_urls_from_html(option.processed_option_text)
        all_urls.update(urls)
        
        if option.processed_explanation:
            urls = extract_urls_from_html(option.processed_explanation)
            all_urls.update(urls)
    
    logger.info(f"   Unique URLs found: {len(all_urls)}")
    
    if check_accessibility and all_urls:
        return validate_url_accessibility(all_urls, sample_size)
    
    # Basic URL format validation
    valid_urls = 0
    invalid_urls = 0
    
    for url in all_urls:
        if is_valid_azure_url(url):
            valid_urls += 1
        else:
            invalid_urls += 1
            logger.warning(f"   ⚠️ Invalid URL format: {url}")
    
    logger.info(f"\n📊 URL validation summary:")
    logger.info(f"   Total URLs: {len(all_urls)}")
    logger.info(f"   Valid format: {valid_urls}")
    logger.info(f"   Invalid format: {invalid_urls}")
    
    return invalid_urls == 0

def validate_url_accessibility(urls, sample_size=None):
    """Check if URLs are actually accessible"""
    logger.info("🌐 Checking URL accessibility...")
    
    urls_to_check = list(urls)
    if sample_size and len(urls_to_check) > sample_size:
        import random
        urls_to_check = random.sample(urls_to_check, sample_size)
        logger.info(f"   Checking random sample of {len(urls_to_check)} URLs")
    
    accessible_count = 0
    inaccessible_count = 0
    error_count = 0
    
    for i, url in enumerate(urls_to_check, 1):
        try:
            logger.info(f"   [{i}/{len(urls_to_check)}] Checking: {url}")
            
            # Make HEAD request to check if URL is accessible
            response = requests.head(url, timeout=10, allow_redirects=True)
            
            if response.status_code == 200:
                accessible_count += 1
                logger.debug(f"   ✅ Accessible: {url}")
            else:
                inaccessible_count += 1
                logger.warning(f"   ❌ HTTP {response.status_code}: {url}")
                
        except requests.exceptions.RequestException as e:
            error_count += 1
            logger.error(f"   💥 Error checking {url}: {str(e)}")
        
        # Progress indicator
        if i % 10 == 0:
            logger.info(f"   Progress: {i}/{len(urls_to_check)} ({(i/len(urls_to_check)*100):.1f}%)")
    
    logger.info(f"\n📊 URL accessibility summary:")
    logger.info(f"   Checked: {len(urls_to_check)}")
    logger.info(f"   Accessible (200): {accessible_count}")
    logger.info(f"   Inaccessible: {inaccessible_count}")
    logger.info(f"   Errors: {error_count}")
    
    success_rate = (accessible_count / len(urls_to_check)) * 100 if urls_to_check else 0
    logger.info(f"   Success rate: {success_rate:.1f}%")
    
    return success_rate > 80  # Consider 80%+ success rate as good

def extract_urls_from_html(html_text):
    """Extract Azure Blob URLs from HTML text"""
    import re
    
    if not html_text:
        return []
    
    # Pattern to match Azure Blob Storage URLs in img tags
    url_pattern = r'src="(https://[^"]*\.blob\.core\.windows\.net[^"]*)"'
    matches = re.findall(url_pattern, html_text)
    
    return matches

def is_valid_azure_url(url):
    """Check if URL matches expected Azure Blob Storage format"""
    try:
        parsed = urlparse(url)
        
        # Check if it's an Azure Blob Storage URL
        if not parsed.hostname or not parsed.hostname.endswith('.blob.core.windows.net'):
            return False
        
        # Check if path contains expected structure
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 3:  # container/course/practice-test/filename
            return False
        
        return True
        
    except Exception:
        return False

def find_unprocessed_images():
    """Find questions/options with IMAGE: references that haven't been processed"""
    logger.info("\n🔍 Finding unprocessed images...")
    
    # Questions with IMAGE: references but no processed text
    unprocessed_questions = Question.query.filter(
        Question.question_text.like('%IMAGE:%'),
        Question.processed_question_text.is_(None)
    ).all()
    
    # Answer options with IMAGE: references but no processed text
    unprocessed_options = AnswerOption.query.filter(
        AnswerOption.option_text.like('%IMAGE:%'),
        AnswerOption.processed_option_text.is_(None)
    ).all()
    
    logger.info(f"   Unprocessed questions: {len(unprocessed_questions)}")
    logger.info(f"   Unprocessed answer options: {len(unprocessed_options)}")
    
    if unprocessed_questions or unprocessed_options:
        logger.info("\n   Unprocessed items by course:")
        
        # Group by test package
        packages = {}
        
        for question in unprocessed_questions:
            package_id = question.test_package_id
            if package_id not in packages:
                packages[package_id] = {'questions': 0, 'options': 0, 'package': question.test_package}
            packages[package_id]['questions'] += 1
        
        for option in unprocessed_options:
            package_id = option.question.test_package_id
            if package_id not in packages:
                packages[package_id] = {'questions': 0, 'options': 0, 'package': option.question.test_package}
            packages[package_id]['options'] += 1
        
        for package_id, data in packages.items():
            logger.info(f"   📦 {data['package'].title}")
            logger.info(f"      Questions: {data['questions']}, Options: {data['options']}")
            
            # Check if mapping exists
            mapping = CourseAzureMapping.query.filter_by(
                test_package_id=package_id,
                is_active=True
            ).first()
            
            if not mapping:
                logger.warning(f"      ⚠️ No active Azure mapping found!")
            else:
                logger.info(f"      ✅ Mapping exists: {mapping.azure_folder_name}")
    
    return len(unprocessed_questions) + len(unprocessed_options)

def generate_validation_report():
    """Generate comprehensive validation report"""
    logger.info("📝 Generating validation report...")
    
    report = {
        'azure_config': validate_azure_configuration(),
        'mappings': validate_course_mappings(),
        'urls': validate_image_urls(check_accessibility=False),
        'unprocessed_count': find_unprocessed_images()
    }
    
    logger.info("\n" + "="*50)
    logger.info("📊 VALIDATION REPORT SUMMARY")
    logger.info("="*50)
    
    overall_status = "✅ PASS" if all([
        report['azure_config'],
        report['mappings'],
        report['urls'],
        report['unprocessed_count'] == 0
    ]) else "❌ ISSUES FOUND"
    
    logger.info(f"Overall Status: {overall_status}")
    logger.info(f"Azure Config: {'✅ Valid' if report['azure_config'] else '❌ Invalid'}")
    logger.info(f"Course Mappings: {'✅ Valid' if report['mappings'] else '❌ Issues'}")
    logger.info(f"URL Format: {'✅ Valid' if report['urls'] else '❌ Issues'}")
    logger.info(f"Unprocessed Items: {report['unprocessed_count']}")
    
    if report['unprocessed_count'] > 0:
        logger.info(f"\n💡 To process unprocessed items, run:")
        logger.info(f"   python process_azure_images.py all")
    
    return overall_status == "✅ PASS"

def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("Azure Image Validator")
        print("Usage:")
        print("  python validate_azure_images.py config       - Validate Azure configuration")
        print("  python validate_azure_images.py mappings     - Validate course mappings")
        print("  python validate_azure_images.py urls         - Validate URL formats")
        print("  python validate_azure_images.py accessibility [sample_size] - Check URL accessibility")
        print("  python validate_azure_images.py unprocessed  - Find unprocessed images")
        print("  python validate_azure_images.py report       - Full validation report")
        return
    
    command = sys.argv[1].lower()
    
    with app.app_context():
        if command == "config":
            success = validate_azure_configuration()
            
        elif command == "mappings":
            success = validate_course_mappings()
            
        elif command == "urls":
            success = validate_image_urls(check_accessibility=False)
            
        elif command == "accessibility":
            sample_size = None
            if len(sys.argv) > 2:
                try:
                    sample_size = int(sys.argv[2])
                except ValueError:
                    logger.error("❌ Invalid sample size. Must be a number.")
                    sys.exit(1)
            
            success = validate_image_urls(check_accessibility=True, sample_size=sample_size)
            
        elif command == "unprocessed":
            unprocessed_count = find_unprocessed_images()
            success = unprocessed_count == 0
            
        elif command == "report":
            success = generate_validation_report()
            
        else:
            logger.error(f"❌ Unknown command: {command}")
            sys.exit(1)
        
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()