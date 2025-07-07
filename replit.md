# PrepMyCert - Certification Test Preparation Platform

## Overview

PrepMyCert is a comprehensive Flask-based web application designed for professional certification exam preparation. The platform offers test packages across various domains including cloud computing, cybersecurity, networking, and project management. Users can purchase test packages with lifetime access and track their progress through detailed analytics.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 for responsive design
- **Styling**: Custom CSS with purple theme branding, responsive design patterns
- **JavaScript**: Vanilla JavaScript for interactive features, form validation, and test-taking functionality
- **UI Components**: Bootstrap components with custom styling, Font Awesome icons

### Backend Architecture
- **Framework**: Flask web framework with blueprints pattern
- **Database ORM**: SQLAlchemy with Flask-SQLAlchemy integration
- **Authentication**: Flask-Login for session management
- **Payment Processing**: Stripe integration for test package purchases
- **File Processing**: Pandas for CSV question imports

### Database Schema
- **User Management**: Users table with authentication, profile information, and admin roles
- **Test Content**: TestPackage, Question, AnswerOption tables for organizing test materials
- **Purchase Tracking**: UserPurchase table for managing lifetime access to packages
- **Progress Tracking**: TestAttempt and UserAnswer tables for detailed analytics

## Key Components

### Authentication System
- User registration and login with password hashing (Werkzeug)
- Session-based authentication using Flask-Login
- Admin role-based access control for question management
- Secure password requirements and validation

### Test Management
- CSV-based question import system for administrators
- Support for multiple-choice questions with detailed explanations
- Domain-based question categorization
- Flexible answer option structure (1-6 options per question)

### Payment Integration
- Stripe integration for secure payment processing
- One-time purchase model with lifetime access
- Payment success/failure handling with proper redirects
- User purchase tracking and access control

### Test Taking Engine
- Interactive test interface with progress tracking
- Question navigation (previous/next functionality)
- Answer selection and submission handling
- Real-time progress indicators

## Data Flow

### User Registration Flow
1. User submits registration form
2. System validates email uniqueness
3. Password is hashed and stored
4. User account created with default permissions

### Purchase Flow
1. User selects test package
2. Stripe checkout session created
3. Payment processed securely
4. UserPurchase record created on success
5. User granted lifetime access to package

### Test Taking Flow
1. User accesses purchased test package
2. Questions loaded from database
3. User navigates through questions
4. Answers stored in UserAnswer table
5. Test results calculated and displayed
6. TestAttempt record created for tracking

## External Dependencies

### Payment Processing
- **Stripe**: Secure payment processing with webhook support
- **Environment Variables**: STRIPE_SECRET_KEY for API integration

### Database
- **SQLAlchemy**: Database ORM with PostgreSQL compatibility
- **Connection Pooling**: Configured for production deployment
- **Environment Variables**: DATABASE_URL for connection string

### File Processing
- **Pandas**: CSV file processing for question imports
- **File Upload**: Multipart form handling for CSV uploads

### Frontend Libraries
- **Bootstrap 5**: Responsive CSS framework
- **Font Awesome**: Icon library for UI elements
- **jQuery**: JavaScript library for DOM manipulation

## Deployment Strategy

### Environment Configuration
- Environment variables for sensitive data (DATABASE_URL, STRIPE_SECRET_KEY, SESSION_SECRET)
- Debug mode configuration for development vs production
- Database connection pooling for scalability

### Static Asset Management
- CSS and JavaScript files served from static directory
- CDN integration for external libraries (Bootstrap, Font Awesome)
- Optimized asset loading for performance

### Database Management
- Automatic table creation on application startup
- Migration support through SQLAlchemy
- Connection pooling and recycling for stability

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### Image Support for Questions (July 07, 2025)
- Added automatic image processing for questions and answer options
- CSV imports now support IMAGE: references that convert to actual img tags
- Created `/static/images/questions/` folder for image storage
- Questions display images properly in test interface

### Question Management System (July 07, 2025)
- Added comprehensive admin question management interface
- Individual question editing with live image processing
- Manual question creation with multiple answer options
- Question deletion with confirmation
- Enhanced admin dashboard with package-specific question management

### Admin Test Access (July 07, 2025)
- Admin users can now take any test without purchasing
- Special admin indicators on test package pages
- Test interface works properly with admin access

### UI Improvements (July 07, 2025)
- Removed yellow star from homepage hero area
- Added professional graduation cap icon with animated domain badges
- Enhanced hero section with hover effects and animations
- Fixed CSS formatting and responsiveness

## Changelog

Changelog:
- July 06, 2025. Initial setup
- July 07, 2025. Added image support, question management, and admin enhancements