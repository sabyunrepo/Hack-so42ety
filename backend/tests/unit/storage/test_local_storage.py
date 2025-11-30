"""
Local Storage Service Unit Tests
"""

import pytest
import os
import shutil
from pathlib import Path
from backend.infrastructure.storage.local import LocalStorageService

TEST_STORAGE_PATH = "test_data/storage"

class TestLocalStorageService:
    @pytest.fixture
    def service(self):
        # Setup
        service = LocalStorageService(base_path=TEST_STORAGE_PATH, base_url="http://test/static")
        yield service
        # Teardown
        if os.path.exists(TEST_STORAGE_PATH):
            shutil.rmtree(TEST_STORAGE_PATH)

    @pytest.mark.asyncio
    async def test_save_and_get(self, service):
        file_data = b"test content"
        path = "test_file.txt"
        
        url = await service.save(file_data, path)
        
        assert url == "http://test/static/test_file.txt"
        assert await service.exists(path)
        
        content = await service.get(path)
        assert content == file_data

    @pytest.mark.asyncio
    async def test_save_nested_path(self, service):
        file_data = b"nested content"
        path = "folder/nested.txt"
        
        url = await service.save(file_data, path)
        
        assert url == "http://test/static/folder/nested.txt"
        assert await service.exists(path)

    @pytest.mark.asyncio
    async def test_delete(self, service):
        file_data = b"to delete"
        path = "delete_me.txt"
        await service.save(file_data, path)
        
        assert await service.exists(path)
        
        result = await service.delete(path)
        assert result is True
        assert not await service.exists(path)

    @pytest.mark.asyncio
    async def test_get_not_found(self, service):
        with pytest.raises(FileNotFoundError):
            await service.get("non_existent.txt")
