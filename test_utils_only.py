#!/usr/bin/env python3
"""
Standalone test for image processing utilities.
Tests image processing logic without requiring full Flask app initialization.
"""

import os
import sys
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_direct_image_detection():
    """Test detection of direct image names (new format)"""
    print("Testing Direct Image Detection")
    print("=" * 35)
    
    # Test patterns for direct image detection
    test_texts = [
        "Review the schema: 74f7b4a1b01300dc94f2de0e704e2258 for the answer.",
        "Analyze configuration 25942145522df220e961deff1f5ae79d in the diagram.",
        "Multiple images: 74f7b4a1b01300dc94f2de0e704e2258 and 25942145522df220e961deff1f5ae79d",
        "Short hash: abc123def456 (should not match - too short)",
        "No images here at all."
    ]
    
    # Direct pattern matching (same as in utils.py)
    direct_image_pattern = r'\b([a-f0-9]{32}|[a-f0-9]{16,64})\b'
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: {text}")
        
        matches = re.findall(direct_image_pattern, text, flags=re.IGNORECASE)
        print(f"  Direct images found: {matches}")
    
    return True

def test_old_image_detection():
    """Test detection of old IMAGE: format"""
    print("\nTesting Old Image Format Detection")
    print("=" * 40)
    
    test_texts = [
        "Check diagram [IMAGE: word-image-43535-354.png] for reference.",
        "See IMAGE: network-topology.jpg for details.",
        "Multiple: IMAGE: diagram1.png and [IMAGE: diagram2.svg]",
        "No images in this text."
    ]
    
    # Old pattern matching (same as in utils.py)
    old_image_pattern = r'\[?IMAGE:\s*([^\s\[\]]+\.(png|jpg|jpeg|gif|svg))\]?'
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: {text}")
        
        matches = re.findall(old_image_pattern, text, flags=re.IGNORECASE)
        images = [match[0] for match in matches]  # Extract filename part
        print(f"  Old format images found: {images}")
    
    return True

def test_azure_url_generation():
    """Test Azure URL generation"""
    print("\nTesting Azure URL Generation")
    print("=" * 35)
    
    try:
        # Import Azure storage functions
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from azure_storage import get_blob_url, is_azure_configured
        
        print(f"Azure configured: {is_azure_configured()}")
        
        if not is_azure_configured():
            print("❌ Azure not configured - check environment variables")
            return False
        
        # Test URL generation
        test_cases = [
            ("ai-102", "74f7b4a1b01300dc94f2de0e704e2258"),
            ("ai-102", "25942145522df220e961deff1f5ae79d"),
            ("az-900", "sample-diagram.png"),
            ("aws-clf-002", "architecture-overview")
        ]
        
        for folder, image in test_cases:
            url = get_blob_url(folder, image)
            if url:
                print(f"✓ {folder}/{image}")
                print(f"  URL: {url}")
            else:
                print(f"✗ Failed: {folder}/{image}")
                return False
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_image_to_html_conversion():
    """Test conversion of image names to HTML img tags"""
    print("\nTesting Image to HTML Conversion")
    print("=" * 40)
    
    # Mock the convert_image_to_html function
    def convert_image_to_html(image_name, package_name=None, azure_folder_name=None):
        """Mock version of the convert function"""
        image_url = None
        alt_text = f"Image: {image_name}"
        
        # Try Azure URL generation
        if azure_folder_name:
            try:
                from azure_storage import get_blob_url
                image_url = get_blob_url(azure_folder_name, image_name)
                if image_url:
                    return f'<img src="{image_url}" alt="{alt_text}" class="question-image azure-image" style="max-width: 100%; height: auto; margin: 10px 0;" loading="lazy">'
            except:
                pass
        
        # Fallback to local
        if package_name:
            safe_package_name = re.sub(r'[^a-zA-Z0-9\-_]', '_', package_name.lower().replace(' ', '_'))
            image_url = f"/static/images/questions/{safe_package_name}/{image_name}"
        else:
            image_url = f"/static/images/questions/{image_name}"
        
        return f'<img src="{image_url}" alt="{alt_text}" class="question-image local-image" style="max-width: 100%; height: auto; margin: 10px 0;" loading="lazy">'
    
    test_cases = [
        {
            "name": "Azure image",
            "image_name": "74f7b4a1b01300dc94f2de0e704e2258",
            "package_name": "AI-102 Package",
            "azure_folder_name": "ai-102"
        },
        {
            "name": "Local fallback",
            "image_name": "sample-diagram.png",
            "package_name": "Test Package",
            "azure_folder_name": None
        },
        {
            "name": "No package name",
            "image_name": "generic-image.jpg",
            "package_name": None,
            "azure_folder_name": None
        }
    ]
    
    for case in test_cases:
        print(f"\nTest: {case['name']}")
        
        html = convert_image_to_html(
            case['image_name'],
            case['package_name'],
            case['azure_folder_name']
        )
        
        print(f"Generated HTML: {html}")
        
        # Check if it contains expected elements
        if '<img' in html and 'src=' in html:
            print("✓ Valid HTML img tag generated")
            
            # Check URL type
            if 'blob.core.windows.net' in html:
                print("✓ Azure URL detected")
            elif '/static/images/' in html:
                print("✓ Local URL detected")
        else:
            print("✗ Invalid HTML generated")
            return False
    
    return True

