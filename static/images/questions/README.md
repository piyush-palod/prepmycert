
# Question Images

This directory contains images used in test questions.

## Structure

### Package-Specific Images (Recommended)
- `package_1/` - Images for test package 1
- `package_2/` - Images for test package 2
- etc.

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
