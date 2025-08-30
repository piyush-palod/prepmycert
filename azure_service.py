"""
Azure Blob Storage service for image URL generation
"""

import os
import logging
from typing import Optional
from models import CourseAzureMapping

logger = logging.getLogger(__name__)

class AzureBlobService:
    """Service for generating Azure Blob Storage URLs"""
    
    def __init__(self):
        self.storage_account_name = os.environ.get('AZURE_STORAGE_ACCOUNT_NAME')
        self.container_name = os.environ.get('AZURE_CONTAINER_NAME', 'certification-images')
        
        if not self.storage_account_name:
            logger.warning("AZURE_STORAGE_ACCOUNT_NAME not configured")
    
    def generate_image_url(self, test_package_id: int, image_filename: str) -> Optional[str]:
        """
        Generate Azure Blob Storage URL for an image
        
        Args:
            test_package_id: ID of the test package
            image_filename: Name of the image file
            
        Returns:
            Azure Blob URL or None if mapping not found
            
        Format: https://{storage-account}.blob.core.windows.net/{container}/{course-name}/{practice-test-folder}/{filename}
        """
        if not self.storage_account_name:
            logger.error("Azure storage account name not configured")
            return None
        
        # Get Azure mapping from database
        mapping = CourseAzureMapping.query.filter_by(
            test_package_id=test_package_id,
            is_active=True
        ).first()
        
        if not mapping:
            logger.warning(f"No Azure mapping found for test package {test_package_id}")
            return None
        
        # Generate Azure Blob URL
        url = f"https://{self.storage_account_name}.blob.core.windows.net/{self.container_name}/{mapping.azure_folder_name}/{mapping.practice_test_folder}/{image_filename}"
        
        logger.debug(f"Generated Azure URL: {url}")
        return url
    
    def get_azure_mapping(self, test_package_id: int) -> Optional[CourseAzureMapping]:
        """Get the active Azure mapping for a test package"""
        return CourseAzureMapping.query.filter_by(
            test_package_id=test_package_id,
            is_active=True
        ).first()
    
    def validate_configuration(self) -> bool:
        """Check if Azure configuration is properly set up"""
        if not self.storage_account_name:
            logger.error("AZURE_STORAGE_ACCOUNT_NAME environment variable not set")
            return False
        
        if not self.container_name:
            logger.error("AZURE_CONTAINER_NAME environment variable not set")
            return False
        
        return True
    
    def get_base_url(self) -> Optional[str]:
        """Get the base Azure Blob Storage URL"""
        if not self.storage_account_name:
            return None
        
        return f"https://{self.storage_account_name}.blob.core.windows.net/{self.container_name}"

# Global instance
azure_service = AzureBlobService()