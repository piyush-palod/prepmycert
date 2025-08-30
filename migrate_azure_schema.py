#!/usr/bin/env python3
"""
Migration script for Azure image integration
Adds new columns and CourseAzureMapping table
"""

import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from app import app, db
from models import CourseAzureMapping, Question, AnswerOption
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_columns_if_not_exists():
    """Add new columns to existing tables if they don't exist"""
    with app.app_context():
        try:
            # Check and add processed_question_text to questions table
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='questions' AND column_name='processed_question_text'
            """)).fetchone()
            
            if not result:
                logger.info("Adding processed_question_text column to questions table")
                db.session.execute(text("ALTER TABLE questions ADD COLUMN processed_question_text TEXT"))
            
            # Check and add processed_explanation to questions table
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='questions' AND column_name='processed_explanation'
            """)).fetchone()
            
            if not result:
                logger.info("Adding processed_explanation column to questions table")
                db.session.execute(text("ALTER TABLE questions ADD COLUMN processed_explanation TEXT"))
            
            # Check and add processed_option_text to answer_options table
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='answer_options' AND column_name='processed_option_text'
            """)).fetchone()
            
            if not result:
                logger.info("Adding processed_option_text column to answer_options table")
                db.session.execute(text("ALTER TABLE answer_options ADD COLUMN processed_option_text TEXT"))
            
            # Check and add processed_explanation to answer_options table
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='answer_options' AND column_name='processed_explanation'
            """)).fetchone()
            
            if not result:
                logger.info("Adding processed_explanation column to answer_options table")
                db.session.execute(text("ALTER TABLE answer_options ADD COLUMN processed_explanation TEXT"))
            
            db.session.commit()
            logger.info("✅ Successfully added new columns")
            
        except Exception as e:
            logger.error(f"❌ Error adding columns: {str(e)}")
            db.session.rollback()
            raise

def create_course_azure_mapping_table():
    """Create the CourseAzureMapping table if it doesn't exist"""
    with app.app_context():
        try:
            # Check if table exists
            result = db.session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name='course_azure_mappings'
            """)).fetchone()
            
            if not result:
                logger.info("Creating course_azure_mappings table")
                db.create_all()  # This will create any missing tables including CourseAzureMapping
                logger.info("✅ Successfully created course_azure_mappings table")
            else:
                logger.info("course_azure_mappings table already exists")
                
        except Exception as e:
            logger.error(f"❌ Error creating CourseAzureMapping table: {str(e)}")
            db.session.rollback()
            raise

def migrate_schema():
    """Run the complete schema migration"""
    logger.info("🔄 Starting Azure schema migration...")
    
    # Add new columns to existing tables
    add_columns_if_not_exists()
    
    # Create new CourseAzureMapping table
    create_course_azure_mapping_table()
    
    logger.info("✅ Azure schema migration completed successfully!")

if __name__ == '__main__':
    migrate_schema()