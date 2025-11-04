import os
import uuid
import boto3
import base64
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError
import mimetypes
from datetime import datetime

class S3StorageService:
    """
    Service for handling file uploads to S3
    """
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'emr-resc')
        self.s3_prefix = os.getenv('S3_FILE_PREFIX', 'agentx/files')
        
    def upload_file(self, file_content: bytes, filename: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a file to S3 and return file information
        
        Args:
            file_content: The file content as bytes
            filename: Original filename
            content_type: MIME type of the file
            
        Returns:
            Dict containing file information including S3 key, URL, etc.
        """
        try:
            # Generate unique filename
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            s3_key = f"{self.s3_prefix}/{datetime.now().strftime('%Y/%m/%d')}/{unique_filename}"
            
            # Determine content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(filename)
                if not content_type:
                    content_type = 'application/octet-stream'
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'original_filename': filename,
                    'upload_timestamp': datetime.now().isoformat()
                }
            )
            
            # Generate presigned URL for access
            file_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=3600 * 24 * 7  # 7 days
            )
            
            return {
                'file_id': unique_filename.split('.')[0],
                's3_key': s3_key,
                'original_filename': filename,
                'content_type': content_type,
                'file_size': len(file_content),
                'file_url': file_url,
                'upload_timestamp': datetime.now().isoformat()
            }
            
        except ClientError as e:
            raise Exception(f"Failed to upload file to S3: {str(e)}")
    
    def get_file(self, s3_key: str) -> bytes:
        """
        Download a file from S3
        
        Args:
            s3_key: S3 key of the file
            
        Returns:
            File content as bytes
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return response['Body'].read()
        except ClientError as e:
            raise Exception(f"Failed to download file from S3: {str(e)}")

    def get_encoded_file(self, s3_key: str) -> str:
        """
        Download a file from S3
        
        Args:
            s3_key: S3 key of the file
            
        Returns:
            File content as base64 encoded string
        """
        try:
            content = self.get_file(s3_key)
            return base64.b64encode(content).decode()
        except Exception as e:
            raise Exception(f"Failed to download file from S3: {str(e)}")

    def get_file_info(self, s3_key: str) -> Dict[str, Any]:
        """
        Get file metadata from S3
        
        Args:
            s3_key: S3 key of the file
            
        Returns:
            File metadata
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return {
                'content_type': response.get('ContentType'),
                'file_size': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError as e:
            raise Exception(f"Failed to get file info from S3: {str(e)}")
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3
        
        Args:
            s3_key: S3 key of the file
            
        Returns:
            True if successful
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            print(f"Failed to delete file from S3: {str(e)}")
            return False
