# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PrepMyCert is a Flask-based web application for online certification test preparation. It provides:

- User registration and authentication with OTP-based security
- Course and practice test management system
- Bundle system for grouping courses with discounts
- Coupon system with percentage and fixed promotional discounts
- Comprehensive admin interface for content and user management
- Stripe integration for secure payment processing
- Azure Blob Storage for image management with SAS token security
- Email notifications and OTP delivery system
- Testing engine with scoring and performance analytics

## Development Commands

### Running the Application
```bash
python main.py                    # Start development server
```

### Database Management
```bash
python migrate_database.py        # Apply database migrations
python migrate_coupon_bundle.py   # Migrate coupon and bundle data
python setup_admin.py            # Create initial admin user
```

### Importing Questions
```bash
python import_azure_questions.py  # Import questions from CSV files
```

## Architecture

### Core Application Structure
- **app.py**: Flask application factory with database, authentication, rate limiting, and extension setup
- **main.py**: Application entry point with environment validation and route module imports
- **models.py**: SQLAlchemy database models with comprehensive schema for courses, tests, and users
- **routes.py**: Main application routes (courses, practice tests, payments, dashboard)
- **auth_routes.py**: Complete OTP-based authentication system with security features
- **admin_coupon_routes.py**: Admin routes for coupon and bundle management
- **admin_email_routes.py**: Admin routes for email configuration and templates
- **azure_service.py**: Azure Blob Storage service for secure image management
- **utils.py**: Utility functions for CSV imports, image processing, and validation
- **email_service.py**: Flask-Mail service with OTP and notification support

### Database Models
Key models include:
- **User**: User accounts with OTP authentication, admin roles, account locking, and security features
- **Course**: Individual certification courses with pricing, domains, and Azure folder configuration
- **PracticeTest**: Practice tests within courses with time limits and ordering
- **Question/AnswerOption**: Rich test content with Azure image support and explanations
- **Bundle/BundleCourse**: Grouped courses with discounted pricing and savings calculations
- **Coupon**: Advanced promotional system with percentage/fixed discounts and usage analytics
- **UserPurchase**: Purchase records supporting courses, bundles, and Stripe integration
- **TestAttempt/UserAnswer**: Complete testing engine with scoring and performance tracking
- **OTPToken**: Secure multi-purpose token system for authentication and verification

### Authentication System
Uses a comprehensive OTP-based authentication system:
- Users register/login exclusively using email addresses and OTP codes
- Multi-purpose OTP tokens: registration verification, login, password reset
- Advanced security: rate limiting, account locking, failed attempt tracking
- Session-based authentication with Flask-Login integration
- Admin role system with granular access controls
- Token expiration and automatic cleanup mechanisms

### Payment Processing
- Stripe Checkout integration for secure payment processing
- Support for individual course and bundle purchases
- Advanced coupon system with percentage and fixed amount discounts
- Automatic purchase record creation with Stripe session tracking
- Email confirmations and purchase notifications
- Bundle pricing with automatic savings calculations

### Image Management
Advanced Azure Blob Storage integration with secure access:
- Images stored in Azure Blob Storage with course-specific folder organization
- SAS token generation for secure, time-limited image access (30-day expiry)
- CSV imports support `IMAGE: filename.png` syntax with automatic Azure processing
- Images automatically processed during question import/editing
- Support for PNG, JPG, JPEG, GIF formats with secure URL generation
- Environment-configurable Azure storage settings

### Admin Features
- Comprehensive course and practice test management
- Question management with rich text, images, and Azure integration
- User management with admin privilege controls and analytics
- Advanced coupon creation with usage tracking and analytics
- Bundle management with automatic pricing and savings calculations
- Email template configuration and SMTP settings
- CSV question importing with validation and error handling
- Azure image upload and management interface

## Environment Variables

Required environment variables:
- `DATABASE_URL`: PostgreSQL database connection string
- `SESSION_SECRET`: Flask session secret key for security

Payment configuration:
- `STRIPE_PUBLISHABLE_KEY`: Stripe public key for frontend
- `STRIPE_SECRET_KEY`: Stripe secret key for backend processing

Azure Storage configuration:
- `AZURE_STORAGE_CONNECTION_STRING`: Azure Blob Storage connection string
- `AZURE_CONTAINER_NAME`: Azure container name (default: 'certification-images')
- `AZURE_STORAGE_ACCOUNT_NAME`: Azure storage account name (default: 'prepmycertimages')
- `AZURE_BLOB_BASE_URL`: Base URL for Azure blobs

