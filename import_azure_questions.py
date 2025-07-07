#!/usr/bin/env python3
"""Import Azure questions from the provided CSV file"""

from app import app, db
from models import TestPackage
from utils import import_questions_from_csv
import os

def import_azure_questions():
    """Import questions from the provided Azure CSV file"""
    with app.app_context():
        # Create Azure test package
        azure_package = TestPackage.query.filter_by(title='Microsoft Azure Fundamentals AZ-900').first()
        if not azure_package:
            azure_package = TestPackage(
                title='Microsoft Azure Fundamentals AZ-900',
                description='Master Azure cloud fundamentals with comprehensive AZ-900 certification preparation. Covers Azure services, pricing, security, and governance.',
                price=42.99,
                domain='Cloud Computing'
            )
            db.session.add(azure_package)
            db.session.commit()
            print("✅ Created Azure Fundamentals test package")
        
        # Import questions from CSV
        csv_path = 'attached_assets/p5_1751843506788.csv'
        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r', encoding='utf-8') as file:
                    result = import_questions_from_csv(file, azure_package.id)
                    print(f"✅ Imported {result['imported']} Azure questions, skipped {result['skipped']} duplicates")
            except Exception as e:
                print(f"❌ Error importing questions: {str(e)}")
        else:
            print(f"❌ CSV file not found at {csv_path}")

if __name__ == '__main__':
    print("📥 Importing Azure questions from CSV...")
    import_azure_questions()
    print("✅ Import complete!")