# Azure Blob Storage Image Integration - Setup Guide

## Overview

The PrepMyCert application has been enhanced with Azure Blob Storage integration for handling images in certification questions. This system replaces the previous local image handling with a production-ready cloud solution.

## Features Implemented

### ✅ Core Components

1. **Database-Driven Course Mappings** - Dynamic mapping between test packages and Azure folder structures
2. **Image Processing Pipeline** - Automatic conversion of `IMAGE: filename.png` references to Azure URLs  
3. **Admin Management Interface** - Web-based tools for managing course mappings and processing images
4. **Command-Line Tools** - Scripts for bulk processing and validation
5. **Template Integration** - Updated templates to use processed Azure URLs

### ✅ Key Files Created/Modified

#### New Files
- `azure_service.py` - Core Azure Blob Storage service
- `image_processor.py` - Image reference processing logic
- `admin_course_mapping_routes.py` - Admin routes for mapping management
- `migrate_azure_schema.py` - Database migration script
- `process_azure_images.py` - Command-line processing tool
- `validate_azure_images.py` - Validation and testing tool
- `templates/admin/course_mappings.html` - Admin interface for mappings
- `templates/admin/bulk_process_images.html` - Bulk processing interface

#### Modified Files
- `models.py` - Added CourseAzureMapping model and processed text fields
- `utils.py` - Updated CSV import to use Azure processing
- `main.py` - Added admin route imports
- `requirements.txt` - Added Azure dependencies
- `.env.example` - Added Azure configuration variables
- `templates/test_results.html` - Use processed text for images
- `templates/test_taking.html` - Use processed text for images

## Setup Instructions

### 1. Environment Configuration

Add these variables to your `.env` file:

```bash
# Azure Blob Storage Configuration
AZURE_STORAGE_ACCOUNT_NAME=yourstorageaccount
AZURE_CONTAINER_NAME=certification-images
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Database Migration

```bash
python migrate_azure_schema.py
```

### 4. Azure Container Structure

Organize your Azure Blob Storage container as follows:

```
certification-images/
├── az-900/
│   ├── practice-test-1/
│   │   ├── image1.png
│   │   └── image2.png
│   └── practice-test-2/
├── ai-102/
│   └── practice-test-1/
└── ...
```

## Usage Workflow

### 1. Create Course Mappings

1. Access admin panel at `/admin/course-mappings`
2. Map each test package to its corresponding Azure folder name
3. Specify practice test folder (usually `practice-test-1`)

### 2. Import Questions

When importing CSV files with `IMAGE: filename.png` references:
- Images are automatically processed during import
- Azure URLs are generated and stored in database
- Original text is preserved for backward compatibility

### 3. Process Existing Questions

For existing questions with IMAGE references:

```bash
# Process all courses
python process_azure_images.py all

# Process specific package
python process_azure_images.py package 1

# Show statistics
python process_azure_images.py stats
```

### 4. Validate Integration

```bash
# Full validation report
python validate_azure_images.py report

# Check specific components
python validate_azure_images.py config
python validate_azure_images.py mappings
python validate_azure_images.py urls
```

## How It Works

### Image Processing Flow

1. **CSV Import**: Questions with `IMAGE: filename.png` are detected
2. **Mapping Lookup**: Test package is mapped to Azure folder structure  
3. **URL Generation**: Azure Blob URL is generated using pattern:
   ```
   https://storageaccount.blob.core.windows.net/certification-images/course-name/practice-test-1/filename.png
   ```
4. **HTML Conversion**: `IMAGE:` reference becomes `<img>` tag with Azure URL
5. **Database Storage**: Processed HTML is stored alongside original text

### Template Rendering

Templates automatically use processed versions when available:

```html
<!-- Before: -->
{{ question.question_text|safe }}

<!-- After: -->
{{ question.processed_question_text|safe if question.processed_question_text else question.question_text|safe }}
```

## Admin Interface

### Course Mappings Management

- **Create Mappings**: Map test packages to Azure folders
- **Edit Mappings**: Update folder names or practice test numbers
- **Test URLs**: Validate URL generation
- **View Statistics**: See unprocessed item counts

### Bulk Processing

- **Process by Course**: Handle one course at a time
- **Batch Processing**: Process all courses simultaneously  
- **Progress Tracking**: Monitor processing status
- **Validation**: Check results after processing

## Benefits

### Production Ready
- Direct Azure Blob Storage delivery
- No local file dependencies
- Global CDN capabilities
- Scalable cloud storage

### Admin Friendly
- Web interface for all management tasks
- No code changes needed for new courses
- Visual progress tracking
- Comprehensive validation tools

### Developer Friendly
- Clean separation of concerns
- Backward compatibility maintained
- Comprehensive error handling
- Detailed logging and validation

## Troubleshooting

### Common Issues

1. **Missing Azure Configuration**
   - Ensure `AZURE_STORAGE_ACCOUNT_NAME` is set
   - Verify container name is correct

2. **Course Mapping Not Found**
   - Create mapping via admin interface
   - Check mapping is marked as active

3. **Images Not Displaying**
   - Verify Azure container structure matches mappings
   - Check image files exist at expected paths
   - Use validation tool to test URLs

### Validation Commands

```bash
# Check configuration
python validate_azure_images.py config

# Test URL accessibility (sample of 10)
python validate_azure_images.py accessibility 10

# Find unprocessed items
python validate_azure_images.py unprocessed
```

## Migration from Local Images

If migrating from local image storage:

1. Upload local images to Azure following the folder structure
2. Create course mappings for all test packages
3. Run bulk processing to convert existing questions
4. Validate all URLs are accessible
5. Remove local image files once validated

## Security Considerations

- Azure Blob Storage uses HTTPS by default
- No authentication required for public blob access
- Container and folder structure provides organization
- No sensitive data in image URLs

## Next Steps

Consider implementing:
- Image optimization and compression
- CDN configuration for faster delivery
- Automatic image validation during upload
- Image versioning for updates
- Thumbnail generation for previews

---

For technical support or questions about this integration, refer to the individual file documentation or contact the development team.