"""
S3-compatible object storage client.
This is CORE INFRASTRUCTURE - Do not modify.
"""

import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO, Dict, Any, List
from io import BytesIO
import structlog

from app.core.config import settings
from app.core.exceptions import StorageException

logger = structlog.get_logger()


class S3Client:
    """S3-compatible storage client with connection pooling"""

    def __init__(self):
        self.client = None
        self.bucket_name = settings.S3_BUCKET_NAME
        self._initialize_client()

    def _initialize_client(self):
        """Initialize S3 client"""
        try:
            self.client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
                region_name=settings.S3_REGION,
                config=boto3.session.Config(
                    signature_version="s3v4",
                    max_pool_connections=50,
                    retries={"max_attempts": 3, "mode": "adaptive"},
                ),
            )
            logger.info("S3 client initialized", endpoint=settings.S3_ENDPOINT_URL)
        except Exception as e:
            logger.error("Failed to initialize S3 client", error=str(e))
            raise StorageException(f"S3 initialization failed: {str(e)}")

    def upload_file(
        self,
        file_data: BinaryIO,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Upload file to S3"""
        try:
            extra_args: Dict[str, Any] = {}
            if content_type:
                extra_args["ContentType"] = content_type
            if metadata:
                extra_args["Metadata"] = metadata

            self.client.upload_fileobj(
                Fileobj=file_data,
                Bucket=self.bucket_name,
                Key=object_key,
                ExtraArgs=extra_args if extra_args else None,
            )

            head = self.client.head_object(Bucket=self.bucket_name, Key=object_key)

            logger.info("File uploaded", object_key=object_key, size=head["ContentLength"])

            return {
                "object_key": object_key,
                "size": head["ContentLength"],
                "etag": head["ETag"].strip("\""),
                "content_type": head.get("ContentType"),
                "url": f"{settings.S3_ENDPOINT_URL}/{self.bucket_name}/{object_key}",
            }
        except ClientError as e:
            logger.error("S3 upload failed", object_key=object_key, error=str(e))
            raise StorageException(
                f"Upload failed: {str(e)}", details={"object_key": object_key}
            )

    def download_file(self, object_key: str) -> BytesIO:
        """Download file from S3"""
        try:
            file_stream = BytesIO()
            self.client.download_fileobj(
                Bucket=self.bucket_name,
                Key=object_key,
                Fileobj=file_stream,
            )
            file_stream.seek(0)
            logger.info("File downloaded", object_key=object_key)
            return file_stream
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise StorageException(f"File not found: {object_key}")
            logger.error("S3 download failed", object_key=object_key, error=str(e))
            raise StorageException(f"Download failed: {str(e)}")

    def delete_file(self, object_key: str) -> bool:
        """Delete file from S3"""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_key)
            logger.info("File deleted", object_key=object_key)
            return True
        except ClientError as e:
            logger.error("S3 delete failed", object_key=object_key, error=str(e))
            raise StorageException(f"Delete failed: {str(e)}")

    def list_files(self, prefix: Optional[str] = None, max_keys: int = 1000) -> List[Dict]:
        """List files in bucket"""
        try:
            params: Dict[str, Any] = {"Bucket": self.bucket_name, "MaxKeys": max_keys}
            if prefix:
                params["Prefix"] = prefix

            response = self.client.list_objects_v2(**params)

            return [
                {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                    "etag": obj["ETag"].strip("\""),
                }
                for obj in response.get("Contents", [])
            ]
        except ClientError as e:
            logger.error("S3 list failed", prefix=prefix, error=str(e))
            raise StorageException(f"List failed: {str(e)}")

    def generate_presigned_url(
        self, object_key: str, expiration: int = 3600, operation: str = "get_object"
    ) -> str:
        """Generate presigned URL"""
        try:
            url = self.client.generate_presigned_url(
                ClientMethod=operation,
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expiration,
            )
            logger.info("Presigned URL generated", object_key=object_key)
            return url
        except ClientError as e:
            logger.error("Failed to generate presigned URL", error=str(e))
            raise StorageException(f"URL generation failed: {str(e)}")

    def file_exists(self, object_key: str) -> bool:
        """Check if file exists"""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise StorageException(f"Existence check failed: {str(e)}")


# Global shared instance
s3_client = S3Client()
