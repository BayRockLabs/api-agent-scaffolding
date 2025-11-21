"""
File management service - usable by REST APIs, agents, and tools.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from typing import Optional, BinaryIO, Dict, List
from datetime import datetime
import uuid
import mimetypes
import structlog

from app.infrastructure.storage.s3_client import s3_client
from app.core.auth import UserContext
from app.core.exceptions import StorageException, AuthorizationException

logger = structlog.get_logger()


class FileService:
    """
    File operations service - usable internally by any component.
    Provides user-scoped file management.
    """

    def __init__(self):
        self.s3_client = s3_client

    def _generate_object_key(
        self, user_id: str, filename: str, category: Optional[str] = None
    ) -> str:
        """Generate unique S3 object key: {user_id}/{category}/{uuid}_{filename}"""
        file_uuid = uuid.uuid4().hex[:8]
        safe_filename = filename.replace(" ", "_").replace("/", "_")

        if category:
            return f"{user_id}/{category}/{file_uuid}_{safe_filename}"
        return f"{user_id}/{file_uuid}_{safe_filename}"

    def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        user_context: UserContext,
        category: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Upload file with user scoping"""
        object_key = self._generate_object_key(user_context.user_id, filename, category)

        content_type, _ = mimetypes.guess_type(filename)

        file_metadata: Dict[str, str] = {
            "user_id": user_context.user_id,
            "user_email": user_context.email,
            "original_filename": filename,
            "uploaded_at": datetime.utcnow().isoformat(),
        }
        if metadata:
            file_metadata.update(metadata)

        result = self.s3_client.upload_file(
            file_data=file_data,
            object_key=object_key,
            content_type=content_type,
            metadata=file_metadata,
        )

        logger.info("File uploaded", user_id=user_context.user_id, filename=filename)

        return {
            "file_id": object_key,
            "filename": filename,
            "size": result["size"],
            "content_type": result.get("content_type"),
            "url": result["url"],
            "uploaded_at": datetime.utcnow().isoformat(),
        }

    def download_file(self, file_id: str, user_context: UserContext):
        """Download file with permission check"""
        # Validate user has access
        if not file_id.startswith(user_context.user_id + "/"):
            logger.warning(
                "Unauthorized file access", user_id=user_context.user_id, file_id=file_id
            )
            raise AuthorizationException("You don't have permission to access this file")

        file_stream = self.s3_client.download_file(file_id)
        logger.info("File downloaded", user_id=user_context.user_id, file_id=file_id)
        return file_stream

    def list_user_files(
        self, user_context: UserContext, category: Optional[str] = None
    ) -> List[Dict]:
        """List files for a user"""
        prefix = f"{user_context.user_id}/"
        if category:
            prefix += f"{category}/"

        files = self.s3_client.list_files(prefix=prefix)

        return [
            {
                "file_id": f["key"],
                "filename": f["key"].split("/")[-1],
                "size": f["size"],
                "last_modified": f["last_modified"],
            }
            for f in files
        ]

    def delete_file(self, file_id: str, user_context: UserContext) -> bool:
        """Delete file with permission check"""
        if not file_id.startswith(user_context.user_id + "/"):
            raise AuthorizationException("You don't have permission to delete this file")

        result = self.s3_client.delete_file(file_id)
        logger.info("File deleted", user_id=user_context.user_id, file_id=file_id)
        return result

    def generate_download_url(
        self, file_id: str, user_context: UserContext, expiration: int = 3600
    ) -> str:
        """Generate temporary download URL"""
        if not file_id.startswith(user_context.user_id + "/"):
            raise AuthorizationException("You don't have permission to access this file")

        return self.s3_client.generate_presigned_url(
            object_key=file_id, expiration=expiration, operation="get_object"
        )


# Global shared instance
file_service = FileService()
