"""Unit tests for File Service"""

import pytest
from io import BytesIO

from app.infrastructure.storage.file_service import FileService
from app.core.exceptions import AuthorizationException


@pytest.mark.unit
class TestFileService:
    def test_upload_file_success(self, mock_user_context, mock_s3_client):
        """Test successful file upload"""
        # Arrange
        service = FileService()
        service.s3_client = mock_s3_client
        file_data = BytesIO(b"test content")

        # Act
        result = service.upload_file(
            file_data=file_data,
            filename="test.txt",
            user_context=mock_user_context,
            category="reports",
        )

        # Assert
        assert result["filename"] == "test.txt"
        assert result["size"] == 1024
        assert "file_id" in result
        assert result["file_id"].startswith(mock_user_context.user_id)
        mock_s3_client.upload_file.assert_called_once()

    def test_download_file_with_permission(self, mock_user_context, mock_s3_client):
        """Test file download with valid permission"""
        # Arrange
        service = FileService()
        service.s3_client = mock_s3_client
        file_id = f"{mock_user_context.user_id}/reports/test.txt"

        # Act
        result = service.download_file(file_id=file_id, user_context=mock_user_context)

        # Assert
        assert result is not None
        mock_s3_client.download_file.assert_called_once_with(file_id)

    def test_download_file_without_permission(self, mock_user_context, mock_s3_client):
        """Test file download fails without permission"""
        # Arrange
        service = FileService()
        service.s3_client = mock_s3_client
        file_id = "another_user_789/reports/test.txt"

        # Act & Assert
        with pytest.raises(AuthorizationException):
            service.download_file(file_id=file_id, user_context=mock_user_context)

        mock_s3_client.download_file.assert_not_called()
