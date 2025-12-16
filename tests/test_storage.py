"""Tests for storage abstraction layer."""

import pytest
import tempfile
from pathlib import Path

from app.storage.interface import (
    StorageBackend,
    FileStorageBackend,
    get_storage_backend,
    register_storage_backend,
    save_file,
    load_file,
    delete_file,
    file_exists,
    list_files,
)
from app.storage.local_storage import LocalStorage


class MockStorageBackend(StorageBackend):
    """Mock storage backend for testing."""

    def __init__(self):
        self.data = {}

    async def save(self, path: str, data: bytes | str, **kwargs):
        self.data[path] = data

    async def load(self, path: str, **kwargs) -> bytes | str:
        if path not in self.data:
            raise FileNotFoundError(f"Path {path} not found")
        return self.data[path]

    async def delete(self, path: str, **kwargs) -> bool:
        if path in self.data:
            del self.data[path]
            return True
        return False

    async def exists(self, path: str, **kwargs) -> bool:
        return path in self.data

    async def list(self, prefix: str = "", **kwargs) -> list[str]:
        if prefix:
            return [p for p in self.data.keys() if p.startswith(prefix)]
        return list(self.data.keys())

    async def copy(self, source: str, destination: str, **kwargs):
        if source in self.data:
            self.data[destination] = self.data[source]

    async def move(self, source: str, destination: str, **kwargs):
        if source in self.data:
            self.data[destination] = self.data[source]
            del self.data[source]


class TestStorageBackend:
    """Test storage backend interface."""

    @pytest.mark.asyncio
    async def test_save_and_load(self):
        """Test saving and loading data."""
        storage = MockStorageBackend()

        await storage.save("test/path", "test data")
        data = await storage.load("test/path")

        assert data == "test data"

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting data."""
        storage = MockStorageBackend()

        await storage.save("test/path", "test data")
        assert await storage.exists("test/path")

        deleted = await storage.delete("test/path")
        assert deleted is True
        assert not await storage.exists("test/path")

        # Delete non-existent file
        deleted = await storage.delete("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_list(self):
        """Test listing files."""
        storage = MockStorageBackend()

        await storage.save("file1.txt", "data1")
        await storage.save("file2.txt", "data2")
        await storage.save("dir/file3.txt", "data3")

        all_files = await storage.list()
        assert len(all_files) == 3

        dir_files = await storage.list(prefix="dir/")
        assert len(dir_files) == 1
        assert dir_files[0] == "dir/file3.txt"


class TestLocalStorage:
    """Test local storage implementation."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_save_and_load(self, temp_dir):
        """Test saving and loading files."""
        storage = LocalStorage(temp_dir)

        await storage.save("test/file.txt", "test content")

        # Load as string
        content = await storage.load("test/file.txt")
        assert content == "test content"

        # Load as bytes
        content_bytes = await storage.load("test/file.txt", binary=True)
        assert content_bytes == b"test content"

    @pytest.mark.asyncio
    async def test_exists(self, temp_dir):
        """Test file existence check."""
        storage = LocalStorage(temp_dir)

        assert not await storage.exists("test/file.txt")

        await storage.save("test/file.txt", "content")
        assert await storage.exists("test/file.txt")

    @pytest.mark.asyncio
    async def test_delete(self, temp_dir):
        """Test file deletion."""
        storage = LocalStorage(temp_dir)

        await storage.save("test/file.txt", "content")
        assert await storage.exists("test/file.txt")

        deleted = await storage.delete("test/file.txt")
        assert deleted is True
        assert not await storage.exists("test/file.txt")

    @pytest.mark.asyncio
    async def test_list(self, temp_dir):
        """Test file listing."""
        storage = LocalStorage(temp_dir)

        await storage.save("file1.txt", "content1")
        await storage.save("file2.txt", "content2")
        await storage.save("dir/file3.txt", "content3")

        files = await storage.list()
        assert len(files) == 3
        assert "file1.txt" in files
        assert "file2.txt" in files
        assert "dir/file3.txt" in files

    @pytest.mark.asyncio
    async def test_copy(self, temp_dir):
        """Test file copying."""
        storage = LocalStorage(temp_dir)

        await storage.save("source.txt", "original content")
        await storage.copy("source.txt", "destination.txt")

        assert await storage.exists("source.txt")
        assert await storage.exists("destination.txt")

        content = await storage.load("destination.txt")
        assert content == "original content"

    @pytest.mark.asyncio
    async def test_move(self, temp_dir):
        """Test file moving."""
        storage = LocalStorage(temp_dir)

        await storage.save("source.txt", "content")
        await storage.move("source.txt", "destination.txt")

        assert not await storage.exists("source.txt")
        assert await storage.exists("destination.txt")

        content = await storage.load("destination.txt")
        assert content == "content"

    @pytest.mark.asyncio
    async def test_get_size(self, temp_dir):
        """Test file size retrieval."""
        storage = LocalStorage(temp_dir)

        await storage.save("file.txt", "hello world")

        size = await storage.get_size("file.txt")
        assert size == 11  # len("hello world")

    @pytest.mark.asyncio
    async def test_ensure_dir(self, temp_dir):
        """Test directory creation."""
        storage = LocalStorage(temp_dir)

        await storage.ensure_dir("nested/directory")

        dir_path = temp_dir / "nested" / "directory"
        assert dir_path.exists()
        assert dir_path.is_dir()

    @pytest.mark.asyncio
    async def test_remove_dir(self, temp_dir):
        """Test directory removal."""
        storage = LocalStorage(temp_dir)

        # Create directory with files
        await storage.save("dir/file1.txt", "content1")
        await storage.save("dir/file2.txt", "content2")

        # Remove recursively
        removed = await storage.remove_dir("dir", recursive=True)
        assert removed is True

        dir_path = temp_dir / "dir"
        assert not dir_path.exists()


class TestStorageRegistry:
    """Test storage backend registry."""

    def test_register_storage_backend(self):
        """Test registering a storage backend."""
        register_storage_backend("mock", MockStorageBackend)

        backend = get_storage_backend("mock")
        assert isinstance(backend, MockStorageBackend)

    def test_get_unknown_backend(self):
        """Test error when getting unknown backend."""
        with pytest.raises(ValueError, match="Unknown storage backend"):
            get_storage_backend("unknown_backend")


class TestConvenienceFunctions:
    """Test convenience functions for storage operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_save_and_load_file(self, temp_dir):
        """Test save_file and load_file convenience functions."""
        # Save file
        await save_file("test.txt", "test content")

        # Load file
        content = await load_file("test.txt")
        assert content == "test content"

    @pytest.mark.asyncio
    async def test_delete_file(self, temp_dir):
        """Test delete_file convenience function."""
        await save_file("test.txt", "content")
        assert await file_exists("test.txt")

        deleted = await delete_file("test.txt")
        assert deleted is True
        assert not await file_exists("test.txt")

    @pytest.mark.asyncio
    async def test_list_files(self, temp_dir):
        """Test list_files convenience function."""
        await save_file("file1.txt", "content1")
        await save_file("file2.txt", "content2")

        files = await list_files()
        # Don't check total count (data directory may have existing files)
        # Just verify our files are present
        assert "file1.txt" in files
        assert "file2.txt" in files


if __name__ == "__main__":
    pytest.main([__file__])
