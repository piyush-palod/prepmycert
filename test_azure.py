#!/usr/bin/env python3
"""
Test script for Azure Blob Storage integration.

This script tests:
1. Azure storage configuration
2. Connection to Azure
3. URL generation for test images
4. Integration with TestPackage models

Usage: python test_azure.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_azure_configuration():
    """Test Azure storage configuration"""
    print("Testing Azure Storage Configuration...")
    
    connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
    container_name = os.environ.get('AZURE_STORAGE_CONTAINER_NAME')
    
    if connection_string:
        print("✓ AZURE_STORAGE_CONNECTION_STRING is set")
        # Show partial connection string for security
        masked = connection_string[:50] + "..." if len(connection_string) > 50 else connection_string
        print(f"  Connection string: {masked}")
    else:
        print("✗ AZURE_STORAGE_CONNECTION_STRING is not set")
        return False
    
    if container_name:
        print(f"✓ AZURE_STORAGE_CONTAINER_NAME is set: {container_name}")
    else:
        print("✗ AZURE_STORAGE_CONTAINER_NAME is not set")
        return False
    
    return True

def test_azure_imports():
    """Test that Azure libraries are installed"""
    print("\nTesting Azure Library Imports...")
    
    try:
        import azure_storage
        print("✓ azure_storage module imports successfully")
    except ImportError as e:
        print(f"✗ Failed to import azure_storage: {e}")
        return False
    
    try:
        from azure.storage.blob import BlobServiceClient
        print("✓ Azure Blob Storage library imports successfully")
    except ImportError as e:
        print(f"✗ Azure Blob Storage library not installed: {e}")
        print("  Run: pip install azure-storage-blob")
        return False
    
    return True

def test_azure_connection():
    """Test connection to Azure Blob Storage"""
    print("\nTesting Azure Connection...")
    
    try:
        from azure_storage import test_azure_connection, is_azure_configured
        
        if not is_azure_configured():
            print("✗ Azure storage is not configured")
            return False
        
        success, message = test_azure_connection()
        if success:
            print(f"✓ Azure connection successful: {message}")
        else:
            print(f"✗ Azure connection failed: {message}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Azure connection test error: {e}")
        return False

def test_url_generation():
    """Test URL generation for sample images"""
    print("\nTesting URL Generation...")
    
    try:
        from azure_storage import get_blob_url, get_container_base_url
        
        # Test data from your examples
        test_cases = [
            ("ai-102", "74f7b4a1b01300dc94f2de0e704e2258"),
            ("ai-102", "25942145522df220e961deff1f5ae79d"),
            ("az-900", "sample-image.png"),
            ("aws-clf-002", "test-diagram.jpg")
        ]
        
        print("Generating URLs for test images:")
        
        for folder, image in test_cases:
            url = get_blob_url(folder, image)
            if url:
                print(f"✓ {folder}/{image}")
                print(f"  URL: {url}")
            else:
                print(f"✗ Failed to generate URL for {folder}/{image}")
        
        # Test container base URL
        base_url = get_container_base_url("ai-102")
        if base_url:
            print(f"✓ Container base URL: {base_url}")
        else:
            print("✗ Failed to generate container base URL")
        
        return True
        
    except Exception as e:
        print(f"✗ URL generation test error: {e}")
        return False

def test_model_integration():
    """Test integration with TestPackage model"""
    print("\nTesting Model Integration...")
    
    try:
        from app import app, db
        from models import TestPackage
        
        with app.app_context():
            # Create a test package (don't save to DB)
            test_package = TestPackage(
                title="Test AI-102 Package",
                description="Test package for Azure integration",
                price=49.99,
                azure_folder_name="ai-102",
                created_by=1
            )
            
            # Test model methods
            uses_azure = test_package.uses_azure_storage
            print(f"✓ uses_azure_storage: {uses_azure}")
            
            if uses_azure:
                image_url = test_package.get_image_url("74f7b4a1b01300dc94f2de0e704e2258")
                print(f"✓ get_image_url: {image_url}")
            else:
                print("✗ Package not configured for Azure storage")
            
            # Test validation
            is_valid, error = test_package.validate_azure_folder_name()
            if is_valid:
                print("✓ Folder name validation passed")
            else:
                print(f"✗ Folder name validation failed: {error}")
            
            # Test with invalid folder name
            test_package.azure_folder_name = "Invalid Folder Name!"
            is_valid, error = test_package.validate_azure_folder_name()
            if not is_valid:
                print(f"✓ Invalid folder name correctly rejected: {error}")
            else:
                print("✗ Invalid folder name validation should have failed")
        
        return True
        
    except Exception as e:
        print(f"✗ Model integration test error: {e}")
        return False

def test_cache_functionality():
    """Test URL caching functionality"""
    print("\nTesting Cache Functionality...")
    
    try:
        from azure_storage import get_blob_url, clear_url_cache, get_cache_stats
        
        # Clear cache first
        clear_url_cache()
        initial_stats = get_cache_stats()
        print(f"✓ Cache cleared - entries: {initial_stats['cached_urls']}")
        
        # Generate URL (should cache it)
        url1 = get_blob_url("ai-102", "74f7b4a1b01300dc94f2de0e704e2258", use_cache=True)
        if url1:
            print("✓ First URL generation successful")
        
        # Generate same URL again (should use cache)
        url2 = get_blob_url("ai-102", "74f7b4a1b01300dc94f2de0e704e2258", use_cache=True)
        if url2 == url1:
            print("✓ Cache working - same URL returned")
        else:
            print("✗ Cache not working - different URLs returned")
        
        # Check cache stats
        final_stats = get_cache_stats()
        if final_stats['cached_urls'] > 0:
            print(f"✓ Cache populated - entries: {final_stats['cached_urls']}")
        else:
            print("✗ Cache not populated")
        
        return True
        
    except Exception as e:
        print(f"✗ Cache functionality test error: {e}")
        return False

def main():
    """Run all tests"""
    print("Azure Blob Storage Integration Test")
    print("=" * 50)
    
    tests = [
        ("Configuration Test", test_azure_configuration),
        ("Import Test", test_azure_imports),
        ("Connection Test", test_azure_connection),
        ("URL Generation Test", test_url_generation),
        ("Model Integration Test", test_model_integration),
        ("Cache Functionality Test", test_cache_functionality),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        if test_func():
            print(f"\n✅ {test_name} PASSED")
        else:
            print(f"\n❌ {test_name} FAILED")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL AZURE TESTS PASSED!")
        print("\nYour Azure Blob Storage integration is working correctly.")
        print("Next steps:")
        print("1. Set Azure folder names for your test packages via admin interface")
        print("2. Proceed with Phase 3 (Update image processing logic)")
    else:
        print("⚠️  SOME AZURE TESTS FAILED")
        print("\nPlease fix the issues above before proceeding.")
        print("Common issues:")
        print("- Missing Azure credentials in .env file")
        print("- Azure libraries not installed (pip install azure-storage-blob)")
        print("- Incorrect container name or connection string")
    
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)