Email configuration (Flask-Mail):
- `MAIL_SERVER`: SMTP server hostname (default: 'localhost' for development)
- `MAIL_PORT`: SMTP server port (default: 1025 for MailHog)
- `MAIL_USE_TLS`: Enable TLS (default: false)
- `MAIL_USE_SSL`: Enable SSL (default: false)
- `MAIL_USERNAME`: SMTP username
- `MAIL_PASSWORD`: SMTP password
- `MAIL_DEFAULT_SENDER`: Default sender email (default: 'noreply@prepmycert.com')
- `MAIL_SUPPRESS_SEND`: Disable email sending for development (default: true)

Optional configuration:
- `ADMIN_EMAIL`: Initial admin user email for auto-creation
- `ADMIN_PASSWORD`: Initial admin user password (default: 'admin123')
- `FLASK_DEBUG`: Enable debug mode (default: False)

## Key Patterns

### Route Organization
Routes are modularized for maintainability:
- **routes.py**: Core application routes (courses, practice tests, payments, dashboard)
- **auth_routes.py**: Complete OTP authentication system (register, login, password reset)
- **admin_coupon_routes.py**: Admin coupon and bundle management
- **admin_email_routes.py**: Admin email configuration and templates

### Database Sessions
All database operations use proper session management:
- Use `db.session.commit()` to save changes
- Use `db.session.rollback()` on errors
- Use `db.session.flush()` to get IDs before commit

### Error Handling
- Flash messages for comprehensive user feedback
- Try/catch blocks around all database operations
- Custom error pages (404.html, 500.html) with user-friendly messaging
- CSRF protection with custom error handling and token refresh
- Rate limiting with graceful error responses

### Image Processing
- Images referenced in questions using `IMAGE: filename.png` syntax
- `process_text_with_images()` function converts references to secure Azure URLs
- Course-specific Azure folders for organization
- Automatic SAS token generation for secure, time-limited access
- Support for bulk image uploads via admin interface

### Security Features
- Rate limiting on all authentication endpoints (Flask-Limiter)
- CSRF protection with custom error handling
- OTP token expiration and automatic cleanup
- Account lockout after failed login attempts
- Secure password hashing with Werkzeug
- Environment-based configuration management
- Azure SAS tokens for secure image access

## Recent Changes and Fixes (September 2025)

### Critical Issues Resolved

**Import and Circular Dependency Fixes:**
- Added missing `CouponUsage` model with complete relationships to coupons, users, and purchases
- Enhanced `OTPToken` model with missing `user_id` field and complete implementation including:
  - Token generation with 6-digit codes and expiration handling  
  - `verify_token()` method for secure token validation
  - `cleanup_expired_tokens()` static method for maintenance
- Added missing `User` model security methods:
  - `is_account_locked()` with automatic unlock after 1 hour
  - `increment_login_attempts()` with account locking after 5 failed attempts
  - `reset_login_attempts()` for successful logins
- Enhanced `Coupon` model with validation and calculation methods:
  - `is_valid()` method checking expiry, usage limits, and user eligibility
  - `calculate_discount()` method for percentage and fixed discounts

**Legacy Naming Standardization:**
- Completely migrated from `TestPackage` to `Course` terminology throughout the application
- Updated `admin_coupon_routes.py` to use `Course` instead of deprecated `TestPackage` references
- Fixed `BundlePackage` references to use existing `BundleCourse` model consistently
- Rewrote `import_azure_questions.py` to work with Course → PracticeTest → Question hierarchy
- Updated `migrate_coupon_bundle.py` with correct model imports

**Template and Route Consistency:**
- Added legacy route `/test-packages` that redirects to `/courses` for backward compatibility
- Renamed `test_packages.html` → `courses.html` with updated content and terminology
- Renamed `package_detail.html` → `course_detail.html` for consistency
- Fixed all template references from `admin_packages` to `admin_courses`
- Updated navigation, footer, and admin panel links throughout the application
- Changed terminology from "Test Packages" to "Courses" in all user-facing text

### Database Schema Improvements

**Enhanced Model Relationships:**
- `CouponUsage` model properly linked to coupons, users, and purchases with cascade options
- `OTPToken` model with proper user relationships and nullable email-only token support
- Improved foreign key constraints and indexes for better performance

