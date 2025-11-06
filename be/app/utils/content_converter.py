from typing import List, Dict, Any, Optional
from ..utils.s3_storage import S3StorageService
import os

class ContentConverter:
    """
    Utility class to convert files and text to Strands ContentBlocks
    """
    
    def __init__(self):
        self.s3_service = S3StorageService()
    
    def create_content_blocks(self, text_message: str, file_attachments: Optional[List[Dict[str, Any]]] = None, use_s3_reference: bool = False) -> List[Dict[str, Any]]:
        """
        Create ContentBlocks from text message and file attachments
        
        Args:
            text_message: The text message
            file_attachments: List of file attachment info from S3
            use_s3_reference: Whether to use S3 references instead of binary content
            
        Returns:
            List of ContentBlocks compatible with Strands agent
        """
        content_blocks = []
        
        # Add text content block
        if text_message:
            content_blocks.append({
                "text": text_message
            })
        
        # Add file content blocks
        if file_attachments:
            for file_info in file_attachments:
                if use_s3_reference:
                    content_block = self._create_s3_reference_content_block(file_info)
                else:
                    content_block = self._create_file_content_block(file_info)
                    if content_block.get("document"):
                        print(f"document content_block: name-{content_block.get("document").get("name")}")
                if content_block:
                    content_blocks.append(content_block)

        return content_blocks
    
    def _create_s3_reference_content_block(self, file_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a text ContentBlock with S3 reference information for a file attachment
        
        Args:
            file_info: File information from S3 upload
            
        Returns:
            ContentBlock dict with S3 reference as text content
        """
        try:
            content_type = file_info.get('content_type', '')
            s3_key = file_info.get('s3_key')
            s3_path = file_info.get('s3_path')
            original_filename = file_info.get('original_filename', '')

            print(f"content_type: {content_type}, _create_s3_reference_content_block: {s3_key}")
            
            if not s3_key:
                return None
            
            # Determine file type based on MIME type
            if content_type.startswith('image/'):
                file_type = '_image'
                format_map = {
                    'image/png': 'png',
                    'image/jpeg': 'jpeg',
                    'image/jpg': 'jpeg',
                    'image/gif': 'gif',
                    'image/webp': 'webp'
                }
                file_format = format_map.get(content_type.lower(), 'jpeg')
            elif content_type.startswith('video/'):
                file_type = '_video'
                format_map = {
                    'video/mp4': 'mp4',
                    'video/mpeg': 'mpeg',
                    'video/quicktime': 'mov',
                    'video/x-msvideo': 'avi',
                    'video/webm': 'webm',
                    'video/x-flv': 'flv',
                    'video/x-ms-wmv': 'wmv'
                }
                file_format = format_map.get(content_type.lower(), 'mp4')
            elif self._is_document_type(content_type, original_filename):
                file_type = '_document'
                format_map = {
                    'application/pdf': 'pdf',
                    'text/csv': 'csv',
                    'application/msword': 'doc',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
                    'application/vnd.ms-excel': 'xls',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
                    'text/html': 'html',
                    'text/plain': 'txt',
                    'text/markdown': 'md'
                }
                
                # Try to determine format from content type first
                file_format = format_map.get(content_type.lower())
                
                # If not found, try to determine from file extension
                if not file_format:
                    _, ext = os.path.splitext(original_filename.lower())
                    ext_map = {
                        '.pdf': 'pdf',
                        '.csv': 'csv',
                        '.doc': 'doc',
                        '.docx': 'docx',
                        '.xls': 'xls',
                        '.xlsx': 'xlsx',
                        '.html': 'html',
                        '.htm': 'html',
                        '.txt': 'txt',
                        '.md': 'md',
                        '.markdown': 'md'
                    }
                    file_format = ext_map.get(ext, 'txt')
            else:
                # For unsupported file types, create a generic text description
                return {
                    "text": f"[File attachment: {original_filename} ({content_type})]"
                }
            
            # Create the S3 reference structure as JSON text
            s3_reference = {
                '_filename': original_filename,
                file_type: {
                    '_format': file_format,
                    '_source_path': s3_path
                }
            }
            
            import json
            return {
                "text": json.dumps(s3_reference)
            }
                
        except Exception as e:
            print(f"Error creating S3 reference content block for file {file_info}: {str(e)}")
            return {
                "text": f"[Error processing file: {file_info.get('original_filename', 'unknown')}]"
            }
    
    def _create_file_content_block(self, file_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a ContentBlock for a file attachment
        
        Args:
            file_info: File information from S3 upload
            
        Returns:
            ContentBlock dict or None if file type not supported
        """
        try:
            content_type = file_info.get('content_type', '')
            s3_key = file_info.get('s3_key')
            original_filename = file_info.get('original_filename', '')

            print(f"content_type: {content_type}, _create_file_content_block: {s3_key}")
            
            if not s3_key:
                return None
            
            # Download file content from S3
            file_content = self.s3_service.get_file(s3_key)
            
            # Determine content block type based on MIME type
            if content_type.startswith('image/'):
                return self._create_image_content_block(file_content, content_type)
            elif content_type.startswith('video/'):
                return self._create_video_content_block(file_content, content_type)
            elif self._is_document_type(content_type, original_filename):
                return self._create_document_content_block(file_content, content_type, original_filename)
            else:
                # For unsupported file types, create a text description
                return {
                    "text": f"[File attachment: {original_filename} ({content_type}, {len(file_content)} bytes)]"
                }
                
        except Exception as e:
            print(f"Error creating content block for file {file_info}: {str(e)}")
            return {
                "text": f"[Error loading file: {file_info.get('original_filename', 'unknown')}]"
            }
    
    def _create_image_content_block(self, file_content: bytes, content_type: str) -> Dict[str, Any]:
        """Create image content block"""
        # Map content type to supported formats
        format_map = {
            'image/png': 'png',
            'image/jpeg': 'jpeg',
            'image/jpg': 'jpeg',
            'image/gif': 'gif',
            'image/webp': 'webp'
        }
        
        image_format = format_map.get(content_type.lower(), 'jpeg')
        
        return {
            "image": {
                "format": image_format,
                "source": {
                    "bytes": file_content
                }
            }
        }
    
    def _create_video_content_block(self, file_content: bytes, content_type: str) -> Dict[str, Any]:
        """Create video content block"""
        # Map content type to supported formats
        format_map = {
            'video/mp4': 'mp4',
            'video/mpeg': 'mpeg',
            'video/quicktime': 'mov',
            'video/x-msvideo': 'avi',
            'video/webm': 'webm',
            'video/x-flv': 'flv',
            'video/x-ms-wmv': 'wmv'
        }
        
        video_format = format_map.get(content_type.lower(), 'mp4')
        
        return {
            "video": {
                "format": video_format,
                "source": {
                    "bytes": file_content
                }
            }
        }
    
    def _create_document_content_block(self, file_content: bytes, content_type: str, filename: str) -> Dict[str, Any]:
        """Create document content block"""
        # Map content type and extension to supported formats
        format_map = {
            'application/pdf': 'pdf',
            'text/csv': 'csv',
            'application/msword': 'doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/vnd.ms-excel': 'xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
            'text/html': 'html',
            'text/plain': 'txt',
            'text/markdown': 'md'
        }
        
        # Try to determine format from content type first
        doc_format = format_map.get(content_type.lower())
        
        # If not found, try to determine from file extension
        if not doc_format:
            _, ext = os.path.splitext(filename.lower())
            ext_map = {
                '.pdf': 'pdf',
                '.csv': 'csv',
                '.doc': 'doc',
                '.docx': 'docx',
                '.xls': 'xls',
                '.xlsx': 'xlsx',
                '.html': 'html',
                '.htm': 'html',
                '.txt': 'txt',
                '.md': 'md',
                '.markdown': 'md'
            }
            doc_format = ext_map.get(ext, 'txt')

        dot_index = filename.rindex('.')
        if dot_index:
            filename = filename[0:dot_index]
        filename = filename.replace('_', '-').replace('.', '-').lower()

        return {
            "document": {
                "format": doc_format,
                "name": filename,
                "source": {
                    "bytes": file_content
                }
            }
        }
    
    def _is_document_type(self, content_type: str, filename: str) -> bool:
        """Check if the file is a supported document type"""
        document_types = [
            'application/pdf',
            'text/csv',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/html',
            'text/plain',
            'text/markdown'
        ]
        
        if content_type.lower() in document_types:
            return True
        
        # Check by file extension
        _, ext = os.path.splitext(filename.lower())
        document_extensions = ['.pdf', '.csv', '.doc', '.docx', '.xls', '.xlsx', '.html', '.htm', '.txt', '.md', '.markdown']
        return ext in document_extensions
