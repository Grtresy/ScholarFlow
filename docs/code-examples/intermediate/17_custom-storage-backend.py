#!/usr/bin/env python3
"""
高级代码示例17: 自定义存储后端
=================================

本示例展示如何构建一个功能完整的自定义存储后端系统，
用于ScholarFlow中的数据持久化管理。

功能特性:
- 多存储后端支持
- 读写分离
- 数据分片
- 缓存层
- 数据压缩
- 备份与恢复
- 分布式存储
- 性能监控

作者: Claude Code
版本: 1.0
"""

import asyncio
import logging
from typing import (
    TypedDict, List, Optional, Dict, Any, Callable,
    Awaitable, Union
)
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import sqlite3
import aiosqlite
import pickle
import zlib
import hashlib
from pathlib import Path
from collections import defaultdict, deque
import uuid
import shutil
from abc import ABC, abstractmethod

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class StorageType(Enum):
    """存储类型"""
    LOCAL = "local"
    SQLITE = "sqlite"
    MEMORY = "memory"
    S3 = "s3"
    DISTRIBUTED = "distributed"


class DataFormat(Enum):
    """数据格式"""
    JSON = "json"
    PICKLE = "pickle"
    BINARY = "binary"
    COMPRESSED = "compressed"


@dataclass
class StorageConfig:
    """存储配置"""
    storage_type: StorageType
    connection_string: str
    max_connections: int = 10
    timeout: float = 30.0
    compression: bool = False
    encryption: bool = False
    backup_enabled: bool = True
    cache_enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StorageItem:
    """存储项"""
    key: str
    value: Any
    format: DataFormat
    size: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StorageMetrics:
    """存储指标"""
    reads: int = 0
    writes: int = 0
    deletes: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_latency: float = 0.0
    total_size: int = 0
    item_count: int = 0


# ============================================================================
# 2. 存储后端接口
# ============================================================================

