"""
S3 Storage Service Unit Tests
"""

import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

from backend.infrastructure.storage.s3 import S3StorageService


class TestS3StorageService:
    @pytest.fixture
    def mock_boto3(self):
        with patch("boto3.client") as mock:
            yield mock

    @pytest.fixture
    def service(self, mock_boto3):
        with patch("backend.infrastructure.storage.s3.settings") as mock_settings:
            mock_settings.aws_s3_bucket_name = "test-bucket"
            mock_settings.aws_s3_region = "test-region"
            mock_settings.aws_access_key_id = "test-key"
            mock_settings.aws_secret_access_key = "test-secret"
            yield S3StorageService()

    @pytest.mark.asyncio
    async def test_save(self, service):
        service.s3_client.put_object = MagicMock()
        
        url = await service.save(b"data", "test.txt")
        
        assert "test-bucket" in url
        assert "test.txt" in url
        service.s3_client.put_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_get(self, service):
        mock_body = MagicMock()
        mock_body.read.return_value = b"data"
        service.s3_client.get_object.return_value = {"Body": mock_body}
        
        data = await service.get("test.txt")
        
        assert data == b"data"
        service.s3_client.get_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete(self, service):
        service.s3_client.delete_object.return_value = {}
        
        result = await service.delete("test.txt")
        
        assert result is True
        service.s3_client.delete_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_true(self, service):
        service.s3_client.head_object.return_value = {}
        
        exists = await service.exists("test.txt")
        
        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_false(self, service):
        error = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        service.s3_client.head_object.side_effect = error
        
        exists = await service.exists("test.txt")
        
        assert exists is False
