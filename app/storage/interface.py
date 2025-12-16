"""Storage interface abstraction for flexible backend selection.

This module defines the abstract base class for all storage backends,
enabling pluggable storage implementations (local filesystem, S3, etc.).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class StorageBackend(ABC):
    """Abstract base class for storage backends.

    All storage implementations (local, S3, etc.) must inherit from this class
    and implement the required methods.
    """

    @abstractmethod
    async def save(self, path: str, data: bytes | str, **kwargs) -> None:
        """Save data to storage.

        Args:
            path: Storage path/key
            data: Data to save (bytes or string)
            **kwargs: Additional backend-specific parameters
        """
        pass

    @abstractmethod
    async def load(self, path: str, **kwargs) -> bytes | str:
        """Load data from storage.

        Args:
            path: Storage path/key
            **kwargs: Additional backend-specific parameters

        Returns:
            Loaded data (bytes or string)
        """
        pass

    @abstractmethod
    async def delete(self, path: str, **kwargs) -> bool:
        """Delete data from storage.

        Args:
            path: Storage path/key
            **kwargs: Additional backend-specific parameters

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, path: str, **kwargs) -> bool:
        """Check if path exists in storage.

        Args:
            path: Storage path/key
            **kwargs: Additional backend-specific parameters

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    async def list(self, prefix: str = "", **kwargs) -> List[str]:
        """List all paths with optional prefix.

        Args:
            prefix: Path prefix to filter by
            **kwargs: Additional backend-specific parameters

        Returns:
            List of paths/keys
        """
        pass

    @abstractmethod
    async def copy(self, source: str, destination: str, **kwargs) -> None:
        """Copy data from source to destination.

        Args:
            source: Source path/key
            destination: Destination path/key
            **kwargs: Additional backend-specific parameters
        """
        pass

    @abstractmethod
    async def move(self, source: str, destination: str, **kwargs) -> None:
        """Move data from source to destination.

        Args:
            source: Source path/key
            destination: Destination path/key
            **kwargs: Additional backend-specific parameters
        """
        pass


class FileStorageBackend(StorageBackend):
    """Base class for file-based storage backends.

    Provides common file operations for local and cloud file systems.
    """

    def __init__(self, base_path: str | Path):
        """Initialize file storage backend.

        Args:
            base_path: Base directory/path
        """
        self.base_path = Path(base_path)

    def _normalize_path(self, path: str) -> Path:
        """Normalize storage path to filesystem path.

        Args:
            path: Storage path

        Returns:
            Normalized filesystem path
        """
        # Remove leading slash to make relative
        path = path.lstrip("/")
        return self.base_path / path

    async def save(self, path: str, data: bytes | str, **kwargs) -> None:
        """Save data to file."""
        file_path = self._normalize_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        mode = "wb" if isinstance(data, bytes) else "w"
        encoding = None if isinstance(data, bytes) else "utf-8"

        with open(file_path, mode, encoding=encoding) as f:
            f.write(data)

    async def load(self, path: str, **kwargs) -> bytes | str:
        """Load data from file."""
        file_path = self._normalize_path(path)

        mode = "rb" if kwargs.get("binary", False) else "r"
        encoding = None if kwargs.get("binary", False) else "utf-8"

        with open(file_path, mode, encoding=encoding) as f:
            return f.read()

    async def delete(self, path: str, **kwargs) -> bool:
        """Delete file."""
        file_path = self._normalize_path(path)

        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def exists(self, path: str, **kwargs) -> bool:
        """Check if file exists."""
        file_path = self._normalize_path(path)
        return file_path.exists()

    async def list(self, prefix: str = "", **kwargs) -> List[str]:
        """List files with prefix."""
        prefix_path = self._normalize_path(prefix) if prefix else self.base_path

        if not prefix_path.exists():
            return []

        paths = []
        if prefix_path.is_dir():
            for file_path in prefix_path.rglob("*"):
                if file_path.is_file():
                    # Return relative path from base
                    rel_path = file_path.relative_to(self.base_path)
                    paths.append(str(rel_path))
        else:
            # Single file
            if prefix_path.exists():
                rel_path = prefix_path.relative_to(self.base_path)
                paths.append(str(rel_path))

        return sorted(paths)

    async def copy(self, source: str, destination: str, **kwargs) -> None:
        """Copy file."""
        import shutil

        source_path = self._normalize_path(source)
        dest_path = self._normalize_path(destination)

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest_path)

    async def move(self, source: str, destination: str, **kwargs) -> None:
        """Move file."""
        import shutil

        source_path = self._normalize_path(source)
        dest_path = self._normalize_path(destination)

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(dest_path))


# Storage registry for backend selection
_storage_backends: Dict[str, type[StorageBackend]] = {}


def register_storage_backend(name: str, backend_class: type[StorageBackend]) -> None:
    """Register a storage backend class.

    Args:
        name: Backend name (e.g., 'local', 's3')
        backend_class: StorageBackend subclass
    """
    _storage_backends[name] = backend_class


def get_storage_backend(name: str, **kwargs) -> StorageBackend:
    """Get storage backend instance by name.

    Args:
        name: Backend name
        **kwargs: Backend initialization parameters

    Returns:
        StorageBackend instance

    Raises:
        ValueError: If backend not found
    """
    if name not in _storage_backends:
        raise ValueError(f"Unknown storage backend: {name}. Available: {list(_storage_backends.keys())}")

    backend_class = _storage_backends[name]
    return backend_class(**kwargs)


def get_storage() -> StorageBackend:
    """Get default storage backend from environment or config.

    Returns:
        Default StorageBackend instance
    """
    from app.core.config import get_settings

    settings = get_settings()
    backend_name = settings.storage_backend or "local"

    if backend_name == "local":
        from app.storage.local_storage import LocalStorage
        base_path = settings.data_dir or Path("data")
        return LocalStorage(base_path=base_path)
    else:
        # Custom backend
        return get_storage_backend(backend_name)


# Convenience functions for common operations
async def save_file(path: str, data: bytes | str, **kwargs) -> None:
    """Save file using default storage backend.

    Args:
        path: Storage path
        data: Data to save
        **kwargs: Additional parameters
    """
    storage = get_storage()
    await storage.save(path, data, **kwargs)


async def load_file(path: str, **kwargs) -> bytes | str:
    """Load file using default storage backend.

    Args:
        path: Storage path
        **kwargs: Additional parameters

    Returns:
        Loaded data
    """
    storage = get_storage()
    return await storage.load(path, **kwargs)


async def delete_file(path: str, **kwargs) -> bool:
    """Delete file using default storage backend.

    Args:
        path: Storage path
        **kwargs: Additional parameters

    Returns:
        True if deleted
    """
    storage = get_storage()
    return await storage.delete(path, **kwargs)


async def file_exists(path: str, **kwargs) -> bool:
    """Check if file exists using default storage backend.

    Args:
        path: Storage path
        **kwargs: Additional parameters

    Returns:
        True if exists
    """
    storage = get_storage()
    return await storage.exists(path, **kwargs)


async def list_files(prefix: str = "", **kwargs) -> List[str]:
    """List files using default storage backend.

    Args:
        prefix: Path prefix
        **kwargs: Additional parameters

    Returns:
        List of file paths
    """
    storage = get_storage()
    return await storage.list(prefix, **kwargs)
