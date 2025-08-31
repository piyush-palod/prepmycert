import os
import re
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

class AzureImageService:
    def __init__(self):
        self.connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        self.container_name = os.environ.get('AZURE_CONTAINER_NAME', 'certification-images')
        self.account_name = os.environ.get('AZURE_STORAGE_ACCOUNT_NAME', 'prepmycertimages')
        self.base_url = os.environ.get('AZURE_BLOB_BASE_URL', 'https://prepmycertimages.blob.core.windows.net/certification-images')
        
        if not self.connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable is required")
        
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
    
    def generate_sas_token(self, blob_name, expiry_days=30):
        """Generate SAS token for a specific blob with 30-day expiry"""
        try:
            # Extract account key from connection string for SAS generation
            account_key = None
            for part in self.connection_string.split(';'):
                if part.startswith('AccountKey='):
                    account_key = part.split('AccountKey=')[1]
                    break
            
            if not account_key:
                logger.error("Could not extract account key from connection string")
                return None
            
            # Set permissions and expiry
            permissions = BlobSasPermissions(read=True)
            expiry = datetime.utcnow() + timedelta(days=expiry_days)
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=account_key,
                permission=permissions,
                expiry=expiry
            )
            
            return sas_token
            
        except Exception as e:
            logger.error(f"Error generating SAS token for {blob_name}: {str(e)}")
            return None
    
    def get_image_url_with_sas(self, azure_folder, filename):
        """Get full Azure blob URL with SAS token"""
        blob_name = f"{azure_folder}/{filename}"
        sas_token = self.generate_sas_token(blob_name)
        
        if sas_token:
            return f"{self.base_url}/{blob_name}?{sas_token}"
        else:
            # Fallback to URL without SAS (might not work if blob is private)
            logger.warning(f"Using URL without SAS token for {blob_name}")
            return f"{self.base_url}/{blob_name}"
    
    def upload_image(self, file, azure_folder, filename=None):
        """Upload image file to Azure blob storage"""
        try:
            if not filename:
                filename = secure_filename(file.filename)
            
            # Validate file size (2MB limit)
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset
            
            max_size = 2 * 1024 * 1024  # 2MB
            if file_size > max_size:
                return {'success': False, 'error': f'File size ({file_size} bytes) exceeds 2MB limit'}
            
            # Validate file extension
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            if file_ext not in allowed_extensions:
                return {'success': False, 'error': f'File type .{file_ext} not allowed. Use: {", ".join(allowed_extensions)}'}
            
            # Create blob path
            blob_name = f"{azure_folder}/{filename}"
            
            # Upload to Azure
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.upload_blob(file.read(), overwrite=True)
            
            # Get URL with SAS token
            image_url = self.get_image_url_with_sas(azure_folder, filename)
            
            return {
                'success': True,
                'filename': filename,
                'blob_name': blob_name,
                'url': image_url,
                'size': file_size
            }
            
        except Exception as e:
            logger.error(f"Error uploading image {filename} to {azure_folder}: {str(e)}")
            return {'success': False, 'error': f'Upload failed: {str(e)}'}
    
    def list_images(self, azure_folder):
        """List all images in a specific course folder"""
        try:
            blob_list = []
            blobs = self.blob_service_client.get_container_client(self.container_name).list_blobs(
                name_starts_with=f"{azure_folder}/"
            )
            
            for blob in blobs:
                # Skip if it's a folder (ends with /)
                if blob.name.endswith('/'):
                    continue
                
                # Extract filename
                filename = blob.name.split('/')[-1]
                
                # Get URL with SAS token
                image_url = self.get_image_url_with_sas(azure_folder, filename)
                
                blob_list.append({
                    'filename': filename,
                    'blob_name': blob.name,
                    'url': image_url,
                    'size': blob.size,
                    'last_modified': blob.last_modified
                })
            
            return {'success': True, 'images': blob_list}
            
        except Exception as e:
            logger.error(f"Error listing images in {azure_folder}: {str(e)}")
            return {'success': False, 'error': f'Failed to list images: {str(e)}'}
    
    def delete_image(self, azure_folder, filename):
        """Delete an image from Azure blob storage"""
        try:
            blob_name = f"{azure_folder}/{filename}"
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.delete_blob()
            
            return {'success': True, 'message': f'Deleted {filename}'}
            
        except Exception as e:
            logger.error(f"Error deleting image {filename} from {azure_folder}: {str(e)}")
            return {'success': False, 'error': f'Delete failed: {str(e)}'}
    
    def process_text_with_images(self, text, azure_folder):
        """
        Process text and replace image references with Azure URLs
        Supports both 'IMAGE: filename.png' and existing HTML img tags
        Stores processed HTML directly - no need to reprocess during display
        """
        if not text or not azure_folder:
            return text
        
        text = str(text).strip()
        
        # Pattern 1: Convert IMAGE: filename.png to full HTML img tags
        image_pattern = r'\[?IMAGE:\s*([^\s\[\]]+\.(png|jpg|jpeg|gif))\]?'
        
        def replace_image_reference(match):
            filename = match.group(1)
            image_url = self.get_image_url_with_sas(azure_folder, filename)
            return f'<img src="{image_url}" alt="{filename}" class="img-fluid question-image" style="max-width: 100%; height: auto; margin: 10px 0;">'
        
        # Replace IMAGE: references
        processed_text = re.sub(image_pattern, replace_image_reference, text, flags=re.IGNORECASE)
        
        # Pattern 2: Update existing HTML img tags that reference Azure images without SAS tokens
        # This handles cases where admin manually writes HTML img tags
        azure_img_pattern = rf'<img([^>]*?)src=["\']({re.escape(self.base_url)}/{re.escape(azure_folder)}/[^"\'?]+)(\?[^"\']*)?["\']([^>]*?)>'
        
        def update_existing_img_tags(match):
            pre_src = match.group(1) if match.group(1) else ''
            base_url_with_file = match.group(2)
            existing_params = match.group(3) if match.group(3) else ''
            post_src = match.group(4) if match.group(4) else ''
            
            # Extract filename from URL
            filename = base_url_with_file.split('/')[-1]
            
            # Generate new URL with fresh SAS token
            new_url = self.get_image_url_with_sas(azure_folder, filename)
            
            # Ensure proper classes and styling
            attrs = f'{pre_src} {post_src}'.strip()
            if 'class=' not in attrs:
                attrs += ' class="img-fluid question-image"'
            if 'style=' not in attrs:
                attrs += ' style="max-width: 100%; height: auto; margin: 10px 0;"'
            
            return f'<img{" " + attrs if attrs else ""} src="{new_url}">'
        
        # Update existing img tags
        processed_text = re.sub(azure_img_pattern, update_existing_img_tags, processed_text)
        
        return processed_text
    
    def get_course_image_info(self, azure_folder):
        """Get summary information about images in a course folder"""
        try:
            images_result = self.list_images(azure_folder)
            if images_result['success']:
                images = images_result['images']
                total_size = sum(img['size'] for img in images)
                return {
                    'success': True,
                    'total_images': len(images),
                    'total_size_mb': round(total_size / (1024 * 1024), 2),
                    'images': images
                }
            else:
                return images_result
                
        except Exception as e:
            logger.error(f"Error getting course image info for {azure_folder}: {str(e)}")
            return {'success': False, 'error': f'Failed to get image info: {str(e)}'}

# Global instance
azure_service = AzureImageService()