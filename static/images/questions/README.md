
# Question Images

This directory contains images used in test questions.

## Structure

### Package-Specific Images (Recommended)
- `az-900/` - Images for Microsoft Azure Fundamentals
- `dp-100/` - Images for Azure Data Scientist Associate
- `sc-900/` - Images for Microsoft Security Fundamentals
- etc.

**Note:** Folder names are automatically generated from package titles (lowercase, spaces/special chars converted to hyphens)

### Legacy Images (Backward Compatibility)
- Root directory - Images from before package-specific structure

## Usage in CSV

Reference images in your CSV files using:
- `IMAGE: filename.png`
- `[IMAGE: filename.png]`

The system will automatically look for images in the appropriate package folder based on the test package being imported.

## Image Guidelines

1. Use descriptive filenames
2. Supported formats: PNG, JPG, JPEG, GIF, SVG
3. Keep file sizes reasonable for web display
4. Images will be automatically resized to fit question containers

## Folder Naming Convention

Package titles are converted to folder names using these rules:
- Convert to lowercase
- Remove special characters (keep only letters, numbers, spaces, hyphens)
- Replace spaces and multiple hyphens with single hyphens
- Example: "Microsoft Azure Fundamentals AZ-900" → "microsoft-azure-fundamentals-az-900"