**Security Enhancements:**
- Account lockout mechanism with automatic unlock functionality
- Enhanced OTP token system with IP address tracking and proper expiration
- Improved coupon validation with comprehensive business rule checking

### Application Structure Improvements

**Route Organization:**
- Maintained clean separation between authentication, admin, and main application routes
- Added proper legacy route handling for smooth transitions
- Enhanced error handling in all route modules

**Template Consistency:**
- Standardized naming conventions across all templates
- Updated all navigation elements to use consistent terminology
- Improved user experience with proper redirects and messaging

### Development Process Documentation

**Testing and Validation:**
- All changes tested to ensure application starts without import errors
- Verified template rendering works correctly with new model structure
- Confirmed legacy routes properly redirect to maintain existing bookmarks
- Validated admin functionality works with updated model references

**Code Quality:**
- Maintained proper error handling and validation throughout
- Preserved existing security measures while enhancing functionality
- Kept consistent code style and documentation standards
- Ensured all database operations use proper session management

These changes resolve all circular import issues, standardize the codebase on the Course-based terminology, and maintain backward compatibility while improving the overall application architecture.

## Recent UI and Functionality Improvements (September 2025)

### Question Management Enhancement

**Add Question Form Flexibility:**
- Modified `templates/admin/add_question.html` to support questions with only 2 answer options
- Removed `required` attribute from options 3 and 4, making them optional
- Added client-side JavaScript validation ensuring:
  - Minimum of 2 answer options are provided
  - At least one correct answer is selected from filled options
  - Clear visual indicators showing optional vs required fields

**Server-Side Validation:**
- Enhanced `routes.py` add question functionality with comprehensive validation:
  - Validates minimum 2 options requirement before database insertion
  - Ensures at least one correct answer is marked among provided options
  - Provides meaningful error messages with form re-display on validation failure
  - Prevents creation of invalid questions that would break the testing engine

### Image Display and Processing Improvements

**Azure Service Image Processing:**
- Updated `azure_service.py` `process_text_with_images()` function with enhanced formatting:
  - Images now wrapped in styled containers with proper spacing
  - Added visual enhancements: rounded corners, shadows, and hover effects
  - Improved responsive behavior for different screen sizes
  - Better separation between text content and images

**CSS Styling Enhancements:**
- Added comprehensive image styling to `static/css/style.css`:
  - `.question-image-container` with centered layout and styled background
  - `.question-image` with responsive sizing (min-width: 300px, max-width: 800px)
  - Hover effects with subtle scaling and enhanced shadows
  - Mobile-responsive breakpoints for optimal viewing on all devices
  - Special styling for test-taking interface with theme colors

**Template Consistency Fixes:**
- Fixed `templates/test_taking.html` template variable mismatches:
  - Updated from `question.question_text` to `question.text` for route data compatibility
  - Changed `question.answer_options` to `question.options` for correct data structure
  - Fixed `option.option_text` to `option.text` for proper option display
- Ensured all question display templates use consistent variable naming

### Edit Question Template Fix

**Route Compatibility:**
- Fixed `templates/admin/edit_question.html` route reference issue:
  - Updated `url_for('manage_questions', package_id=...)` to use `practice_test_id` parameter
  - Resolved URL building errors that caused 500 errors on question editing
  - Maintained proper navigation flow in admin interface

### Technical Implementation Details

**Image Processing Pipeline:**
1. `IMAGE: filename.png` syntax detected in question text
2. Azure service generates SAS-enabled URLs for secure access
3. Images wrapped in responsive containers with styling
4. Proper fallback handling for missing or invalid images
5. Automatic cache refresh with 30-day SAS token expiry

**Form Validation Flow:**
1. Client-side JavaScript provides immediate feedback
2. Server-side validation ensures data integrity
3. Comprehensive error messages guide user corrections
4. Form state preservation on validation failures
5. Graceful handling of edge cases and malformed data

**CSS Architecture:**
- Mobile-first responsive design approach
- Consistent theme integration with existing color scheme
- Performance-optimized with minimal CSS overhead
- Cross-browser compatibility with modern web standards

These improvements enhance the user experience for question management, ensure proper image display across all interfaces, and maintain data integrity through comprehensive validation while preserving the existing security and performance characteristics of the application.