class StorageBackend(ABC):
    """存储后端基类"""

    @abstractmethod
    async def put(self, item: StorageItem) -> bool:
        """存储数据"""
        pass

    @abstractmethod
    async def get(self, key: str) -> Optional[StorageItem]:
        """获取数据"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除数据"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查是否存在"""
        pass

    @abstractmethod
    async def list(self, prefix: str = "") -> List[str]:
        """列出键"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """清空存储"""
        pass


# ============================================================================
# 3. 本地文件存储后端
# ============================================================================

class LocalFileStorageBackend(StorageBackend):
    """本地文件存储后端"""

    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / ".index.json"
        self.index: Dict[str, Dict[str, Any]] = self._load_index()

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """加载索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_index(self):
        """保存索引"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2, default=str)

    def _get_file_path(self, key: str) -> Path:
        """获取文件路径"""
        # 使用哈希避免文件名冲突
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.storage_dir / f"{hash_key}.dat"

    async def put(self, item: StorageItem) -> bool:
        """存储数据"""
        try:
            file_path = self._get_file_path(item.key)

            # 序列化数据
            if item.format == DataFormat.JSON:
                data = json.dumps(item.value, default=str).encode('utf-8')
            elif item.format == DataFormat.PICKLE:
                data = pickle.dumps(item.value)
            else:
                data = item.value if isinstance(item.value, bytes) else str(item.value).encode()

            # 压缩
            if item.metadata.get("compressed"):
                data = zlib.compress(data)

            # 写入文件
            with open(file_path, 'wb') as f:
                f.write(data)

            # 更新索引
            self.index[item.key] = {
                "file": str(file_path),
                "format": item.format.value,
                "size": len(data),
                "created_at": item.created_at.isoformat(),
                "metadata": item.metadata
            }

            self._save_index()
            return True

        except Exception as e:
            logger.error(f"Failed to put item {item.key}: {e}")
            return False

    async def get(self, key: str) -> Optional[StorageItem]:
        """获取数据"""
        try:
            if key not in self.index:
                return None

            index_entry = self.index[key]
            file_path = Path(index_entry["file"])

            if not file_path.exists():
                return None

            # 读取文件
            with open(file_path, 'rb') as f:
                data = f.read()

            # 解压缩
            if index_entry.get("metadata", {}).get("compressed"):
                data = zlib.decompress(data)

            # 反序列化
            if index_entry["format"] == "json":
                value = json.loads(data.decode('utf-8'))
            elif index_entry["format"] == "pickle":
                value = pickle.loads(data)
            else:
                value = data

            return StorageItem(
                key=key,
                value=value,
                format=DataFormat(index_entry["format"]),
                size=index_entry["size"],
                created_at=datetime.fromisoformat(index_entry["created_at"]),
                metadata=index_entry.get("metadata", {})
            )

        except Exception as e:
            logger.error(f"Failed to get item {key}: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """删除数据"""
        try:
            if key not in self.index:
                return False

            index_entry = self.index[key]
            file_path = Path(index_entry["file"])

            # 删除文件
            if file_path.exists():
                file_path.unlink()

            # 从索引中删除
            del self.index[key]
            self._save_index()

            return True

        except Exception as e:
            logger.error(f"Failed to delete item {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """检查是否存在"""
        return key in self.index

    async def list(self, prefix: str = "") -> List[str]:
        """列出键"""
        if not prefix:
            return list(self.index.keys())
        return [k for k in self.index.keys() if k.startswith(prefix)]

    async def clear(self) -> bool:
        """清空存储"""
        try:
            shutil.rmtree(self.storage_dir)
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self.index = {}
            self._save_index()
            return True
        except Exception as e:
            logger.error(f"Failed to clear storage: {e}")
            return False


# ============================================================================
# 4. SQLite存储后端
# ============================================================================

class SQLiteStorageBackend(StorageBackend):
    """SQLite存储后端"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = asyncio.Lock()
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS storage (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    format TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON storage (created_at)
            """)
            conn.commit()

    async def put(self, item: StorageItem) -> bool:
        """存储数据"""
        async with self.lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    # 序列化数据
                    if item.format == DataFormat.JSON:
                        value = json.dumps(item.value, default=str).encode('utf-8')
                    elif item.format == DataFormat.PICKLE:
                        value = pickle.dumps(item.value)
                    else:
                        value = item.value if isinstance(item.value, bytes) else str(item.value).encode()

                    # 压缩
                    if item.metadata.get("compressed"):
                        value = zlib.compress(value)

                    await db.execute(
                        """
                        INSERT OR REPLACE INTO storage
                        (key, value, format, size, created_at, updated_at, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.key,
                            value,
                            item.format.value,
                            len(value),
                            item.created_at.isoformat(),
                            datetime.now().isoformat() if item.updated_at else None,
                            json.dumps(item.metadata)
                        )
                    )
                    await db.commit()
                    return True

            except Exception as e:
                logger.error(f"Failed to put item {item.key}: {e}")
                return False

    async def get(self, key: str) -> Optional[StorageItem]:
        """获取数据"""
        async with self.lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        "SELECT value, format, size, created_at, updated_at, metadata FROM storage WHERE key = ?",
                        (key,)
                    )
                    row = await cursor.fetchone()

                    if not row:
                        return None

                    value, format_str, size, created_at, updated_at, metadata_json = row

                    # 解压缩
                    if json.loads(metadata_json).get("compressed"):
                        value = zlib.decompress(value)

                    # 反序列化
                    if format_str == "json":
                        item_value = json.loads(value.decode('utf-8'))
                    elif format_str == "pickle":
                        item_value = pickle.loads(value)
                    else:
                        item_value = value

                    return StorageItem(
                        key=key,
                        value=item_value,
                        format=DataFormat(format_str),
                        size=size,
                        created_at=datetime.fromisoformat(created_at),
                        updated_at=datetime.fromisoformat(updated_at) if updated_at else None,
                        metadata=json.loads(metadata_json) if metadata_json else {}
                    )

            except Exception as e:
                logger.error(f"Failed to get item {key}: {e}")
                return None

    async def delete(self, key: str) -> bool:
        """删除数据"""
        async with self.lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute("DELETE FROM storage WHERE key = ?", (key,))
                    await db.commit()
                    return True
            except Exception as e:
                logger.error(f"Failed to delete item {key}: {e}")
                return False

    async def exists(self, key: str) -> bool:
        """检查是否存在"""
        async with self.lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute("SELECT COUNT(*) FROM storage WHERE key = ?", (key,))
                    result = await cursor.fetchone()
                    return result[0] > 0
            except Exception as e:
                logger.error(f"Failed to check existence of {key}: {e}")
                return False

    async def list(self, prefix: str = "") -> List[str]:
        """列出键"""
        async with self.lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    if prefix:
                        cursor = await db.execute(
                            "SELECT key FROM storage WHERE key LIKE ?",
                            (f"{prefix}%",)
                        )
                    else:
                        cursor = await db.execute("SELECT key FROM storage")
                    rows = await cursor.fetchall()
                    return [row[0] for row in rows]
            except Exception as e:
                logger.error(f"Failed to list keys: {e}")
                return []

    async def clear(self) -> bool:
        """清空存储"""
        async with self.lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute("DELETE FROM storage")
                    await db.commit()
                    return True
            except Exception as e:
                logger.error(f"Failed to clear storage: {e}")
                return False


