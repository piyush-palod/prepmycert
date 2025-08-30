#!/usr/bin/env python3
"""
Architecture Validation Script - Course > Practice Test > Questions

This script validates that all components of the new architecture are properly integrated:
1. Model relationships and foreign keys
2. Route imports and URL patterns
3. Template references and links
4. Azure integration compatibility

Usage: python3 dev-scripts/validate_new_architecture.py
"""

import os
import sys
import re
import glob
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def validate_model_relationships():
    """Validate database model relationships are properly defined"""
    print("🔍 Validating Model Relationships...")
    
    try:
        # Check models.py file for required model definitions
        models_file = Path(__file__).parent.parent / "models.py"
        with open(models_file, 'r', encoding='utf-8') as f:
            models_content = f.read()
        
        # Check for required model classes
        required_models = ['class Course(', 'class PracticeTest(', 'class Question(', 'class AnswerOption(']
        for model in required_models:
            if model not in models_content:
                print(f"❌ Missing model definition: {model}")
                return False
        
        # Check for key relationships
        required_relationships = [
            'practice_tests = db.relationship', # Course -> PracticeTest
            'questions = db.relationship',      # PracticeTest -> Question  
            'course_id = db.Column',           # PracticeTest -> Course FK
            'practice_test_id = db.Column'     # Question -> PracticeTest FK
        ]
        
        for relationship in required_relationships:
            if relationship not in models_content:
                print(f"❌ Missing relationship: {relationship}")
                return False
        
        print("✅ All model relationships validated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Model validation failed: {str(e)}")
        return False

def validate_route_imports():
    """Validate all route modules are properly imported"""
    print("🔍 Validating Route Imports...")
    
    try:
        # Check main.py imports
        main_py_path = Path(__file__).parent.parent / "main.py"
        with open(main_py_path, 'r') as f:
            main_content = f.read()
            
        required_imports = [
            'import admin_course_routes',
            'from admin_course_routes import *',
            'import routes',
            'from routes import *'
        ]
        
        for import_line in required_imports:
            if import_line not in main_content:
                print(f"❌ Missing import in main.py: {import_line}")
                return False
                
        print("✅ All route imports validated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Route import validation failed: {str(e)}")
        return False

def validate_route_functions():
    """Validate critical route functions exist"""
    print("🔍 Validating Route Functions...")
    
    try:
        # Check routes.py file for critical functions
        routes_file = Path(__file__).parent.parent / "routes.py"
        with open(routes_file, 'r', encoding='utf-8') as f:
            routes_content = f.read()
        
        required_routes = [
            'def course_detail',
            'def take_practice_test', 
            '@app.route(\'/courses\')',
            '@app.route(\'/course/<int:course_id>\')',
            '@app.route(\'/take-practice-test/<int:practice_test_id>\')'
        ]
        
        for route in required_routes:
            if route not in routes_content:
                print(f"❌ Missing route in routes.py: {route}")
                return False
        
        # Check admin_course_routes.py file  
        admin_routes_file = Path(__file__).parent.parent / "admin_course_routes.py"
        with open(admin_routes_file, 'r', encoding='utf-8') as f:
            admin_content = f.read()
            
        required_admin_routes = [
            'def admin_courses',
            'def create_course',
            'def manage_practice_tests',
            '@app.route(\'/admin/courses\')',
            '@app.route(\'/admin/courses/create\')'
        ]
        
        for route in required_admin_routes:
            if route not in admin_content:
                print(f"❌ Missing admin route: {route}")
                return False
        
        print("✅ All route functions validated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Route function validation failed: {str(e)}")
        return False

