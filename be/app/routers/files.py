from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List
from ..utils.s3_storage import S3StorageService
import io
import logging
import urllib.parse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/files",
    tags=["files"],
    responses={404: {"description": "Not found"}}
)

s3_service = S3StorageService()

@router.post("/upload")
async def upload_files(request: Request, files: List[UploadFile] = File(...)) -> JSONResponse:
    """
    Upload multiple files to S3 storage
    
    Args:
        files: List of uploaded files
        
    Returns:
        JSON response with file information
    """
    try:
        # Get current user from request state (set by AuthMiddleware)
        current_user = getattr(request.state, 'current_user', None)
        user_id = current_user.get('user_id', 'anonymous') if current_user else 'anonymous'
        
        uploaded_files = []
        
        for file in files:
            # Read file content
            file_content = await file.read()
            
            # Validate file size (max 50MB)
            if len(file_content) > 50 * 1024 * 1024:
                raise HTTPException(status_code=413, detail=f"File {file.filename} is too large. Maximum size is 50MB.")
            
            # Upload to S3
            file_info = s3_service.upload_file(
                file_content=file_content,
                filename=file.filename,
                content_type=file.content_type
            )
            
            # Add user info
            file_info['user_id'] = user_id
            uploaded_files.append(file_info)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Successfully uploaded {len(uploaded_files)} file(s)",
                "files": uploaded_files
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload files: {str(e)}")

@router.get("/download/{s3_key:path}")
async def download_file(s3_key: str, request: Request):
    """
    Download a file by S3 key.
    :param s3_key: The S3 key of the file to download.
    :return: The file content as a streaming response.
    """
    try:
        # Get current user from request state (set by AuthMiddleware)
        # current_user = getattr(request.state, 'current_user', None)
        # user_id = current_user.get('user_id', '') if current_user else ''
        
        # URL decode the s3_key to handle encoded path separators
        decoded_s3_key = urllib.parse.unquote(s3_key)
        
        # Download file from S3
        file_content = s3_service.download_file(decoded_s3_key)
        
        # Extract filename from decoded s3_key (last part after /)
        filename = decoded_s3_key.split('/')[-1] if '/' in decoded_s3_key else decoded_s3_key
        
        # Determine content type based on file extension
        content_type = "application/octet-stream"
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            ext = filename.split('.')[-1].lower()
            content_type = f"image/{ext if ext != 'jpg' else 'jpeg'}"
        elif filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
            ext = filename.split('.')[-1].lower()
            content_type = f"video/{ext}"
        elif filename.lower().endswith('.pdf'):
            content_type = "application/pdf"
        elif filename.lower().endswith(('.txt', '.md')):
            content_type = "text/plain"
        elif filename.lower().endswith(('.doc', '.docx')):
            content_type = "application/msword"
        elif filename.lower().endswith(('.xls', '.xlsx')):
            content_type = "application/vnd.ms-excel"
        elif filename.lower().endswith('.csv'):
            content_type = "text/csv"
        elif filename.lower().endswith('.html'):
            content_type = "text/html"
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Error downloading file {s3_key}: {str(e)}")
        raise HTTPException(status_code=404, detail="File not found")

@router.post("/download")
async def download_file_post(request: Request):
    """
    Download a file by S3 key using POST request.
    Request body should contain: {"s3_key": "path/to/file"}
    :return: The file content as a streaming response.
    """
    try:
        # Get current user from request state (set by AuthMiddleware)
        current_user = getattr(request.state, 'current_user', None)
        user_id = current_user.get('user_id', '') if current_user else ''
        
        # Parse request body to get s3_key
        body = await request.json()
        s3_key = body.get('s3_key')
        
        if not s3_key:
            raise HTTPException(status_code=400, detail="s3_key is required")
        
        # Download file from S3 (no need to decode since it's from JSON body)
        file_content = s3_service.get_file(s3_key)
        
        # Extract filename from s3_key (last part after /)
        filename = s3_key.split('/')[-1] if '/' in s3_key else s3_key
        
        # Determine content type based on file extension
        content_type = "application/octet-stream"
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            ext = filename.split('.')[-1].lower()
            content_type = f"image/{ext if ext != 'jpg' else 'jpeg'}"
        elif filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
            ext = filename.split('.')[-1].lower()
            content_type = f"video/{ext}"
        elif filename.lower().endswith('.pdf'):
            content_type = "application/pdf"
        elif filename.lower().endswith(('.txt', '.md')):
            content_type = "text/plain"
        elif filename.lower().endswith(('.doc', '.docx')):
            content_type = "application/msword"
        elif filename.lower().endswith(('.xls', '.xlsx')):
            content_type = "application/vnd.ms-excel"
        elif filename.lower().endswith('.csv'):
            content_type = "text/csv"
        elif filename.lower().endswith('.html'):
            content_type = "text/html"
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=404, detail="File not found")

@router.get("/info/{file_id}")
async def get_file_info(file_id: str) -> JSONResponse:
    """
    Get file information by file ID
    
    Args:
        file_id: The file ID
        
    Returns:
        File information
    """
    try:
        # Note: In a real implementation, you'd need to store file_id -> s3_key mapping
        # For now, we'll assume the s3_key can be reconstructed or stored elsewhere
        raise HTTPException(status_code=501, detail="File info retrieval not implemented yet")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file info: {str(e)}")

@router.delete("/{file_id}")
async def delete_file(file_id: str, request: Request) -> JSONResponse:
    """
    Delete a file by file ID
    
    Args:
        file_id: The file ID
        
    Returns:
        Success message
    """
    try:
        # Get current user from request state
        current_user = getattr(request.state, 'current_user', None)
        user_id = current_user.get('user_id', '') if current_user else ''
        
        # Note: In a real implementation, you'd need to:
        # 1. Verify the user owns the file
        # 2. Get the s3_key from file_id
        # 3. Delete from S3
        raise HTTPException(status_code=501, detail="File deletion not implemented yet")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