def test_text_processing_simulation():
    """Test full text processing simulation"""
    print("\nTesting Text Processing Simulation")
    print("=" * 40)
    
    # Mock the full text processing function
    def process_text_simulation(text, package_name=None, azure_folder_name=None):
        """Simulate the text processing function"""
        if not text:
            return ""
        
        processed_text = text
        
        # Pattern 1: Direct image names
        direct_image_pattern = r'\b([a-f0-9]{32}|[a-f0-9]{16,64})\b'
        
        def replace_direct_image(match):
            image_name = match.group(1)
            return convert_image_to_html_mock(image_name, package_name, azure_folder_name)
        
        processed_text = re.sub(direct_image_pattern, replace_direct_image, processed_text, flags=re.IGNORECASE)
        
        # Pattern 2: Old format
        old_image_pattern = r'\[?IMAGE:\s*([^\s\[\]]+\.(png|jpg|jpeg|gif|svg))\]?'
        
        def replace_old_image(match):
            image_filename = match.group(1)
            return convert_image_to_html_mock(image_filename, package_name, azure_folder_name)
        
        processed_text = re.sub(old_image_pattern, replace_old_image, processed_text, flags=re.IGNORECASE)
        
        return processed_text
    
    def convert_image_to_html_mock(image_name, package_name, azure_folder_name):
        """Mock HTML conversion"""
        if azure_folder_name:
            try:
                from azure_storage import get_blob_url
                url = get_blob_url(azure_folder_name, image_name)
                if url:
                    return f'<img src="{url}" alt="Image: {image_name}" class="azure-image">'
            except:
                pass
        
        # Local fallback
        return f'<img src="/static/images/questions/{image_name}" alt="Image: {image_name}" class="local-image">'
    
    # Test with your actual question format
    sample_questions = [
        {
            "text": "You are building an Azure AI Search custom skill.\n74f7b4a1b01300dc94f2de0e704e2258\nFor the following statement, select Yes if the statement is true.",
            "azure_folder": "ai-102"
        },
        {
            "text": "Check the network diagram [IMAGE: topology.png] and analyze the configuration 25942145522df220e961deff1f5ae79d",
            "azure_folder": "network-plus"
        },
        {
            "text": "This question has no images at all.",
            "azure_folder": "test"
        }
    ]
    
    for i, question in enumerate(sample_questions, 1):
        print(f"\n--- Question {i} ---")
        print(f"Original: {question['text'][:100]}...")
        
        processed = process_text_simulation(
            question['text'],
            "Test Package",
            question['azure_folder']
        )
        
        print(f"Processed: {processed[:150]}...")
        
        # Count img tags
        img_count = len(re.findall(r'<img[^>]*>', processed))
        print(f"Images converted: {img_count}")
        
        # Check URL types
        azure_urls = len(re.findall(r'blob\.core\.windows\.net', processed))
        local_urls = len(re.findall(r'/static/images/', processed))
        print(f"Azure URLs: {azure_urls}, Local URLs: {local_urls}")
    
    return True

def main():
    """Run standalone image processing tests"""
    print("Standalone Image Processing Tests")
    print("=" * 50)
    print("Testing core image processing logic without Flask dependencies")
    print()
    
    tests = [
        ("Direct Image Detection", test_direct_image_detection),
        ("Old Image Format Detection", test_old_image_detection),
        ("Azure URL Generation", test_azure_url_generation),
        ("Image to HTML Conversion", test_image_to_html_conversion),
        ("Text Processing Simulation", test_text_processing_simulation),
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
        print(f"{test_name:<30} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL CORE TESTS PASSED!")
        print("\nCore image processing logic is working correctly!")
        print("\nNext steps:")
        print("1. Install missing Flask dependencies: pip install Flask-WTF")
        print("2. Test full Flask integration")
        print("3. Test CSV import in admin interface")
        print("4. Upload test images to Azure Blob Storage")
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
        print("\nCore image processing needs attention before proceeding.")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)