# ============================================================================
# 5. 缓存层
# ============================================================================

class StorageCache:
    """存储缓存层"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, StorageItem] = {}
        self.access_order = deque(maxlen=max_size)
        self.hits = 0
        self.misses = 0

    async def get(self, key: str) -> Optional[StorageItem]:
        """获取缓存"""
        if key in self.cache:
            self.hits += 1
            self.access_order.append(key)
            return self.cache[key]
        else:
            self.misses += 1
            return None

    async def put(self, item: StorageItem):
        """设置缓存"""
        if len(self.cache) >= self.max_size:
            # 淘汰最久未使用的
            oldest = self.access_order.popleft()
            del self.cache[oldest]

        self.cache[item.key] = item
        self.access_order.append(item.key)

    async def invalidate(self, key: str):
        """使缓存失效"""
        if key in self.cache:
            del self.cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self.hits + self.misses
        hit_rate = (self.hits / max(total, 1)) * 100
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "size": len(self.cache),
            "max_size": self.max_size
        }


# ============================================================================
# 6. 高级存储管理器
# ============================================================================

class AdvancedStorageManager:
    """高级存储管理器

    功能特性:
    - 多后端支持
    - 读写分离
    - 数据分片
    - 缓存层
    - 数据压缩
    - 备份恢复
    - 性能监控
    """

    def __init__(
        self,
        primary_backend: StorageBackend,
        read_backends: Optional[List[StorageBackend]] = None,
        cache_enabled: bool = True,
        compression_enabled: bool = True
    ):
        self.primary_backend = primary_backend
        self.read_backends = read_backends or [primary_backend]
        self.cache = StorageCache() if cache_enabled else None
        self.compression_enabled = compression_enabled

        # 指标
        self.metrics = StorageMetrics()
        self.read_metrics = defaultdict(int)

    async def put(
        self,
        key: str,
        value: Any,
        format: DataFormat = DataFormat.JSON,
        backup: bool = True
    ) -> bool:
        """存储数据"""
        start_time = datetime.now()

        # 创建存储项
        item = StorageItem(
            key=key,
            value=value,
            format=format,
            metadata={"compressed": self.compression_enabled}
        )

        # 写入主后端
        success = await self.primary_backend.put(item)

        if success:
            # 更新缓存
            if self.cache:
                await self.cache.put(item)

            # 写入备份
            if backup and self.read_backends and len(self.read_backends) > 1:
                for backend in self.read_backends[1:]:
                    try:
                        await backend.put(item)
                    except Exception as e:
                        logger.warning(f"Backup write failed: {e}")

            # 更新指标
            self.metrics.writes += 1
            self.metrics.total_size += item.size
            self.metrics.item_count += 1

        return success

    async def get(self, key: str, use_cache: bool = True) -> Optional[Any]:
        """获取数据"""
        start_time = datetime.now()

        # 先查缓存
        if use_cache and self.cache:
            cached_item = await self.cache.get(key)
            if cached_item:
                self.metrics.cache_hits += 1
                return cached_item.value
            self.metrics.cache_misses += 1

        # 从读取后端获取
        for backend in self.read_backends:
            try:
                item = await backend.get(key)
                if item:
                    # 更新缓存
                    if self.cache:
                        await self.cache.put(item)

                    # 更新指标
                    self.metrics.reads += 1
                    self.read_metrics[backend.__class__.__name__] += 1

                    return item.value
            except Exception as e:
                logger.warning(f"Read from {backend.__class__.__name__} failed: {e}")
                continue

        return None

    async def delete(self, key: str, cascade: bool = True) -> bool:
        """删除数据"""
        success = True

        # 从主后端删除
        if not await self.primary_backend.delete(key):
            success = False

        # 级联删除
        if cascade and self.read_backends:
            for backend in self.read_backends:
                try:
                    await backend.delete(key)
                except Exception as e:
                    logger.warning(f"Cascade delete failed: {e}")

        # 从缓存删除
        if self.cache:
            await self.cache.invalidate(key)

        if success:
            self.metrics.deletes += 1
            self.metrics.item_count -= 1

        return success

    async def exists(self, key: str) -> bool:
        """检查是否存在"""
        # 先查缓存
        if self.cache:
            cached_item = await self.cache.get(key)
            if cached_item:
                return True

        # 从后端检查
        for backend in self.read_backends:
            if await backend.exists(key):
                return True

        return False

    async def list(self, prefix: str = "") -> List[str]:
        """列出键"""
        if self.read_backends:
            return await self.read_backends[0].list(prefix)
        return []

    async def clear_all(self) -> bool:
        """清空所有存储"""
        success = True

        # 清空所有后端
        all_backends = [self.primary_backend] + self.read_backends
        for backend in all_backends:
            if not await backend.clear():
                success = False

        # 清空缓存
        if self.cache:
            self.cache.cache.clear()
            self.cache.access_order.clear()

        return success

    async def backup(self, backup_path: str) -> bool:
        """备份数据"""
        try:
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)

            # 列出所有键
            keys = await self.list()

            # 备份每个项
            for key in keys:
                item = await self.primary_backend.get(key)
                if item:
                    backup_file = backup_dir / f"{key}.backup"
                    with open(backup_file, 'wb') as f:
                        pickle.dump(item, f)

            return True

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False

    async def restore(self, backup_path: str) -> bool:
        """恢复数据"""
        try:
            backup_dir = Path(backup_path)
            if not backup_dir.exists():
                return False

            # 恢复每个备份文件
            for backup_file in backup_dir.glob("*.backup"):
                with open(backup_file, 'rb') as f:
                    item = pickle.load(f)

                await self.primary_backend.put(item)

            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_ops = self.metrics.reads + self.metrics.writes + self.metrics.deletes
        cache_stats = self.cache.get_stats() if self.cache else {}

        return {
            "primary_backend": self.primary_backend.__class__.__name__,
            "read_backends": [b.__class__.__name__ for b in self.read_backends],
            "metrics": {
                **self.metrics.__dict__,
                "total_operations": total_ops,
                "cache_stats": cache_stats,
            },
            "read_distribution": dict(self.read_metrics)
        }


# ============================================================================
# 7. 使用示例
# ============================================================================

async def example_custom_storage():
    """自定义存储后端示例"""

    # 1. 创建存储后端
    print("\n=== 创建存储后端 ===")
    local_backend = LocalFileStorageBackend("./storage/local")
    sqlite_backend = SQLiteStorageBackend("./storage/data.db")

    print(f"本地存储: {local_backend.storage_dir}")
    print(f"SQLite存储: {sqlite_backend.db_path}")

    # 2. 创建高级存储管理器
    print("\n=== 创建存储管理器 ===")
    storage_manager = AdvancedStorageManager(
        primary_backend=sqlite_backend,
        read_backends=[sqlite_backend, local_backend],
        cache_enabled=True,
        compression_enabled=True
    )

    # 3. 存储数据
    print("\n=== 存储数据 ===")
    test_data = {
        "name": "Test Project",
        "version": "1.0.0",
        "config": {
            "debug": True,
            "log_level": "INFO"
        },
        "items": [f"item_{i}" for i in range(100)]
    }

    await storage_manager.put("project/config", test_data, DataFormat.JSON)
    await storage_manager.put("project/metadata", {"author": "Claude"}, DataFormat.JSON)
    await storage_manager.put("project/data", b"Binary data here", DataFormat.BINARY)

    print("存储了3个项目")

    # 4. 读取数据
    print("\n=== 读取数据 ===")
    config = await storage_manager.get("project/config")
    metadata = await storage_manager.get("project/metadata")
    binary_data = await storage_manager.get("project/data")

    print(f"配置: {config['name']} v{config['version']}")
    print(f"元数据: {metadata}")
    print(f"二进制数据大小: {len(binary_data)} bytes")

    # 5. 检查存在性
    print("\n=== 检查存在性 ===")
    exists_config = await storage_manager.exists("project/config")
    exists_missing = await storage_manager.exists("project/nonexistent")

    print(f"配置存在: {exists_config}")
    print(f"不存在项存在: {exists_missing}")

    # 6. 列出键
    print("\n=== 列出键 ===")
    keys = await storage_manager.list("project/")
    print(f"项目键: {keys}")

    # 7. 缓存测试
    print("\n=== 缓存测试 ===")
    # 第一次读取（缓存未命中）
    await storage_manager.get("project/config")
    # 第二次读取（缓存命中）
    await storage_manager.get("project/config")

    # 8. 备份和恢复
    print("\n=== 备份和恢复 ===")
    backup_success = await storage_manager.backup("./storage/backup")
    print(f"备份结果: {backup_success}")

    # 9. 删除数据
    print("\n=== 删除数据 ===")
    delete_success = await storage_manager.delete("project/data")
    print(f"删除结果: {delete_success}")

    # 验证删除
    deleted_data = await storage_manager.get("project/data")
    print(f"删除后读取: {deleted_data}")

    # 10. 显示统计信息
    print("\n=== 存储统计 ===")
    stats = storage_manager.get_stats()
    print(f"主后端: {stats['primary_backend']}")
    print(f"读取后端: {stats['read_backends']}")

    print("\n指标:")
    metrics = stats["metrics"]
    for key, value in metrics.items():
        if key != "cache_stats":
            print(f"  {key}: {value}")

    if metrics.get("cache_stats"):
        print("\n缓存统计:")
        cache_stats = metrics["cache_stats"]
        for key, value in cache_stats.items():
            print(f"  {key}: {value}")

    print("\n读取分布:")
    for backend, count in stats["read_distribution"].items():
        print(f"  {backend}: {count}")

    # 11. 清理
    print("\n=== 清理 ===")
    await storage_manager.clear_all()
    print("存储已清空")


# ============================================================================
# 8. 高级功能：数据分片
# ============================================================================

class ShardedStorageManager:
    """分片存储管理器

    将数据分布到多个存储后端。
    """

    def __init__(self, backends: List[StorageBackend], shard_count: int = 4):
        self.backends = backends
        self.shard_count = shard_count

    def _get_shard(self, key: str) -> int:
        """根据键计算分片"""
        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return hash_value % self.shard_count

    async def put(self, key: str, value: Any, format: DataFormat = DataFormat.JSON):
        """存储数据到指定分片"""
        shard = self._get_shard(key)
        backend = self.backends[shard % len(self.backends)]

        item = StorageItem(key=key, value=value, format=format)
        return await backend.put(item)

    async def get(self, key: str) -> Optional[Any]:
        """从指定分片获取数据"""
        shard = self._get_shard(key)
        backend = self.backends[shard % len(self.backends)]

        item = await backend.get(key)
        return item.value if item else None


# ============================================================================
# 9. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_custom_storage())
