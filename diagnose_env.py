#!/usr/bin/env python3
"""
Python Environment Diagnostic Script
This script helps diagnose Python environment and Azure package issues.
"""

import sys
import os
import importlib.util

def diagnose_python_environment():
    """Diagnose current Python environment"""
    print("Python Environment Diagnostic")
    print("=" * 50)
    
    # Python version and executable
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    print(f"Python Path: {sys.path[:3]}...")  # Show first 3 paths
    print()
    
    # Check if we're in conda/anaconda
    if 'anaconda' in sys.executable.lower() or 'conda' in sys.executable.lower():
        print("✓ Running in Anaconda/Conda environment")
        # Try to get conda env name
        conda_env = os.environ.get('CONDA_DEFAULT_ENV', 'Unknown')
        print(f"  Conda Environment: {conda_env}")
    else:
        print("• Running in standard Python environment")
    print()

def check_azure_packages():
    """Check Azure package availability"""
    print("Azure Package Diagnostic")
    print("=" * 30)
    
    packages_to_check = [
        'azure',
        'azure.storage',
        'azure.storage.blob',
        'azure.identity'
    ]
    
    for package in packages_to_check:
        try:
            spec = importlib.util.find_spec(package)
            if spec:
                print(f"✓ {package} - Found at: {spec.origin or 'Built-in'}")
            else:
                print(f"✗ {package} - Not found")
        except Exception as e:
            print(f"✗ {package} - Error checking: {e}")
    
    print()

def test_direct_import():
    """Test direct Azure imports"""
    print("Direct Import Test")
    print("=" * 20)
    
    try:
        print("Testing: import azure")
        import azure
        print(f"✓ azure imported successfully from: {azure.__file__}")
    except ImportError as e:
        print(f"✗ Failed to import azure: {e}")
        return False
    
    try:
        print("Testing: from azure.storage.blob import BlobServiceClient")
        from azure.storage.blob import BlobServiceClient
        print("✓ BlobServiceClient imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import BlobServiceClient: {e}")
        return False

def suggest_fixes():
    """Suggest potential fixes"""
    print("\nPotential Fixes")
    print("=" * 20)
    
    if 'anaconda' in sys.executable.lower():
        print("You're using Anaconda. Try these commands:")
        print("1. conda install -c conda-forge azure-storage-blob")
        print("2. conda install -c conda-forge azure-identity")
        print("3. Or use pip in conda: pip install azure-storage-blob azure-identity")
    else:
        print("You're using standard Python. Try:")
        print("1. pip install --upgrade azure-storage-blob azure-identity")
        print("2. pip install --force-reinstall azure-storage-blob")
    
    print("\nAlternatively:")
    print("- Create a new virtual environment")
    print("- Install packages in that environment")
    print("- Run your Flask app from that environment")

def main():
    diagnose_python_environment()
    check_azure_packages()
    
    if test_direct_import():
        print("\n🎉 Azure packages are working correctly!")
        print("The issue might be in the azure_storage.py module.")
    else:
        print("\n⚠️  Azure packages are not properly installed.")
        suggest_fixes()

if __name__ == '__main__':
    main()