"""
Image processor for converting IMAGE: references to Azure URLs
"""

import re
import logging
import pandas as pd
from typing import Optional, Tuple
from azure_service import azure_service

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Process IMAGE: references and convert them to Azure URLs"""
    
    def __init__(self):
        self.azure_service = azure_service
    
    def process_text_for_azure(self, text: str, test_package_id: int) -> str:
        """
        Replace IMAGE: references with Azure URLs
        
        Args:
            text: Text containing IMAGE: references
            test_package_id: ID of the test package for Azure mapping
            
        Returns:
            Text with Azure URLs replacing IMAGE: references
        """
        if not text or pd.isna(text):
            return ""
        
        text = str(text)
        
        # Pattern to match IMAGE: references with or without square brackets
        # Examples: "IMAGE: filename.png" or "[IMAGE: filename.png]"
        image_pattern = r'\[?IMAGE:\s*([^\s\[\]]+\.(png|jpg|jpeg|gif|svg))\]?'
        
        def replace_with_azure_url(match):
            image_filename = match.group(1)
            
            # Generate Azure URL
            azure_url = self.azure_service.generate_image_url(test_package_id, image_filename)
            
            if azure_url:
                # Return as HTML img tag
                return f'<img src="{azure_url}" alt="{image_filename}" class="question-image" style="max-width: 100%; height: auto; margin: 10px 0;">'
            else:
                # Fallback if Azure URL generation fails
                logger.warning(f"Could not generate Azure URL for {image_filename} in package {test_package_id}")
                return f'<span class="missing-image" data-filename="{image_filename}">Image: {image_filename} (not found)</span>'
        
        # Replace all IMAGE: references with Azure URLs
        processed_text = re.sub(image_pattern, replace_with_azure_url, text, flags=re.IGNORECASE)
        
        return processed_text
    
    def has_image_references(self, text: str) -> bool:
        """Check if text contains IMAGE: references"""
        if not text or pd.isna(text):
            return False
        
        pattern = r'\[?IMAGE:\s*[^\s\[\]]+\.(png|jpg|jpeg|gif|svg)\]?'
        return bool(re.search(pattern, str(text), flags=re.IGNORECASE))
    
    def extract_image_filenames(self, text: str) -> list:
        """Extract all image filenames from IMAGE: references"""
        if not text or pd.isna(text):
            return []
        
        pattern = r'\[?IMAGE:\s*([^\s\[\]]+\.(png|jpg|jpeg|gif|svg))\]?'
        matches = re.findall(pattern, str(text), flags=re.IGNORECASE)
        
        # Return just the filenames (first capture group)
        return [match[0] for match in matches]
    
    def process_question_for_azure(self, question, test_package_id: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Process a question's text and explanation for Azure URLs
        
        Args:
            question: Question object
            test_package_id: Test package ID
            
        Returns:
            Tuple of (processed_question_text, processed_explanation)
        """
        processed_question_text = None
        processed_explanation = None
        
        # Process question text
        if self.has_image_references(question.question_text):
            processed_question_text = self.process_text_for_azure(
                question.question_text, 
                test_package_id
            )
        
        # Process explanation
        if question.overall_explanation and self.has_image_references(question.overall_explanation):
            processed_explanation = self.process_text_for_azure(
                question.overall_explanation, 
                test_package_id
            )
        
        return processed_question_text, processed_explanation
    
    def process_answer_option_for_azure(self, answer_option, test_package_id: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Process an answer option's text and explanation for Azure URLs
        
        Args:
            answer_option: AnswerOption object
            test_package_id: Test package ID
            
        Returns:
            Tuple of (processed_option_text, processed_explanation)
        """
        processed_option_text = None
        processed_explanation = None
        
        # Process option text
        if self.has_image_references(answer_option.option_text):
            processed_option_text = self.process_text_for_azure(
                answer_option.option_text, 
                test_package_id
            )
        
        # Process explanation
        if answer_option.explanation and self.has_image_references(answer_option.explanation):
            processed_explanation = self.process_text_for_azure(
                answer_option.explanation, 
                test_package_id
            )
        
        return processed_option_text, processed_explanation
    
    def get_display_text(self, original_text: str, processed_text: Optional[str]) -> str:
        """
        Get the text to display - processed version if available, otherwise original
        
        Args:
            original_text: Original text with IMAGE: references
            processed_text: Processed text with Azure URLs
            
        Returns:
            Text to display in templates
        """
        return processed_text if processed_text else original_text

# Global instance
image_processor = ImageProcessor()