#!/usr/bin/env python3
"""
Migration script to transition from TestPackage to Course > PracticeTest structure
This script:
1. Creates new tables (courses, practice_tests)
2. Migrates existing TestPackages to Courses
3. Creates default "Practice Test 1" for each course
4. Migrates Questions to the new practice tests
5. Updates all related foreign key references
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from app import app, db
from models import (
    TestPackage, Course, PracticeTest, Question, 
    UserPurchase, TestAttempt, CourseAzureMapping,
    BundlePackage
)
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_new_tables():
    """Create new tables for Course and PracticeTest"""
    with app.app_context():
        try:
            logger.info("🏗️  Creating new tables...")
            
            # Create all tables (this will create courses and practice_tests)
            db.create_all()
            
            logger.info("✅ New tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating new tables: {str(e)}")
            return False

def migrate_testpackages_to_courses():
    """Migrate existing TestPackages to new Course model"""
    with app.app_context():
        try:
            logger.info("📦 Migrating TestPackages to Courses...")
            
            # Get all existing test packages
            test_packages = TestPackage.query.all()
            
            if not test_packages:
                logger.info("No TestPackages found to migrate")
                return True
            
            logger.info(f"Found {len(test_packages)} TestPackages to migrate")
            
            migrated_count = 0
            
            for test_package in test_packages:
                # Check if course already exists
                existing_course = Course.query.filter_by(title=test_package.title).first()
                
                if existing_course:
                    logger.info(f"   Course already exists: {test_package.title}")
                    continue
                
                # Create new course
                course = Course(
                    title=test_package.title,
                    description=test_package.description,
                    price=test_package.price,
                    stripe_price_id=test_package.stripe_price_id,
                    domain=test_package.domain,
                    is_active=test_package.is_active,
                    created_at=test_package.created_at
                )
                
                db.session.add(course)
                db.session.flush()  # Get the ID
                
                logger.info(f"   ✅ Migrated: {test_package.title} -> Course ID {course.id}")
                migrated_count += 1
            
            db.session.commit()
            logger.info(f"📊 Migrated {migrated_count} TestPackages to Courses")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error migrating TestPackages: {str(e)}")
            db.session.rollback()
            return False

def create_default_practice_tests():
    """Create default 'Practice Test 1' for each course"""
    with app.app_context():
        try:
            logger.info("🧪 Creating default practice tests...")
            
            # Get all courses
            courses = Course.query.all()
            
            if not courses:
                logger.warning("No courses found")
                return True
            
            created_count = 0
            
            for course in courses:
                # Check if practice test already exists
                existing_practice_test = PracticeTest.query.filter_by(
                    course_id=course.id,
                    order=1
                ).first()
                
                if existing_practice_test:
                    logger.info(f"   Practice test already exists for: {course.title}")
                    continue
                
                # Create default practice test
                practice_test = PracticeTest(
                    course_id=course.id,
                    title="Practice Test 1",
                    description=f"Practice test for {course.title}",
                    order=1,
                    is_active=True,
                    created_at=course.created_at
                )
                
                db.session.add(practice_test)
                created_count += 1
                
                logger.info(f"   ✅ Created Practice Test 1 for: {course.title}")
            
            db.session.commit()
            logger.info(f"📊 Created {created_count} default practice tests")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating practice tests: {str(e)}")
            db.session.rollback()
            return False

def migrate_questions_to_practice_tests():
    """Migrate questions from TestPackages to PracticeTests"""
    with app.app_context():
        try:
            logger.info("❓ Migrating questions to practice tests...")
            
            # Get all questions that still reference test_package_id
            questions = Question.query.filter(
                Question.test_package_id.isnot(None),
                Question.practice_test_id.is_(None)
            ).all()
            
            if not questions:
                logger.info("No questions to migrate")
                return True
            
            logger.info(f"Found {len(questions)} questions to migrate")
            
            migrated_count = 0
            
            for question in questions:
                # Find the corresponding course
                test_package = TestPackage.query.get(question.test_package_id)
                if not test_package:
                    logger.warning(f"   TestPackage not found for question {question.id}")
                    continue
                
                # Find the course
                course = Course.query.filter_by(title=test_package.title).first()
                if not course:
                    logger.warning(f"   Course not found for {test_package.title}")
                    continue
                
                # Find the default practice test for this course
                practice_test = PracticeTest.query.filter_by(
                    course_id=course.id,
                    order=1
                ).first()
                
                if not practice_test:
                    logger.warning(f"   Practice test not found for course {course.title}")
                    continue
                
                # Update question to reference practice test
                question.practice_test_id = practice_test.id
                migrated_count += 1
                
                if migrated_count % 10 == 0:
                    logger.info(f"   Migrated {migrated_count} questions...")
            
            db.session.commit()
            logger.info(f"📊 Migrated {migrated_count} questions to practice tests")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error migrating questions: {str(e)}")
            db.session.rollback()
            return False

def migrate_purchases():
    """Migrate UserPurchases from TestPackage to Course references"""
    with app.app_context():
        try:
            logger.info("💰 Migrating user purchases...")
            
            # Get purchases that reference test_package_id but not course_id
            purchases = UserPurchase.query.filter(
                UserPurchase.test_package_id.isnot(None),
                UserPurchase.course_id.is_(None)
            ).all()
            
            if not purchases:
                logger.info("No purchases to migrate")
                return True
            
            logger.info(f"Found {len(purchases)} purchases to migrate")
            
            migrated_count = 0
            
            for purchase in purchases:
                # Find the corresponding course
                test_package = TestPackage.query.get(purchase.test_package_id)
                if not test_package:
                    logger.warning(f"   TestPackage not found for purchase {purchase.id}")
                    continue
                
                # Find the course
                course = Course.query.filter_by(title=test_package.title).first()
                if not course:
                    logger.warning(f"   Course not found for {test_package.title}")
                    continue
                
                # Update purchase to reference course
                purchase.course_id = course.id
                purchase.purchase_type = 'course'
                migrated_count += 1
            
            db.session.commit()
            logger.info(f"📊 Migrated {migrated_count} purchases to courses")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error migrating purchases: {str(e)}")
            db.session.rollback()
            return False

def migrate_test_attempts():
    """Migrate TestAttempts from TestPackage to PracticeTest references"""
    with app.app_context():
        try:
            logger.info("📝 Migrating test attempts...")
            
            # Get test attempts that reference test_package_id but not practice_test_id
            test_attempts = TestAttempt.query.filter(
                TestAttempt.test_package_id.isnot(None),
                TestAttempt.practice_test_id.is_(None)
            ).all()
            
            if not test_attempts:
                logger.info("No test attempts to migrate")
                return True
            
            logger.info(f"Found {len(test_attempts)} test attempts to migrate")
            
            migrated_count = 0
            
            for attempt in test_attempts:
                # Find the corresponding practice test
                test_package = TestPackage.query.get(attempt.test_package_id)
                if not test_package:
                    logger.warning(f"   TestPackage not found for attempt {attempt.id}")
                    continue
                
                # Find the course
                course = Course.query.filter_by(title=test_package.title).first()
                if not course:
                    logger.warning(f"   Course not found for {test_package.title}")
                    continue
                
                # Find the default practice test
                practice_test = PracticeTest.query.filter_by(
                    course_id=course.id,
                    order=1
                ).first()
                
                if not practice_test:
                    logger.warning(f"   Practice test not found for course {course.title}")
                    continue
                
                # Update attempt to reference practice test
                attempt.practice_test_id = practice_test.id
                migrated_count += 1
            
            db.session.commit()
            logger.info(f"📊 Migrated {migrated_count} test attempts to practice tests")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error migrating test attempts: {str(e)}")
            db.session.rollback()
            return False

def migrate_azure_mappings():
    """Migrate CourseAzureMapping from TestPackage to Course references"""
    with app.app_context():
        try:
            logger.info("☁️  Migrating Azure mappings...")
            
            # Get mappings that reference test_package_id but not course_id
            mappings = CourseAzureMapping.query.filter(
                CourseAzureMapping.test_package_id.isnot(None),
                CourseAzureMapping.course_id.is_(None)
            ).all()
            
            if not mappings:
                logger.info("No Azure mappings to migrate")
                return True
            
            logger.info(f"Found {len(mappings)} Azure mappings to migrate")
            
            migrated_count = 0
            
            for mapping in mappings:
                # Find the corresponding course
                test_package = TestPackage.query.get(mapping.test_package_id)
                if not test_package:
                    logger.warning(f"   TestPackage not found for mapping {mapping.id}")
                    continue
                
                # Find the course
                course = Course.query.filter_by(title=test_package.title).first()
                if not course:
                    logger.warning(f"   Course not found for {test_package.title}")
                    continue
                
                # Update mapping to reference course
                mapping.course_id = course.id
                migrated_count += 1
            
            db.session.commit()
            logger.info(f"📊 Migrated {migrated_count} Azure mappings to courses")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error migrating Azure mappings: {str(e)}")
            db.session.rollback()
            return False

def migrate_bundle_packages():
    """Migrate BundlePackages from TestPackage to Course references"""
    with app.app_context():
        try:
            logger.info("📦 Migrating bundle packages...")
            
            # Get bundle packages that reference test_package_id but not course_id
            bundle_packages = BundlePackage.query.filter(
                BundlePackage.test_package_id.isnot(None),
                BundlePackage.course_id.is_(None)
            ).all()
            
            if not bundle_packages:
                logger.info("No bundle packages to migrate")
                return True
            
            logger.info(f"Found {len(bundle_packages)} bundle packages to migrate")
            
            migrated_count = 0
            
            for bundle_package in bundle_packages:
                # Find the corresponding course
                test_package = TestPackage.query.get(bundle_package.test_package_id)
                if not test_package:
                    logger.warning(f"   TestPackage not found for bundle package {bundle_package.id}")
                    continue
                
                # Find the course
                course = Course.query.filter_by(title=test_package.title).first()
                if not course:
                    logger.warning(f"   Course not found for {test_package.title}")
                    continue
                
                # Update bundle package to reference course
                bundle_package.course_id = course.id
                migrated_count += 1
            
            db.session.commit()
            logger.info(f"📊 Migrated {migrated_count} bundle packages to courses")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error migrating bundle packages: {str(e)}")
            db.session.rollback()
            return False

def generate_migration_report():
    """Generate a report of the migration results"""
    with app.app_context():
        try:
            logger.info("\n" + "="*60)
            logger.info("📊 MIGRATION REPORT")
            logger.info("="*60)
            
            # Count records in new structure
            course_count = Course.query.count()
            practice_test_count = PracticeTest.query.count()
            migrated_questions = Question.query.filter(Question.practice_test_id.isnot(None)).count()
            migrated_purchases = UserPurchase.query.filter(UserPurchase.course_id.isnot(None)).count()
            migrated_attempts = TestAttempt.query.filter(TestAttempt.practice_test_id.isnot(None)).count()
            migrated_mappings = CourseAzureMapping.query.filter(CourseAzureMapping.course_id.isnot(None)).count()
            migrated_bundles = BundlePackage.query.filter(BundlePackage.course_id.isnot(None)).count()
            
            # Count remaining old structure
            old_questions = Question.query.filter(
                Question.test_package_id.isnot(None),
                Question.practice_test_id.is_(None)
            ).count()
            old_purchases = UserPurchase.query.filter(
                UserPurchase.test_package_id.isnot(None),
                UserPurchase.course_id.is_(None)
            ).count()
            old_attempts = TestAttempt.query.filter(
                TestAttempt.test_package_id.isnot(None),
                TestAttempt.practice_test_id.is_(None)
            ).count()
            
            logger.info(f"✅ Courses created: {course_count}")
            logger.info(f"✅ Practice tests created: {practice_test_count}")
            logger.info(f"✅ Questions migrated: {migrated_questions}")
            logger.info(f"✅ Purchases migrated: {migrated_purchases}")
            logger.info(f"✅ Test attempts migrated: {migrated_attempts}")
            logger.info(f"✅ Azure mappings migrated: {migrated_mappings}")
            logger.info(f"✅ Bundle packages migrated: {migrated_bundles}")
            
            if old_questions > 0 or old_purchases > 0 or old_attempts > 0:
                logger.warning("\n⚠️  REMAINING OLD STRUCTURE:")
                logger.warning(f"   Questions not migrated: {old_questions}")
                logger.warning(f"   Purchases not migrated: {old_purchases}")
                logger.warning(f"   Attempts not migrated: {old_attempts}")
            else:
                logger.info("\n🎉 ALL DATA SUCCESSFULLY MIGRATED!")
            
            logger.info("="*60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error generating report: {str(e)}")
            return False

def run_complete_migration():
    """Run the complete migration process"""
    logger.info("🚀 Starting complete migration to Course > PracticeTest structure")
    logger.info("="*60)
    
    # Run migration steps in order
    steps = [
        ("Create new tables", create_new_tables),
        ("Migrate TestPackages to Courses", migrate_testpackages_to_courses),
        ("Create default practice tests", create_default_practice_tests),
        ("Migrate questions to practice tests", migrate_questions_to_practice_tests),
        ("Migrate user purchases", migrate_purchases),
        ("Migrate test attempts", migrate_test_attempts),
        ("Migrate Azure mappings", migrate_azure_mappings),
        ("Migrate bundle packages", migrate_bundle_packages),
        ("Generate migration report", generate_migration_report)
    ]
    
    for step_name, step_function in steps:
        logger.info(f"\n📍 {step_name}...")
        if not step_function():
            logger.error(f"❌ Migration failed at step: {step_name}")
            return False
    
    logger.info("\n🎉 Migration completed successfully!")
    logger.info("="*60)
    
    logger.info("\n📋 NEXT STEPS:")
    logger.info("1. Update your application code to use the new Course/PracticeTest models")
    logger.info("2. Update admin interfaces and templates")
    logger.info("3. Test the new functionality thoroughly")
    logger.info("4. Once confirmed working, you can optionally clean up old TestPackage data")
    
    return True

if __name__ == '__main__':
    run_complete_migration()