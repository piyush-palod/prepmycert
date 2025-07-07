#!/usr/bin/env python3
"""Setup script to create admin user and sample data"""

from app import app, db
from models import User, TestPackage, Question, AnswerOption
from utils import import_questions_from_csv
import pandas as pd
from io import StringIO

def create_admin_user():
    """Create an admin user for testing purposes"""
    with app.app_context():
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
            print("✅ Admin user created: admin@prepmycert.com / admin123")
        else:
            print("ℹ️ Admin user already exists")

def create_sample_packages():
    """Create sample test packages"""
    with app.app_context():
        packages_data = [
            {
                'title': 'AWS Solutions Architect Associate',
                'description': 'Comprehensive preparation for the AWS Solutions Architect Associate certification. Master cloud architecture, security, and best practices.',
                'price': 49.99,
                'domain': 'Cloud Computing'
            },
            {
                'title': 'CompTIA Security+ SY0-601',
                'description': 'Complete study guide for CompTIA Security+ certification. Learn cybersecurity fundamentals, risk management, and security technologies.',
                'price': 39.99,
                'domain': 'Cybersecurity'
            },
            {
                'title': 'Cisco CCNA 200-301',
                'description': 'Master networking fundamentals with Cisco CCNA certification preparation. Covers routing, switching, and network security.',
                'price': 44.99,
                'domain': 'Networking'
            },
            {
                'title': 'PMP Project Management Professional',
                'description': 'Prepare for the Project Management Professional (PMP) certification. Learn project management methodologies and best practices.',
                'price': 54.99,
                'domain': 'Project Management'
            }
        ]
        
        created_packages = []
        for package_data in packages_data:
            existing = TestPackage.query.filter_by(title=package_data['title']).first()
            if not existing:
                package = TestPackage(**package_data)
                db.session.add(package)
                created_packages.append(package_data['title'])
        
        db.session.commit()
        
        if created_packages:
            print(f"✅ Created sample packages: {', '.join(created_packages)}")
        else:
            print("ℹ️ Sample packages already exist")

def create_sample_questions():
    """Create some sample questions for demonstration"""
    with app.app_context():
        # Get the AWS package
        aws_package = TestPackage.query.filter_by(title='AWS Solutions Architect Associate').first()
        if not aws_package:
            print("❌ AWS package not found")
            return
            
        # Check if questions already exist
        existing_questions = Question.query.filter_by(test_package_id=aws_package.id).count()
        if existing_questions > 0:
            print("ℹ️ Sample questions already exist")
            return
        
        sample_questions = [
            {
                'question_text': 'Which AWS service provides object storage with high availability and durability?',
                'question_type': 'multiple-choice',
                'domain': 'Storage',
                'overall_explanation': 'Amazon S3 is the primary object storage service in AWS, designed for 99.999999999% (11 9s) of durability.',
                'options': [
                    {'text': 'Amazon S3', 'explanation': 'Correct! S3 is AWS object storage service.', 'is_correct': True},
                    {'text': 'Amazon EBS', 'explanation': 'EBS provides block storage, not object storage.', 'is_correct': False},
                    {'text': 'Amazon EFS', 'explanation': 'EFS provides file storage, not object storage.', 'is_correct': False},
                    {'text': 'Amazon Glacier', 'explanation': 'Glacier is for archival storage, part of S3 storage classes.', 'is_correct': False}
                ]
            },
            {
                'question_text': 'What is the maximum size of an object that can be stored in Amazon S3?',
                'question_type': 'multiple-choice',
                'domain': 'Storage',
                'overall_explanation': 'S3 supports objects from 0 bytes to 5 TB in size. For objects larger than 100 MB, multipart upload is recommended.',
                'options': [
                    {'text': '5 GB', 'explanation': 'This is the maximum size for a single PUT operation, not the object limit.', 'is_correct': False},
                    {'text': '5 TB', 'explanation': 'Correct! The maximum object size in S3 is 5 TB.', 'is_correct': True},
                    {'text': '1 TB', 'explanation': 'This is smaller than the actual limit.', 'is_correct': False},
                    {'text': 'Unlimited', 'explanation': 'While S3 bucket storage is unlimited, individual objects have size limits.', 'is_correct': False}
                ]
            },
            {
                'question_text': 'Which AWS service is best suited for running containerized applications?',
                'question_type': 'multiple-choice',
                'domain': 'Compute',
                'overall_explanation': 'AWS offers multiple container services including ECS, EKS, and Fargate for different use cases.',
                'options': [
                    {'text': 'Amazon ECS', 'explanation': 'Correct! ECS is AWS managed container orchestration service.', 'is_correct': True},
                    {'text': 'Amazon EC2', 'explanation': 'EC2 can run containers but is not specifically designed for container orchestration.', 'is_correct': False},
                    {'text': 'AWS Lambda', 'explanation': 'Lambda is for serverless functions, not container orchestration.', 'is_correct': False},
                    {'text': 'Amazon RDS', 'explanation': 'RDS is for managed databases, not containers.', 'is_correct': False}
                ]
            }
        ]
        
        for q_data in sample_questions:
            question = Question(
                test_package_id=aws_package.id,
                question_text=q_data['question_text'],
                question_type=q_data['question_type'],
                domain=q_data['domain'],
                overall_explanation=q_data['overall_explanation']
            )
            db.session.add(question)
            db.session.flush()  # Get the question ID
            
            for i, option_data in enumerate(q_data['options']):
                option = AnswerOption(
                    question_id=question.id,
                    option_text=option_data['text'],
                    explanation=option_data['explanation'],
                    is_correct=option_data['is_correct'],
                    option_order=i + 1
                )
                db.session.add(option)
        
        db.session.commit()
        print(f"✅ Created {len(sample_questions)} sample questions for AWS package")

if __name__ == '__main__':
    print("🚀 Setting up PrepMyCert with sample data...")
    create_admin_user()
    create_sample_packages()
    create_sample_questions()
    print("✅ Setup complete!")
    print("\n📝 Next steps:")
    print("1. Login as admin: admin@prepmycert.com / admin123")
    print("2. Create a regular user account to test purchasing")
    print("3. Import more questions using the CSV upload feature")