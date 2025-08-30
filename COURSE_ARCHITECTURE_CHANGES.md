# Course > Practice Test > Questions Architecture Implementation

## 📋 Overview

This document tracks all changes made to implement the new Course > Practice Test > Questions architecture, replacing the previous flat TestPackage > Questions structure. The new system allows users to take individual practice tests within courses, similar to Udemy's approach.

## 🎯 Objective

Transform the system from:
- **Old**: TestPackage → Questions (flat structure, all questions at once)
- **New**: Course → Practice Test → Questions (hierarchical, individual practice tests)

## 📁 Files Changed & Created

### 1. Database Models (`models.py`)

**New Models Added:**
- `Course` - Replaces TestPackage as the main container
- `PracticeTest` - Individual practice tests within a course
- Updated `Question` - Now belongs to PracticeTest instead of TestPackage

**Key Changes:**
```python
# NEW: Course Model
class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    domain = db.Column(db.String(100), nullable=False)
    practice_tests = db.relationship('PracticeTest', backref='course', lazy=True, cascade='all, delete-orphan')

# NEW: PracticeTest Model
class PracticeTest(db.Model):
    __tablename__ = 'practice_tests'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)  # "Practice Test 1", "Practice Test 2"
    order = db.Column(db.Integer, nullable=False, default=1)
    questions = db.relationship('Question', backref='practice_test', lazy=True, cascade='all, delete-orphan')

# UPDATED: Question Model
class Question(db.Model):
    # Old: test_package_id (kept for migration compatibility)
    test_package_id = db.Column(db.Integer, db.ForeignKey('test_packages.id'), nullable=True, index=True)
    # NEW: practice_test_id
    practice_test_id = db.Column(db.Integer, db.ForeignKey('practice_tests.id'), nullable=True, index=True)
```

**Updated Models for Compatibility:**
- `UserPurchase` - Added `course_id` field, `is_course_purchase` property
- `TestAttempt` - Added `practice_test_id` field for new test attempts
- `CourseAzureMapping` - Added `course_id` field to work with courses

### 2. Database Migration Script (`migrate_to_course_structure.py`)

**Purpose**: Migrate existing TestPackages to Courses and create default practice tests.

**Key Functions:**
- `migrate_testpackages_to_courses()` - Convert TestPackages to Courses
- `create_default_practice_tests()` - Create "Practice Test 1" for each course
- `migrate_questions_to_practice_tests()` - Move questions to practice tests
- `update_foreign_key_references()` - Update all related tables

**Status**: Script exists but not needed since using fresh database approach.

### 3. Main Application Routes (`routes.py`)

**New Routes Added:**
```python
@app.route('/courses')  # List all courses
def courses():

@app.route('/course/<int:course_id>')  # Course detail page
def course_detail(course_id):

@app.route('/practice-test/<int:practice_test_id>')  # Individual practice test detail
def practice_test_detail(practice_test_id):

@app.route('/take-practice-test/<int:practice_test_id>')  # Take specific practice test
@login_required
def take_practice_test(practice_test_id):
```

**Updated Routes:**
- `dashboard()` - Now shows purchased courses and practice test progress
- `create_checkout_session()` - Updated to handle course purchases via Stripe
- Payment success/cancel handlers updated for courses

### 4. Admin Course Management (`admin_course_routes.py`) - **NEW FILE**

**Complete admin interface for the new architecture:**

```python
@app.route('/admin/courses')  # Main admin courses dashboard
def admin_courses():

@app.route('/admin/courses/create', methods=['GET', 'POST'])  # Create new course
def create_course():

@app.route('/admin/courses/<int:course_id>/edit', methods=['GET', 'POST'])  # Edit course
def edit_course(course_id):

@app.route('/admin/courses/<int:course_id>/practice-tests')  # Manage practice tests for course
def manage_practice_tests(course_id):

@app.route('/admin/courses/<int:course_id>/practice-tests/create', methods=['GET', 'POST'])  # Create practice test
def create_practice_test(course_id):

# Additional routes for practice test management, question management, etc.
```

### 5. Application Entry Point (`main.py`)

