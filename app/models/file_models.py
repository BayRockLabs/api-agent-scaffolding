"""File-related models"""

from pydantic import Field
from typing import Optional, List
from app.models.base import BaseModel


class FileUploadResponse(BaseModel):
    """File upload response"""

    file_id: str
    filename: str
    size: int
    content_type: Optional[str] = None
    url: str
    uploaded_at: str


class FileInfo(BaseModel):
    """File information"""

    file_id: str
    filename: str
    size: int
    last_modified: str


class FileListResponse(BaseModel):
    """File list response"""

    files: List[FileInfo]
    total: int


class FileDownloadURLResponse(BaseModel):
    """Presigned URL response"""

    file_id: str
    url: str
    expires_in: int
