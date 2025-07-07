# Question Images

This folder contains images used in questions and answer options.

## How to Use Images in Questions

1. Upload your image files (PNG, JPG, JPEG, GIF, SVG) to this folder
2. In your CSV file or when creating questions, reference images using this format:
   ```
   IMAGE: filename.png
   ```

## Example Usage

In a question text:
```
What does this diagram show? IMAGE: aws-architecture-diagram.png
```

In an answer option:
```
IMAGE: option-a-diagram.jpg This represents the correct architecture
```

## Supported Formats
- PNG
- JPG/JPEG  
- GIF
- SVG

## Notes
- Images will be automatically resized to fit properly in the question interface
- Make sure filenames match exactly (case-sensitive)
- Use descriptive filenames for easier management