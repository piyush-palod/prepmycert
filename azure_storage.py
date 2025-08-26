#!/usr/bin/env python3
"""
Azure Blob Storage service for handling image storage and retrieval.

This module provides utilities to:
1. Generate URLs for images stored in Azure Blob Storage
2. Handle folder-based organization (ai-102, az-900, etc.)
3. Provide fallback mechanisms when Azure is not configured
4. Cache blob URLs for performance

Environment Variables Required:
- AZURE_STORAGE_CONNECTION_STRING: Your Azure storage connection string
- AZURE_STORAGE_CONTAINER_NAME: Container name (default: certification-images)
"""

import os
import logging
from urllib.parse import quote
from flask import current_app
from datetime import datetime, timedelta

# Global variables for caching
_blob_service_client = None
_container_name = None
_connection_string = None
_url_cache = {}
_cache_expiry = {}

def init_azure_storage(app=None):
    """
    Initialize Azure Blob Storage configuration.
    Call this from your app.py to set up Azure storage.
    """
    global _connection_string, _container_name
    
    try:
        if app:
            # Get configuration from Flask app
            _connection_string = app.config.get('AZURE_STORAGE_CONNECTION_STRING') or \
                               os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
            _container_name = app.config.get('AZURE_STORAGE_CONTAINER_NAME') or \
                            os.environ.get('AZURE_STORAGE_CONTAINER_NAME', 'certification-images')
        else:
            # Get from environment directly
            _connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
            _container_name = os.environ.get('AZURE_STORAGE_CONTAINER_NAME', 'certification-images')
        
        if _connection_string:
            logging.info("Azure Blob Storage configured successfully")
            logging.info(f"Container: {_container_name}")
        else:
            logging.warning("Azure Blob Storage not configured - missing connection string")
        
    except Exception as e:
        logging.error(f"Failed to initialize Azure storage: {e}")

def is_azure_configured():
    """Check if Azure Blob Storage is properly configured"""
    return bool(_connection_string and _container_name)

def get_blob_service_client():
    """Get or create Azure Blob Service Client"""
    global _blob_service_client
    
    if not is_azure_configured():
        return None
    
    if _blob_service_client is None:
        try:
            # Try different import methods to handle various Python environments
            try:
                from azure.storage.blob import BlobServiceClient
            except ImportError:
                # Try alternative import for different environments
                import sys
                import importlib.util
                
                # Check if azure package exists
                azure_spec = importlib.util.find_spec("azure")
                if azure_spec is None:
                    raise ImportError("Azure package not found")
                
                # Force reimport
                import azure.storage.blob
                from azure.storage.blob import BlobServiceClient
            
            _blob_service_client = BlobServiceClient.from_connection_string(_connection_string)
            logging.debug("Created new BlobServiceClient")
        except ImportError as e:
            logging.error(f"Azure Storage libraries not available: {e}")
            logging.error("Please ensure azure-storage-blob is installed in the correct Python environment")
            return None
        except Exception as e:
            logging.error(f"Failed to create BlobServiceClient: {e}")
            return None
    
    return _blob_service_client

def parse_connection_string():
    """Parse Azure connection string to get account name and key"""
    if not _connection_string:
        return None, None
    
    try:
        # Parse connection string to extract AccountName
        parts = _connection_string.split(';')
        account_name = None
        
        for part in parts:
            if part.startswith('AccountName='):
                account_name = part.split('=', 1)[1]
                break
        
        return account_name, None
    except Exception as e:
        logging.error(f"Failed to parse connection string: {e}")
        return None, None

def get_blob_url(folder_name, image_name, use_cache=True):
    """
    Generate a direct URL to a blob in Azure Storage.
    
    Args:
        folder_name (str): The folder name in the container (e.g., 'ai-102')
        image_name (str): The image filename (e.g., '74f7b4a1b01300dc94f2de0e704e2258')
        use_cache (bool): Whether to use URL caching
    
    Returns:
        str: Full URL to the blob, or None if Azure is not configured
    """
    if not is_azure_configured():
        logging.debug("Azure not configured - cannot generate blob URL")
        return None
    
    # Create cache key
    cache_key = f"{folder_name}/{image_name}"
    
    # Check cache first (cache for 1 hour)
    if use_cache and cache_key in _url_cache:
        if datetime.utcnow() < _cache_expiry.get(cache_key, datetime.min):
            return _url_cache[cache_key]
        else:
            # Cache expired, remove it
            _url_cache.pop(cache_key, None)
            _cache_expiry.pop(cache_key, None)
    
    try:
        account_name, _ = parse_connection_string()
        if not account_name:
            logging.error("Could not extract account name from connection string")
            return None
        
        # Construct blob name (folder/filename)
        blob_name = f"{folder_name}/{image_name}"
        
        # Generate direct URL
        # Format: https://{account}.blob.core.windows.net/{container}/{blob}
        url = f"https://{account_name}.blob.core.windows.net/{_container_name}/{quote(blob_name)}"
        
        # Cache the URL for 1 hour
        if use_cache:
            _url_cache[cache_key] = url
            _cache_expiry[cache_key] = datetime.utcnow() + timedelta(hours=1)
        
        logging.debug(f"Generated blob URL: {url}")
        return url
        
    except Exception as e:
        logging.error(f"Failed to generate blob URL for {folder_name}/{image_name}: {e}")
        return None

