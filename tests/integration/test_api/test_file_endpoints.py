"""Integration tests for File API endpoints"""

import pytest
from io import BytesIO
from fastapi import status


@pytest.mark.integration
class TestFileEndpoints:
    @pytest.mark.asyncio
    async def test_upload_file_endpoint(self, authenticated_client):
        """Test file upload via API"""
        # Arrange
        file_content = b"Test file content"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

        # Act
        response = await authenticated_client.post(
            "/api/v1/files/upload",
            files=files,
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "file_id" in data
        assert data["filename"] == "test.txt"
        assert data["size"] > 0

    @pytest.mark.asyncio
    async def test_list_files_endpoint(self, authenticated_client):
        """Test listing files via API"""
        # Act
        response = await authenticated_client.get("/api/v1/files/list")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "files" in data
        assert "total" in data
        assert isinstance(data["files"], list)

    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client):
        """Test health check endpoint"""
        # Act
        response = await async_client.get("/api/v1/health")

        # Assert
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]
        data = response.json()
        assert "status" in data
        assert "version" in data