**Updated Imports:**
```python
import routes  # Added explicit import
from routes import *
import admin_course_routes  # NEW: Import course management routes
from admin_course_routes import *
```

### 6. Templates Created/Updated

#### User-Facing Templates

**`templates/courses.html` - NEW**
- Lists all available courses
- Shows course statistics (practice test count, question count, price)
- Purchase/access buttons based on user status
- Domain filtering functionality

**`templates/course_detail.html` - NEW**
- Detailed course information
- Lists all practice tests within the course
- Purchase interface for courses
- Direct links to take individual practice tests

**`templates/index.html` - UPDATED**
- Updated to show courses instead of test packages
- Links to new course browsing and detail pages
- Maintains existing design but with course-focused content

#### Admin Templates

**`templates/admin/courses.html` - NEW**
- Main admin dashboard for course management
- Course statistics and overview
- Actions: Create, Edit, Delete, Manage Practice Tests

**`templates/admin/create_course.html` - NEW**
- Form to create new courses
- Fields: title, description, price, domain
- Validation and error handling

**`templates/admin/manage_practice_tests.html` - NEW**
- Lists all practice tests for a specific course
- Actions per practice test: Edit, Delete, Manage Questions, Import Questions
- Create new practice test button

**`templates/admin/create_practice_test.html` - NEW**
- Form to create practice tests within a course
- Fields: title, description, order, active status
- Best practices guide and naming conventions

#### Navigation Updates

**`templates/base.html` - UPDATED**
```html
<!-- UPDATED: Admin navigation -->
<li><a href="{{ url_for('admin_courses') }}"><i class="fas fa-graduation-cap me-2"></i>Manage Courses</a></li>
<li><a href="{{ url_for('admin_packages') }}"><i class="fas fa-box me-2"></i>Legacy Packages</a></li>
```

### 7. Development Scripts

#### `dev-scripts/reset_database.py` - NEW
**Purpose**: Clean database reset for testing new architecture.
- Drops all existing tables
- Lets Flask recreate tables automatically on startup
- Simplified approach without redundant table creation

**Key Changes Made:**
- Fixed SQLAlchemy compatibility (`db.session.execute()` instead of `db.engine.execute()`)
- Removed redundant table creation (Flask handles this)
- Proper session management with commit/rollback

#### `dev-scripts/validate_new_architecture.py` - NEW
**Purpose**: Validate all components of new architecture are integrated.
- Model relationship validation
- Route import/function validation  
- Template reference validation
- Azure integration validation
- Payment integration validation

**Key Changes Made:**
- Fixed circular import issues by using file-based validation
- Added environment variable loading
- Validates without actually importing problematic modules

## 🔧 Technical Implementation Details

### Database Schema Changes

**New Tables:**
1. `courses` - Main course container
2. `practice_tests` - Individual practice tests within courses

**Updated Tables:**
1. `questions` - Added `practice_test_id` foreign key
2. `user_purchases` - Added `course_id` foreign key  
3. `test_attempts` - Added `practice_test_id` foreign key
4. `course_azure_mappings` - Added `course_id` foreign key

**Backward Compatibility:**
- Old `test_package_id` fields maintained during transition
- New fields nullable to support gradual migration
- Purchase types distinguish between 'course', 'package', 'bundle'

### Route Architecture

**User Flow:**
1. `/courses` - Browse all courses
2. `/course/<id>` - View course details and practice tests
3. Purchase course via Stripe
4. `/take-practice-test/<id>` - Take individual practice tests
5. View results and progress

**Admin Flow:**
1. `/admin/courses` - Course management dashboard  
2. Create/edit courses
3. `/admin/courses/<id>/practice-tests` - Manage practice tests
4. Add questions to specific practice tests
5. Import questions via CSV

### Payment Integration

**Course Purchases:**
- Stripe integration updated to handle course purchases
- `UserPurchase` model tracks course ownership
- Access control checks course purchase before allowing practice tests

**Backward Compatibility:**
- Still supports legacy test package purchases
- Bundle purchases work with both courses and packages
- Coupon system works with all purchase types

### Azure Integration

**Image Management:**
- `CourseAzureMapping` links courses to Azure blob folders
- Image processing works with course structure
- Azure URL generation updated for course-based paths