def validate_template_references():
    """Validate template references and URL patterns"""
    print("🔍 Validating Template References...")
    
    try:
        template_dir = Path(__file__).parent.parent / "templates"
        
        # Key templates that should exist
        required_templates = [
            "courses.html",
            "course_detail.html", 
            "admin/courses.html",
            "admin/create_course.html",
            "admin/manage_practice_tests.html",
            "admin/create_practice_test.html"
        ]
        
        missing_templates = []
        for template in required_templates:
            template_path = template_dir / template
            if not template_path.exists():
                missing_templates.append(template)
        
        if missing_templates:
            print(f"❌ Missing templates: {', '.join(missing_templates)}")
            return False
            
        # Check URL patterns in templates
        html_files = glob.glob(str(template_dir / "**/*.html"), recursive=True)
        
        critical_urls = [
            'course_detail',
            'courses', 
            'take_practice_test',
            'admin_courses',
            'create_course',
            'manage_practice_tests'
        ]
        
        for html_file in html_files:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Check for broken URL references (basic validation)
                if 'url_for(' in content and 'undefined_route' in content:
                    print(f"❌ Potential broken URL reference in {html_file}")
                    return False
                    
        print("✅ Template references validated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Template validation failed: {str(e)}")
        return False

def validate_azure_integration():
    """Validate Azure integration still works with new structure"""
    print("🔍 Validating Azure Integration...")
    
    try:
        # Check azure_service.py exists and has required class
        azure_file = Path(__file__).parent.parent / "azure_service.py"
        if not azure_file.exists():
            print("❌ azure_service.py file not found")
            return False
            
        with open(azure_file, 'r', encoding='utf-8') as f:
            azure_content = f.read()
        
        # Check for AzureService class and key methods
        required_azure_components = [
            'class AzureService',
            'def generate_question_image_url',
            'def upload_blob'
        ]
        
        for component in required_azure_components:
            if component not in azure_content:
                print(f"❌ Missing Azure component: {component}")
                return False
        
        # Check models.py has CourseAzureMapping
        models_file = Path(__file__).parent.parent / "models.py"
        with open(models_file, 'r', encoding='utf-8') as f:
            models_content = f.read()
            
        if 'class CourseAzureMapping' not in models_content:
            print("❌ Missing CourseAzureMapping model")
            return False
            
        if 'course_id = db.Column' not in models_content:
            print("❌ CourseAzureMapping missing course_id field")
            return False
        
        print("✅ Azure integration validated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Azure integration validation failed: {str(e)}")
        return False

def validate_payment_integration():
    """Validate payment processing works with courses"""
    print("🔍 Validating Payment Integration...")
    
    try:
        from models import UserPurchase, Course
        
        # Check UserPurchase has course_id field
        assert hasattr(UserPurchase, 'course_id'), "UserPurchase missing course_id field"
        assert hasattr(UserPurchase, 'is_course_purchase'), "UserPurchase missing is_course_purchase property"
        
        # Check Course has price field for Stripe
        assert hasattr(Course, 'price'), "Course missing price field"
        assert hasattr(Course, 'stripe_price_id'), "Course missing stripe_price_id field"
        
        print("✅ Payment integration validated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Payment integration validation failed: {str(e)}")
        return False

def main():
    """Run all validation checks"""
    print("🚀 Starting Architecture Validation for Course > Practice Test > Questions")
    print("=" * 80)
    
    validation_results = []
    
    # Run all validation checks
    validation_results.append(("Model Relationships", validate_model_relationships()))
    validation_results.append(("Route Imports", validate_route_imports()))
    validation_results.append(("Route Functions", validate_route_functions()))
    validation_results.append(("Template References", validate_template_references()))
    validation_results.append(("Azure Integration", validate_azure_integration()))
    validation_results.append(("Payment Integration", validate_payment_integration()))
    
    print("\n" + "=" * 80)
    print("📊 VALIDATION SUMMARY")
    print("=" * 80)
    
    all_passed = True
    for check_name, passed in validation_results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{check_name:.<50}{status}")
        if not passed:
            all_passed = False
    
    print("=" * 80)
    
    if all_passed:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("")
        print("🚀 Your Course > Practice Test > Questions architecture is ready!")
        print("")
        print("📋 Next Steps:")
        print("   1. Run: python3 dev-scripts/reset_database.py")
        print("   2. Start app: python3 main.py")
        print("   3. Login as admin and test course creation")
        print("   4. Test practice test creation and question management")
        print("   5. Test user flow: browse courses → purchase → take practice tests")
        return True
    else:
        print("💥 SOME VALIDATIONS FAILED!")
        print("Please fix the issues above before proceeding.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)