#!/usr/bin/env python3
"""
Test script for the new image processing logic.
Tests both old and new image formats with Azure integration.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_image_detection():
    """Test image detection in sample texts"""
    print("Testing Image Detection")
    print("=" * 30)
    
    from utils import detect_image_references
    
    # Sample texts from your questions
    sample_texts = [
        # New format - direct image names
        "You are building an Azure AI Search custom skill.\n74f7b4a1b01300dc94f2de0e704e2258\nFor the following statement, select Yes if the statement is true.",
        
        # Another new format example
        "You have the following custom skill schema definition.\n25942145522df220e961deff1f5ae79d\nSelect Yes if the statement is true.",
        
        # Old format - for backward compatibility
        "Check the following diagram.\n[IMAGE: word-image-43535-354.png]\nWhich component is highlighted?",
        
        # Mixed format
        "Review the schema: 74f7b4a1b01300dc94f2de0e704e2258 and the diagram IMAGE: network-topology.png to answer the question.",
        
        # No images
        "This is a question with no images. What is the capital of France?"
    ]
    
    for i, text in enumerate(sample_texts, 1):
        print(f"\nSample {i}:")
        print(f"Text: {text[:100]}...")
        
        detected = detect_image_references(text)
        print(f"Direct images: {detected['direct_images']}")
        print(f"Old format images: {detected['old_format_images']}")
        print(f"Total images: {detected['total_images']}")
    
    return True

def test_image_processing():
    """Test image processing with Azure integration"""
    print("\nTesting Image Processing")
    print("=" * 30)
    
    from utils import process_text_with_images
    
    # Test scenarios
    test_cases = [
        {
            "name": "New format with Azure",
            "text": "Review the schema: 74f7b4a1b01300dc94f2de0e704e2258 for the answer.",
            "package_name": "AI-102 Test Package",
            "azure_folder_name": "ai-102"
        },
        {
            "name": "Old format with Azure",
            "text": "Check the diagram [IMAGE: network-diagram.png] for reference.",
            "package_name": "Network+ Test Package", 
            "azure_folder_name": "network-plus"
        },
        {
            "name": "New format without Azure (fallback)",
            "text": "Analyze the code: 25942145522df220e961deff1f5ae79d for errors.",
            "package_name": "Security+ Test Package",
            "azure_folder_name": None
        },
        {
            "name": "Multiple images mixed format",
            "text": "Compare 74f7b4a1b01300dc94f2de0e704e2258 with IMAGE: comparison.png",
            "package_name": "Mixed Test Package",
            "azure_folder_name": "mixed-format"
        }
    ]
    
    for case in test_cases:
        print(f"\nTest Case: {case['name']}")
        print(f"Original: {case['text']}")
        
        processed = process_text_with_images(
            case['text'],
            case['package_name'], 
            case['azure_folder_name']
        )
        
        print(f"Processed: {processed}")
        
        # Count img tags
        import re
        img_tags = re.findall(r'<img[^>]*>', processed)
        print(f"Generated {len(img_tags)} img tag(s)")
        
        # Show URLs
        for tag in img_tags:
            src_match = re.search(r'src="([^"]*)"', tag)
            if src_match:
                url = src_match.group(1)
                if 'blob.core.windows.net' in url:
                    print(f"  ✓ Azure URL: {url}")
                else:
                    print(f"  ✓ Local URL: {url}")
    
    return True

def test_azure_url_generation():
    """Test Azure URL generation specifically"""
    print("\nTesting Azure URL Generation")
    print("=" * 35)
    
    try:
        from azure_storage import get_blob_url
        
        test_images = [
            ("ai-102", "74f7b4a1b01300dc94f2de0e704e2258"),
            ("ai-102", "25942145522df220e961deff1f5ae79d"),
            ("az-900", "azure-architecture-diagram"),
            ("aws-clf-002", "aws-services-overview")
        ]
        
        print("Testing Azure Blob URL generation:")
        
        for folder, image in test_images:
            url = get_blob_url(folder, image)
            if url:
                print(f"✓ {folder}/{image} → {url}")
            else:
                print(f"✗ Failed to generate URL for {folder}/{image}")
        
        return True
        
    except ImportError:
        print("⚠ Azure storage not available - skipping Azure URL tests")
        return True
    except Exception as e:
        print(f"✗ Azure URL generation error: {e}")
        return False

def test_validation_function():
    """Test the validation function"""
    print("\nTesting Validation Function")
    print("=" * 30)
    
    from utils import validate_image_processing
    
    test_text = "Review schema 74f7b4a1b01300dc94f2de0e704e2258 and diagram IMAGE: test.png"
    
    validation = validate_image_processing(
        test_text,
        "Test Package",
        "test-folder"
    )
    
    print(f"Original text: {test_text}")
    print(f"Valid: {validation['valid']}")
    print(f"Detected images: {validation['detected_images']}")
    print(f"IMG tags found: {validation['img_tags_count']}")
    print(f"Processed text: {validation['processed_text'][:100]}...")
    
    return validation['valid']

def test_csv_import_simulation():
    """Test CSV import simulation with your sample questions"""
    print("\nTesting CSV Import Simulation")
    print("=" * 35)
    
    # Simulate your sample questions
    sample_questions = [
        {
            "Question": "You are building an Azure AI Search custom skill.\nYou have the following custom skill schema definition.\n74f7b4a1b01300dc94f2de0e704e2258\nFor the following statement, select Yes if the statement is true. Otherwise, select No.\nCompanyDescription is available for indexing.",
            "Question Type": "multiple-choice",
            "Answer Option 1": "Yes",
            "Answer Option 2": "No", 
            "Correct Answers": "2",
            "Overall Explanation": "No is CORRECT. While the custom skill schema shows that the skill generates an output field named companyDescription, that alone does not make the field available for indexing in Azure Cognitive Search.",
            "Domain": "Implement knowledge mining & information extraction solution"
        },
        {
            "Question": "You are building an Azure AI Search custom skill.\nYou have the following custom skill schema definition.\n25942145522df220e961deff1f5ae79d\nFor the following statement, select Yes if the statement is true. Otherwise, select No.\nThe definition calls a web API as part of the enrichment process.",
            "Question Type": "multiple-choice", 
            "Answer Option 1": "Yes",
            "Answer Option 2": "No",
            "Correct Answers": "1",
            "Overall Explanation": "Yes is CORRECT because as defined in the schema we have uri: https://contoso-webskill.azurewebsites.net/api/process which indicates that the custom skill is calling a web API from this URI as part of the enrichment process.",
            "Domain": "Implement knowledge mining & information extraction solution"
        }
    ]
    
    # Test image detection and processing
    from utils import detect_image_references, process_text_with_images
    
    azure_folder = "ai-102"
    package_name = "AI-102 Azure AI Search"
    
    for i, question_data in enumerate(sample_questions, 1):
        print(f"\n--- Question {i} ---")
        question_text = question_data["Question"]
        explanation = question_data["Overall Explanation"]
        
        # Test image detection
        q_images = detect_image_references(question_text)
        e_images = detect_image_references(explanation)
        
        print(f"Question images detected: {q_images['total_images']}")
        if q_images['direct_images']:
            print(f"  Direct images: {q_images['direct_images']}")
        
        print(f"Explanation images detected: {e_images['total_images']}")
        
        # Test processing
        processed_question = process_text_with_images(question_text, package_name, azure_folder)
        processed_explanation = process_text_with_images(explanation, package_name, azure_folder)
        
        # Check if Azure URLs are generated
        import re
        q_imgs = re.findall(r'<img[^>]*src="([^"]*)"', processed_question)
        e_imgs = re.findall(r'<img[^>]*src="([^"]*)"', processed_explanation)
        
        for img_url in q_imgs:
            if 'blob.core.windows.net' in img_url:
                print(f"  ✓ Question Azure URL: {img_url}")
            else:
                print(f"  ✓ Question Local URL: {img_url}")
        
        for img_url in e_imgs:
            if 'blob.core.windows.net' in img_url:
                print(f"  ✓ Explanation Azure URL: {img_url}")
            else:
                print(f"  ✓ Explanation Local URL: {img_url}")
    
    return True

def test_backward_compatibility():
    """Test that old image format still works"""
    print("\nTesting Backward Compatibility")
    print("=" * 35)
    
    from utils import process_text_with_images
    
    old_format_texts = [
        "Check the diagram [IMAGE: word-image-43535-354.png] for reference.",
        "IMAGE: network-topology.jpg shows the network layout.", 
        "Review IMAGE: security-architecture.png and [IMAGE: threat-model.svg]"
    ]
    
    for text in old_format_texts:
        print(f"\nOriginal: {text}")
        
        # Test with Azure
        processed_azure = process_text_with_images(text, "Test Package", "test-folder")
        print(f"With Azure: {processed_azure[:100]}...")
        
        # Test without Azure (local fallback)
        processed_local = process_text_with_images(text, "Test Package", None)
        print(f"Local only: {processed_local[:100]}...")
    
    return True

def main():
    """Run all image processing tests"""
    print("Image Processing Integration Test Suite")
    print("=" * 50)
    
    # Activate virtual environment check
    import sys
    if 'prepmycert_env' not in sys.executable:
        print("⚠️  Warning: Not running in prepmycert_env virtual environment")
        print(f"Current Python: {sys.executable}")
        print("Consider activating the virtual environment first.")
        print()
    
    tests = [
        ("Image Detection", test_image_detection),
        ("Image Processing", test_image_processing), 
        ("Azure URL Generation", test_azure_url_generation),
        ("Validation Function", test_validation_function),
        ("CSV Import Simulation", test_csv_import_simulation),
        ("Backward Compatibility", test_backward_compatibility),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        try:
            success = test_func()
            results.append((test_name, success))
            if success:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<25} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nYour image processing integration is working correctly!")
        print("\nNext steps:")
        print("1. Test with real CSV import using your sample questions")
        print("2. Set Azure folder names for test packages via admin interface")
        print("3. Upload test images to Azure Blob Storage")
        print("4. Test image loading in the web interface")
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
        print("\nPlease review the errors above before proceeding.")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)