def get_container_base_url(folder_name):
    """
    Generate base URL for a folder in the container.
    Useful for debugging or batch operations.
    
    Args:
        folder_name (str): The folder name (e.g., 'ai-102')
    
    Returns:
        str: Base URL for the folder, or None if Azure is not configured
    """
    if not is_azure_configured():
        return None
    
    try:
        account_name, _ = parse_connection_string()
        if not account_name:
            return None
        
        # Generate folder base URL
        base_url = f"https://{account_name}.blob.core.windows.net/{_container_name}/{quote(folder_name)}/"
        logging.debug(f"Generated container base URL: {base_url}")
        return base_url
        
    except Exception as e:
        logging.error(f"Failed to generate container base URL for {folder_name}: {e}")
        return None

def test_azure_connection():
    """
    Test Azure Blob Storage connection.
    Returns tuple (success: bool, message: str)
    """
    if not is_azure_configured():
        return False, "Azure storage not configured - missing connection string or container name"
    
    try:
        client = get_blob_service_client()
        if not client:
            return False, "Failed to create blob service client"
        
        # Try to get container properties (this tests the connection)
        container_client = client.get_container_client(_container_name)
        properties = container_client.get_container_properties()
        
        return True, f"Connection successful to container '{_container_name}'"
        
    except Exception as e:
        error_msg = str(e)
        if "The specified container does not exist" in error_msg:
            return False, f"Container '{_container_name}' does not exist in your storage account"
        elif "AuthenticationFailed" in error_msg:
            return False, "Authentication failed - check your connection string and account key"
        else:
            return False, f"Connection test failed: {error_msg}"

def list_blobs_in_folder(folder_name, max_results=10):
    """
    List blobs in a specific folder (for debugging/testing).
    
    Args:
        folder_name (str): The folder name to list
        max_results (int): Maximum number of results to return
    
    Returns:
        list: List of blob names, or None if error
    """
    if not is_azure_configured():
        return None
    
    try:
        client = get_blob_service_client()
        if not client:
            return None
        
        container_client = client.get_container_client(_container_name)
        
        # List blobs with folder prefix
        blobs = container_client.list_blobs(name_starts_with=f"{folder_name}/")
        
        blob_names = []
        count = 0
        for blob in blobs:
            blob_names.append(blob.name)
            count += 1
            if count >= max_results:
                break
        
        logging.debug(f"Found {len(blob_names)} blobs in folder '{folder_name}'")
        return blob_names
        
    except Exception as e:
        logging.error(f"Failed to list blobs in folder '{folder_name}': {e}")
        return None

def clear_url_cache():
    """Clear the URL cache (useful for testing or if URLs change)"""
    global _url_cache, _cache_expiry
    _url_cache.clear()
    _cache_expiry.clear()
    logging.debug("Cleared URL cache")

def get_cache_stats():
    """Get cache statistics (for monitoring/debugging)"""
    return {
        'cached_urls': len(_url_cache),
        'cache_entries': list(_url_cache.keys())[:10],  # First 10 entries
        'azure_configured': is_azure_configured(),
        'container_name': _container_name
    }

# Development/Testing utilities
def generate_test_urls(folder_name, image_names):
    """
    Generate test URLs for a list of images (useful for testing).
    
    Args:
        folder_name (str): Folder name
        image_names (list): List of image names
    
    Returns:
        dict: Mapping of image names to URLs
    """
    results = {}
    for image_name in image_names:
        url = get_blob_url(folder_name, image_name)
        results[image_name] = url
    return results

def validate_folder_name(folder_name):
    """
    Validate Azure folder name according to blob naming rules.
    
    Args:
        folder_name (str): The folder name to validate
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not folder_name:
        return False, "Folder name cannot be empty"
    
    if len(folder_name) < 1 or len(folder_name) > 1024:
        return False, "Folder name must be between 1 and 1024 characters"
    
    # Check for invalid characters
    invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        if char in folder_name:
            return False, f"Folder name cannot contain '{char}'"
    
    # Check for trailing dots or spaces
    if folder_name.endswith('.') or folder_name.endswith(' '):
        return False, "Folder name cannot end with '.' or space"
    
    return True, None

# Initialize with environment variables when module is imported
init_azure_storage()