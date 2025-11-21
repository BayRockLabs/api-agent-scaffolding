"""
File management REST API endpoints.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import structlog

from app.core.dependencies import UserContextDep
from app.infrastructure.storage.file_service import file_service
from app.models.file_models import (
    FileUploadResponse,
    FileListResponse,
    FileDownloadURLResponse,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    user: UserContextDep,
    file: UploadFile = File(...),
    category: Optional[str] = Query(None, description="File category"),
):
    """
    Upload file to S3-compatible storage.

    - User-scoped (stored under user_id)
    - Optional categorization
    - Returns file metadata and URL
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    try:
        result = file_service.upload_file(
            file_data=file.file,
            filename=file.filename,
            user_context=user,
            category=category,
            metadata={"content_type": file.content_type},
        )

        return FileUploadResponse(**result)

    except Exception as e:
        logger.error("File upload failed", error=str(e), user_id=user.user_id)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/download/{file_id:path}")
async def download_file(
    file_id: str,
    user: UserContextDep,
):
    """
    Download file from storage.

    - User-scoped (can only download own files)
    - Returns file as streaming response
    """
    try:
        file_stream = file_service.download_file(
            file_id=file_id,
            user_context=user,
        )

        filename = file_id.split("/")[-1]

        return StreamingResponse(
            file_stream,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        logger.error("File download failed", error=str(e), file_id=file_id)
        msg = str(e)
        status_code = (
            404
            if "not found" in msg.lower()
            else 403
            if "permission" in msg.lower()
            else 500
        )
        raise HTTPException(status_code=status_code, detail=msg)


@router.get("/list", response_model=FileListResponse)
async def list_files(
    user: UserContextDep,
    category: Optional[str] = Query(None),
):
    """
    List user's files.

    - User-scoped (only shows user's files)
    - Optional category filter
    """
    try:
        files = file_service.list_user_files(
            user_context=user,
            category=category,
        )

        return FileListResponse(files=files, total=len(files))

    except Exception as e:
        logger.error("File listing failed", error=str(e), user_id=user.user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{file_id:path}")
async def delete_file(
    file_id: str,
    user: UserContextDep,
):
    """
    Delete a file.

    - User-scoped (can only delete own files)
    """
    try:
        file_service.delete_file(file_id=file_id, user_context=user)
        return {"message": "File deleted successfully", "file_id": file_id}

    except Exception as e:
        logger.error("File deletion failed", error=str(e), file_id=file_id)
        msg = str(e)
        status_code = 403 if "permission" in msg.lower() else 500
        raise HTTPException(status_code=status_code, detail=msg)


@router.get("/url/{file_id:path}", response_model=FileDownloadURLResponse)
async def generate_download_url(
    file_id: str,
    user: UserContextDep,
    expiration: int = Query(3600, description="URL expiration in seconds"),
):
    """
    Generate temporary download URL.

    - User-scoped
    - URL expires after specified time
    """
    try:
        url = file_service.generate_download_url(
            file_id=file_id,
            user_context=user,
            expiration=expiration,
        )

        return FileDownloadURLResponse(
            file_id=file_id,
            url=url,
            expires_in=expiration,
        )

    except Exception as e:
        logger.error("URL generation failed", error=str(e), file_id=file_id)
        raise HTTPException(status_code=500, detail=str(e))