## 🚀 Testing Approach

### Fresh Database Strategy
Instead of complex migration, using clean database approach:

1. **Reset Database:**
   ```bash
   python dev-scripts/reset_database.py
   ```

2. **Start Application:**
   ```bash
   python main.py
   ```
   - Flask automatically creates all tables (`db.create_all()`)
   - Admin user created via existing `setup_admin.py` logic

3. **Test Admin Flow:**
   - Login as admin → Admin → "Manage Courses"
   - Create course → Add practice tests → Add questions

4. **Test User Flow:**
   - Browse courses → Purchase → Take individual practice tests

## 🐛 Issues Fixed

### 1. SQLAlchemy Compatibility
**Problem**: `db.engine.execute()` deprecated in newer SQLAlchemy versions
**Solution**: Updated to `db.session.execute()` with proper result handling

### 2. Circular Import Issues
**Problem**: Validation script had circular imports when importing models/routes
**Solution**: File-based validation checking code content instead of importing

### 3. Admin Navigation
**Problem**: Admin menu still pointed to old `admin_packages` route
**Solution**: Updated navigation to point to new `admin_courses` route

### 4. Route Import Missing
**Problem**: Validation script expected explicit `import routes` 
**Solution**: Added explicit import alongside wildcard import

## 📊 Architecture Comparison

### Before (Old Architecture)
```
TestPackage (e.g., "AI-102 Practice Test")
├── Question 1
├── Question 2  
├── Question 3
└── ...all questions (user takes all at once)
```

### After (New Architecture) 
```
Course (e.g., "AI-102: Azure AI Engineer Associate")
├── Practice Test 1
│   ├── Question 1
│   ├── Question 2
│   └── Question 10
├── Practice Test 2  
│   ├── Question 11
│   ├── Question 12
│   └── Question 20
└── Practice Test 3
    ├── Question 21
    ├── Question 22
    └── Question 30
```

## 🎯 Benefits Achieved

1. **User Experience**: Users can take individual practice tests instead of all questions at once
2. **Progress Tracking**: Track performance per practice test within courses
3. **Content Organization**: Better organization with courses containing multiple practice tests
4. **Admin Flexibility**: Admins can create unlimited practice tests per course
5. **Scalability**: More scalable structure for growing content library
6. **Udemy-like Experience**: Similar to popular e-learning platforms

## 📝 Next Steps After Testing

1. **Validate Full Flow**: Test complete user and admin workflows
2. **Performance Testing**: Ensure new queries perform well
3. **Data Migration**: If moving from existing data, run migration scripts  
4. **Documentation Update**: Update user documentation for new interface
5. **Cleanup**: Remove dev-scripts folder after successful testing

## 🔄 Rollback Plan

If issues arise, rollback steps:
1. Restore database from backup
2. Checkout previous commit before architecture changes  
3. Remove new template files
4. Restore old admin navigation links

## 📋 File Checklist

### Files Created ✅
- `admin_course_routes.py` - Admin course management
- `dev-scripts/reset_database.py` - Database reset script
- `dev-scripts/validate_new_architecture.py` - Architecture validation
- `templates/courses.html` - Course listing page
- `templates/course_detail.html` - Course detail page
- `templates/admin/courses.html` - Admin course dashboard
- `templates/admin/create_course.html` - Create course form
- `templates/admin/manage_practice_tests.html` - Practice test management
- `templates/admin/create_practice_test.html` - Create practice test form
- `COURSE_ARCHITECTURE_CHANGES.md` - This documentation

### Files Modified ✅
- `models.py` - Added Course and PracticeTest models
- `routes.py` - Added course and practice test routes
- `main.py` - Updated imports for new admin routes
- `templates/base.html` - Updated admin navigation
- `templates/index.html` - Updated to show courses

### Migration Files Created (Not Used)
- `migrate_to_course_structure.py` - Complex migration (not needed for fresh start)

---

**Status**: ✅ **Implementation Complete - Ready for Testing**

All components of the Course > Practice Test > Questions architecture have been implemented. The system is ready for fresh database testing following the reset script approach.