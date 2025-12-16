"""Local filesystem storage backend implementation.

This module provides a concrete implementation of StorageBackend for local filesystem,
enabling easy switching between local and cloud storage backends.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.storage.interface import FileStorageBackend


class LocalStorage(FileStorageBackend):
    """Local filesystem storage backend.

    This backend stores files on the local filesystem, making it easy to:
    - Switch between local and cloud storage
    - Support multi-node deployments with shared storage
    - Maintain backward compatibility with existing code
    """

    def __init__(self, base_path: str | Path):
        """Initialize local storage backend.

        Args:
            base_path: Base directory for all stored files
        """
        super().__init__(base_path=base_path)

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

        print(f"📁 Local storage initialized:")
        print(f"   Base path: {self.base_path.absolute()}")

    async def save(self, path: str, data: bytes | str, **kwargs) -> None:
        """Save data to local filesystem.

        Args:
            path: Storage path (relative to base_path)
            data: Data to save (bytes or string)
            **kwargs: Additional parameters (encoding, mode, etc.)
        """
        file_path = self._normalize_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine write mode
        if isinstance(data, bytes):
            mode = "wb"
            encoding = None
        else:
            mode = "w"
            encoding = kwargs.get("encoding", "utf-8")

        # Write file atomically (write to temp then rename)
        import tempfile
        import shutil

        with tempfile.NamedTemporaryFile(
            mode=mode,
            encoding=encoding,
            dir=file_path.parent,
            delete=False
        ) as temp_file:
            temp_path = temp_file.name
            temp_file.write(data)

        # Atomically replace existing file
        shutil.move(temp_path, file_path)

    async def load(self, path: str, **kwargs) -> bytes | str:
        """Load data from local filesystem.

        Args:
            path: Storage path (relative to base_path)
            **kwargs: Additional parameters (binary, encoding, etc.)

        Returns:
            Loaded data (bytes or string)

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self._normalize_path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine read mode
        binary = kwargs.get("binary", False)
        encoding = kwargs.get("encoding", "utf-8") if not binary else None

        mode = "rb" if binary else "r"

        with open(file_path, mode, encoding=encoding) as f:
            return f.read()

    async def delete(self, path: str, **kwargs) -> bool:
        """Delete file from local filesystem.

        Args:
            path: Storage path (relative to base_path)
            **kwargs: Additional parameters

        Returns:
            True if file was deleted, False if not found
        """
        file_path = self._normalize_path(path)

        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def exists(self, path: str, **kwargs) -> bool:
        """Check if file exists in local filesystem.

        Args:
            path: Storage path (relative to base_path)
            **kwargs: Additional parameters

        Returns:
            True if file exists, False otherwise
        """
        file_path = self._normalize_path(path)
        return file_path.exists()

    async def list(self, prefix: str = "", **kwargs) -> List[str]:
        """List files in local filesystem with optional prefix.

        Args:
            prefix: Path prefix to filter by (relative to base_path)
            **kwargs: Additional parameters (recursive, pattern, etc.)

        Returns:
            List of file paths (relative to base_path)
        """
        recursive = kwargs.get("recursive", True)
        pattern = kwargs.get("pattern", "*")

        prefix_path = self._normalize_path(prefix) if prefix else self.base_path

        if not prefix_path.exists():
            return []

        paths = []

        if recursive:
            # Search recursively
            for file_path in prefix_path.rglob(pattern):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.base_path)
                    paths.append(str(rel_path))
        else:
            # Search only in directory
            if prefix_path.is_dir():
                for file_path in prefix_path.glob(pattern):
                    if file_path.is_file():
                        rel_path = file_path.relative_to(self.base_path)
                        paths.append(str(rel_path))

        return sorted(paths)

    async def copy(self, source: str, destination: str, **kwargs) -> None:
        """Copy file within local filesystem.

        Args:
            source: Source path (relative to base_path)
            destination: Destination path (relative to base_path)
            **kwargs: Additional parameters
        """
        import shutil

        source_path = self._normalize_path(source)
        dest_path = self._normalize_path(destination)

        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest_path)

    async def move(self, source: str, destination: str, **kwargs) -> None:
        """Move file within local filesystem.

        Args:
            source: Source path (relative to base_path)
            destination: Destination path (relative to base_path)
            **kwargs: Additional parameters
        """
        import shutil

        source_path = self._normalize_path(source)
        dest_path = self._normalize_path(destination)

        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(dest_path))

    async def get_size(self, path: str) -> int:
        """Get file size in bytes.

        Args:
            path: Storage path (relative to base_path)

        Returns:
            File size in bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self._normalize_path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return file_path.stat().st_size

    async def get_mtime(self, path: str) -> float:
        """Get file modification time (timestamp).

        Args:
            path: Storage path (relative to base_path)

        Returns:
            Modification time as timestamp

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self._normalize_path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return file_path.stat().st_mtime

    async def ensure_dir(self, path: str) -> None:
        """Ensure directory exists.

        Args:
            path: Directory path (relative to base_path)
        """
        dir_path = self._normalize_path(path)
        dir_path.mkdir(parents=True, exist_ok=True)

    async def remove_dir(self, path: str, recursive: bool = True) -> bool:
        """Remove directory.

        Args:
            path: Directory path (relative to base_path)
            recursive: Remove recursively if True

        Returns:
            True if directory was removed
        """
        dir_path = self._normalize_path(path)

        if not dir_path.exists():
            return False

        import shutil
        if recursive:
            shutil.rmtree(dir_path)
        else:
            dir_path.rmdir()

        return True


# Register local storage backend
from app.storage.interface import register_storage_backend
register_storage_backend("local", LocalStorage)
