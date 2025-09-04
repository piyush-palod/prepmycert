#!/usr/bin/env python3
"""Import Azure questions from the provided CSV file"""

from app import app, db
from models import Course, PracticeTest
from utils import import_questions_from_csv
import os

def import_azure_questions():
    """Import questions from the provided Azure CSV file"""
    with app.app_context():
        # Create or get Azure course
        azure_course = Course.query.filter_by(title='Microsoft Azure Fundamentals AZ-900').first()
        if not azure_course:
            azure_course = Course(
                title='Microsoft Azure Fundamentals AZ-900',
                description='Master Azure cloud fundamentals with comprehensive AZ-900 certification preparation. Covers Azure services, pricing, security, and governance.',
                price=42.99,
                domain='Cloud Computing',
                azure_folder='az-900'  # Azure folder for images
            )
            db.session.add(azure_course)
            db.session.flush()  # Get the course ID
            print("✅ Created Azure Fundamentals course")
        else:
            print("ℹ️ Azure Fundamentals course already exists")
        
        # Create or get practice test within the course
        practice_test = PracticeTest.query.filter_by(
            course_id=azure_course.id,
            title='AZ-900 Practice Test'
        ).first()
        
        if not practice_test:
            practice_test = PracticeTest(
                course_id=azure_course.id,
                title='AZ-900 Practice Test',
                description='Comprehensive practice test for Azure Fundamentals certification',
                time_limit_minutes=60,  # 60 minutes time limit
                order_index=1
            )
            db.session.add(practice_test)
            db.session.flush()  # Get the practice test ID
            print("✅ Created AZ-900 Practice Test")
        else:
            print("ℹ️ AZ-900 Practice Test already exists")
        
        db.session.commit()
        
        # Import questions from CSV
        csv_path = 'attached_assets/p5_1751843506788.csv'
        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r', encoding='utf-8') as file:
                    result = import_questions_from_csv(file, practice_test.id)
                    print(f"✅ Imported {result['imported']} Azure questions, skipped {result['skipped']} duplicates")
                    if result.get('errors', 0) > 0:
                        print(f"⚠️ {result['errors']} errors occurred during import")
            except Exception as e:
                print(f"❌ Error importing questions: {str(e)}")
        else:
            print(f"❌ CSV file not found at {csv_path}")
            print("ℹ️ Available files in attached_assets:")
            if os.path.exists('attached_assets'):
                for file in os.listdir('attached_assets'):
                    if file.endswith('.csv'):
                        print(f"  - {file}")
            else:
                print("  No attached_assets directory found")

if __name__ == '__main__':
    print("📥 Importing Azure questions from CSV...")
    import_azure_questions()
    print("✅ Import complete!")