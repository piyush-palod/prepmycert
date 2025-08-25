# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PrepMyCert is a Flask-based web application for online certification test preparation. It provides:

- User registration and authentication with OTP-based security
- Test package management and purchasing system
- Bundle system for grouping test packages with discounts
- Coupon system for promotional discounts
- Admin interface for content and user management
- Stripe integration for payment processing
- Email notifications and OTP delivery

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
- **app.py**: Flask application factory with database, authentication, and extension setup
- **main.py**: Application entry point that imports all route modules
- **models.py**: SQLAlchemy database models defining the complete data schema
- **routes.py**: Main application routes (packages, tests, payments, admin)
- **auth_routes.py**: OTP-based authentication system routes
- **admin_coupon_routes.py**: Admin routes for coupon and bundle management
- **admin_email_routes.py**: Admin routes for email configuration
- **utils.py**: Utility functions for CSV imports and image processing
- **email_service.py**: Email delivery service with template support

### Database Models
Key models include:
- **User**: User accounts with OTP authentication, admin roles, and account locking
- **TestPackage**: Individual test packages with pricing and domain categorization
- **Bundle**: Grouped packages with discounted pricing
- **Question/AnswerOption**: Test content with support for images and explanations
- **Coupon**: Promotional discount system with usage limits and validation
- **UserPurchase**: Purchase records supporting both individual and bundle purchases
- **TestAttempt/UserAnswer**: Test-taking functionality with scoring
- **OTPToken**: Secure token-based authentication system

### Authentication System
Uses a custom OTP-based authentication system:
- Users register/login using email addresses
- OTP tokens sent via email for verification
- Account locking after failed attempts
- Session-based authentication with Flask-Login
- Admin role system for management access

### Payment Processing
- Stripe integration for secure payments
- Support for individual package and bundle purchases
- Coupon system with percentage and fixed discounts
- Automatic purchase record creation and email confirmations

### Image Management
Images are organized by test package in `static/images/questions/{package_name}/`:
- CSV imports support `IMAGE: filename.png` syntax
- Images automatically processed during question import/editing
- Package-specific folders created automatically
- Support for PNG, JPG, JPEG, GIF formats

### Admin Features
- Question management with rich text and image support
- User management with admin privilege controls
- Coupon creation and analytics
- Bundle management with automatic pricing calculations
- Email template configuration
- CSV question importing with validation

## Environment Variables

Required environment variables:
- `DATABASE_URL`: PostgreSQL database connection string
- `SESSION_SECRET`: Flask session secret key
- `STRIPE_PUBLISHABLE_KEY`: Stripe public key for payments
- `STRIPE_SECRET_KEY`: Stripe secret key for payments
- `ADMIN_EMAIL`: Initial admin user email (optional)
- `ADMIN_PASSWORD`: Initial admin user password (optional)

Email configuration (for SMTP):
- `EMAIL_HOST`: SMTP server hostname
- `EMAIL_PORT`: SMTP server port
- `EMAIL_USER`: SMTP username
- `EMAIL_PASSWORD`: SMTP password
- `EMAIL_FROM_NAME`: Display name for outgoing emails

## Key Patterns

### Route Organization
Routes are split across multiple modules:
- Main routes in `routes.py`
- Authentication routes in `auth_routes.py` 
- Admin functionality split by feature (coupons, email)

### Database Sessions
All database operations use proper session management:
- Use `db.session.commit()` to save changes
- Use `db.session.rollback()` on errors
- Use `db.session.flush()` to get IDs before commit

### Error Handling
- Flash messages for user feedback
- Try/catch blocks around database operations
- Custom error pages (404.html, 500.html)
- CSRF protection with custom error handling

### Image Processing
- Images referenced in questions using `IMAGE: filename.png` syntax
- `process_text_with_images()` function converts references to HTML img tags
- Package-specific image folders for organization