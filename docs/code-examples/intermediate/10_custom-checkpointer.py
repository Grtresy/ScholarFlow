#!/usr/bin/env python3
"""
高级代码示例10: 自定义Checkpointer
===================================

本示例展示如何构建一个功能完整的自定义Checkpointer系统，
用于ScholarFlow工作流中的状态持久化和恢复。

功能特性:
- 多存储后端支持
- 增量检查点
- 状态压缩
- 并发控制
- 检查点版本管理
- 自动清理机制
- 分布式检查点

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
import hashlib
import zlib
from pathlib import Path
from collections import defaultdict, deque
import uuid
import threading
from abc import ABC, abstractmethod

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class CheckpointType(Enum):
    """检查点类型"""
    FULL = "full"          # 完整状态
    INCREMENTAL = "incremental"  # 增量状态
    DIFF = "diff"          # 差异状态
    COMPRESSED = "compressed"    # 压缩状态


@dataclass
class CheckpointMetadata:
    """检查点元数据"""
    checkpoint_id: str
    thread_id: str
    node_name: str
    checkpoint_type: CheckpointType
    created_at: datetime = field(default_factory=datetime.now)
    state_size: int = 0
    compressed: bool = False
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckpointRecord:
    """检查点记录"""
    metadata: CheckpointMetadata
    state_data: bytes
    version: int = 1


# ============================================================================
# 2. 存储后端接口
# ============================================================================

class CheckpointStorageBackend(ABC):
    """检查点存储后端基类"""

    @abstractmethod
    async def save_checkpoint(self, record: CheckpointRecord) -> bool:
        """保存检查点"""
        pass

    @abstractmethod
    async def load_checkpoint(
        self,
        thread_id: str,
        node_name: str
    ) -> Optional[CheckpointRecord]:
        """加载检查点"""
        pass

    @abstractmethod
    async def list_checkpoints(
        self,
        thread_id: Optional[str] = None
    ) -> List[CheckpointMetadata]:
        """列出检查点"""
        pass

    @abstractmethod
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """删除检查点"""
        pass

    @abstractmethod
    async def cleanup_old_checkpoints(
        self,
        thread_id: str,
        keep_count: int = 10
    ) -> int:
        """清理旧检查点"""
        pass


# ============================================================================
# 3. SQLite存储后端
# ============================================================================

class SQLiteCheckpointBackend(CheckpointStorageBackend):
    """SQLite检查点存储后端

    使用SQLite数据库存储检查点。
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = asyncio.Lock()
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    node_name TEXT NOT NULL,
                    checkpoint_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    state_size INTEGER NOT NULL,
                    compressed INTEGER NOT NULL,
                    checksum TEXT,
                    version INTEGER NOT NULL,
                    state_data BLOB NOT NULL,
                    metadata TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_thread_node
                ON checkpoints (thread_id, node_name)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON checkpoints (created_at)
            """)

            conn.commit()

    async def save_checkpoint(self, record: CheckpointRecord) -> bool:
        """保存检查点"""
        async with self.lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO checkpoints
                        (checkpoint_id, thread_id, node_name, checkpoint_type,
                         created_at, state_size, compressed, checksum, version,
                         state_data, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            record.metadata.checkpoint_id,
                            record.metadata.thread_id,
                            record.metadata.node_name,
                            record.metadata.checkpoint_type.value,
                            record.metadata.created_at.isoformat(),
                            record.metadata.state_size,
                            1 if record.metadata.compressed else 0,
                            record.metadata.checksum,
                            record.version,
                            record.state_data,
                            json.dumps(record.metadata.metadata)
                        )
                    )
                    await db.commit()
                    return True
            except Exception as e:
                logger.error(f"Failed to save checkpoint: {e}")
                return False

    async def load_checkpoint(
        self,
        thread_id: str,
        node_name: str
    ) -> Optional[CheckpointRecord]:
        """加载检查点"""
        async with self.lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        """
                        SELECT checkpoint_id, thread_id, node_name, checkpoint_type,
                               created_at, state_size, compressed, checksum, version,
                               state_data, metadata
                        FROM checkpoints
                        WHERE thread_id = ? AND node_name = ?
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        (thread_id, node_name)
                    )
                    row = await cursor.fetchone()

                    if not row:
                        return None

                    metadata = CheckpointMetadata(
                        checkpoint_id=row[0],
                        thread_id=row[1],
                        node_name=row[2],
                        checkpoint_type=CheckpointType(row[3]),
                        created_at=datetime.fromisoformat(row[4]),
                        state_size=row[5],
                        compressed=bool(row[6]),
                        checksum=row[7],
                        metadata=json.loads(row[10]) if row[10] else {}
                    )

                    return CheckpointRecord(
                        metadata=metadata,
                        state_data=row[9],
                        version=row[8]
                    )
            except Exception as e:
                logger.error(f"Failed to load checkpoint: {e}")
                return None

    async def list_checkpoints(
        self,
        thread_id: Optional[str] = None
    ) -> List[CheckpointMetadata]:
        """列出检查点"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if thread_id:
                    cursor = await db.execute(
                        """
                        SELECT checkpoint_id, thread_id, node_name, checkpoint_type,
                               created_at, state_size, compressed, checksum, metadata
                        FROM checkpoints
                        WHERE thread_id = ?
                        ORDER BY created_at DESC
                        """,
                        (thread_id,)
                    )
                else:
                    cursor = await db.execute(
                        """
                        SELECT checkpoint_id, thread_id, node_name, checkpoint_type,
                               created_at, state_size, compressed, checksum, metadata
                        FROM checkpoints
                        ORDER BY created_at DESC
                        """
                    )

                rows = await cursor.fetchall()
                return [
                    CheckpointMetadata(
                        checkpoint_id=row[0],
                        thread_id=row[1],
                        node_name=row[2],
                        checkpoint_type=CheckpointType(row[3]),
                        created_at=datetime.fromisoformat(row[4]),
                        state_size=row[5],
                        compressed=bool(row[6]),
                        checksum=row[7],
                        metadata=json.loads(row[8]) if row[8] else {}
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to list checkpoints: {e}")
            return []

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """删除检查点"""
        async with self.lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        "DELETE FROM checkpoints WHERE checkpoint_id = ?",
                        (checkpoint_id,)
                    )
                    await db.commit()
                    return True
            except Exception as e:
                logger.error(f"Failed to delete checkpoint: {e}")
                return False

    async def cleanup_old_checkpoints(
        self,
        thread_id: str,
        keep_count: int = 10
    ) -> int:
        """清理旧检查点"""
        async with self.lock:
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        """
                        SELECT checkpoint_id
                        FROM checkpoints
                        WHERE thread_id = ?
                        ORDER BY created_at DESC
                        """,
                        (thread_id,)
                    )
                    rows = await cursor.fetchall()

                    # 获取要删除的ID
                    delete_ids = [row[0] for row in rows[keep_count:]]

                    # 删除
                    for checkpoint_id in delete_ids:
                        await db.execute(
                            "DELETE FROM checkpoints WHERE checkpoint_id = ?",
                            (checkpoint_id,)
                        )

                    await db.commit()
                    return len(delete_ids)
            except Exception as e:
                logger.error(f"Failed to cleanup checkpoints: {e}")
                return 0


# ============================================================================
# 4. 文件存储后端
# ============================================================================

class FileCheckpointBackend(CheckpointStorageBackend):
    """文件检查点存储后端

    使用文件系统存储检查点。
    """

    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def _get_checkpoint_path(self, checkpoint_id: str) -> Path:
        """获取检查点文件路径"""
        return self.storage_dir / f"{checkpoint_id}.checkpoint"

    async def save_checkpoint(self, record: CheckpointRecord) -> bool:
        """保存检查点"""
        try:
            checkpoint_path = self._get_checkpoint_path(record.metadata.checkpoint_id)

            # 序列化记录
            data = {
                "metadata": {
                    **record.metadata.__dict__,
                    "checkpoint_type": record.metadata.checkpoint_type.value
                },
                "version": record.version,
                "state_data": record.state_data.hex()
            }

            # 写入文件
            with open(checkpoint_path, 'wb') as f:
                f.write(pickle.dumps(data))

            return True
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False

    async def load_checkpoint(
        self,
        thread_id: str,
        node_name: str
    ) -> Optional[CheckpointRecord]:
        """加载检查点（简化实现）"""
        # 文件后端不支持按thread_id和node_name查询
        # 这里返回最新的检查点
        try:
            checkpoint_files = list(self.storage_dir.glob("*.checkpoint"))
            if not checkpoint_files:
                return None

            latest_file = max(checkpoint_files, key=lambda p: p.stat().st_mtime)

            with open(latest_file, 'rb') as f:
                data = pickle.loads(f.read())

            metadata_data = data["metadata"]
            metadata_data["checkpoint_type"] = CheckpointType(metadata_data["checkpoint_type"])

            metadata = CheckpointMetadata(**metadata_data)

            return CheckpointRecord(
                metadata=metadata,
                state_data=bytes.fromhex(data["state_data"]),
                version=data["version"]
            )
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    async def list_checkpoints(
        self,
        thread_id: Optional[str] = None
    ) -> List[CheckpointMetadata]:
        """列出检查点"""
        try:
            checkpoint_files = list(self.storage_dir.glob("*.checkpoint"))
            metadata_list = []

            for file_path in checkpoint_files:
                with open(file_path, 'rb') as f:
                    data = pickle.loads(f.read())

                metadata_data = data["metadata"]
                metadata_data["checkpoint_type"] = CheckpointType(metadata_data["checkpoint_type"])
                metadata = CheckpointMetadata(**metadata_data)
                metadata_list.append(metadata)

            return sorted(metadata_list, key=lambda m: m.created_at, reverse=True)
        except Exception as e:
            logger.error(f"Failed to list checkpoints: {e}")
            return []

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """删除检查点"""
        try:
            checkpoint_path = self._get_checkpoint_path(checkpoint_id)
            if checkpoint_path.exists():
                checkpoint_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete checkpoint: {e}")
            return False

    async def cleanup_old_checkpoints(
        self,
        thread_id: str,
        keep_count: int = 10
    ) -> int:
        """清理旧检查点"""
        try:
            checkpoints = await self.list_checkpoints(thread_id)
            delete_count = len(checkpoints) - keep_count

            if delete_count > 0:
                for checkpoint in checkpoints[-delete_count:]:
                    await self.delete_checkpoint(checkpoint.checkpoint_id)

            return delete_count
        except Exception as e:
            logger.error(f"Failed to cleanup checkpoints: {e}")
            return 0


# ============================================================================
# 5. 状态压缩器
# ============================================================================

class StateCompressor:
    """状态压缩器"""

    @staticmethod
    def compress(data: bytes) -> tuple[bytes, str]:
        """压缩数据"""
        compressed = zlib.compress(data)
        checksum = hashlib.sha256(compressed).hexdigest()
        return compressed, checksum

    @staticmethod
    def decompress(data: bytes, checksum: str) -> bytes:
        """解压缩数据"""
        # 验证校验和
        calculated_checksum = hashlib.sha256(data).hexdigest()
        if calculated_checksum != checksum:
            raise ValueError("Checksum mismatch")

        return zlib.decompress(data)


# ============================================================================
# 6. 自定义Checkpointer
# ============================================================================

class CustomCheckpointer:
    """自定义Checkpointer

    功能特性:
    - 多存储后端支持
    - 状态压缩
    - 并发控制
    - 自动清理
    - 版本管理
    """

    def __init__(
        self,
        backend: CheckpointStorageBackend,
        enable_compression: bool = True,
        auto_cleanup: bool = True,
        max_checkpoints_per_thread: int = 50
    ):
        self.backend = backend
        self.enable_compression = enable_compression
        self.auto_cleanup = auto_cleanup
        self.max_checkpoints_per_thread = max_checkpoints_per_thread

        self.compressor = StateCompressor()
        self.stats = {
            "saves": 0,
            "loads": 0,
            "compressions": 0,
            "bytes_saved": 0,
        }

    async def aget(
        self,
        thread_id: str,
        node_name: str
    ) -> Optional[Dict[str, Any]]:
        """获取状态"""
        record = await self.backend.load_checkpoint(thread_id, node_name)

        if not record:
            return None

        self.stats["loads"] += 1

        # 解压缩
        state_data = record.state_data
        if record.metadata.compressed:
            state_data = self.compressor.decompress(
                state_data,
                record.metadata.checksum
            )

        # 反序列化
        return pickle.loads(state_data)

    async def aput(
        self,
        thread_id: str,
        node_name: str,
        state: Dict[str, Any],
        checkpoint_type: CheckpointType = CheckpointType.FULL
    ) -> str:
        """保存状态"""
        # 序列化状态
        state_bytes = pickle.dumps(state)

        # 压缩
        compressed = False
        checksum = None
        if self.enable_compression:
            state_bytes, checksum = self.compressor.compress(state_bytes)
            compressed = True
            self.stats["compressions"] += 1

        # 创建元数据
        checkpoint_id = f"{thread_id}:{node_name}:{uuid.uuid4().hex[:8]}"
        metadata = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            thread_id=thread_id,
            node_name=node_name,
            checkpoint_type=checkpoint_type,
            state_size=len(state_bytes),
            compressed=compressed,
            checksum=checksum,
            metadata={
                "original_size": len(pickle.dumps(state)),
            }
        )

        # 创建记录
        record = CheckpointRecord(
            metadata=metadata,
            state_data=state_bytes
        )

        # 保存
        success = await self.backend.save_checkpoint(record)

        if success:
            self.stats["saves"] += 1
            self.stats["bytes_saved"] += len(state_bytes)

            # 自动清理
            if self.auto_cleanup:
                await self.backend.cleanup_old_checkpoints(
                    thread_id,
                    self.max_checkpoints_per_thread
                )

        return checkpoint_id

    async def alist(
        self,
        thread_id: Optional[str] = None
    ) -> List[CheckpointMetadata]:
        """列出检查点"""
        return await self.backend.list_checkpoints(thread_id)

    async def adelete(self, checkpoint_id: str) -> bool:
        """删除检查点"""
        return await self.backend.delete_checkpoint(checkpoint_id)

    async def acleanup(
        self,
        thread_id: str,
        keep_count: Optional[int] = None
    ) -> int:
        """清理旧检查点"""
        keep = keep_count or self.max_checkpoints_per_thread
        return await self.backend.cleanup_old_checkpoints(thread_id, keep)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        compression_ratio = (
            self.stats["bytes_saved"] / max(self.stats["saves"], 1)
        ) if self.stats["saves"] > 0 else 0

        return {
            **self.stats,
            "compression_ratio": compression_ratio,
        }


# ============================================================================
# 7. 分布式Checkpointer
# ============================================================================

class DistributedCheckpointer:
    """分布式Checkpointer

    支持多节点分布式检查点存储。
    """

    def __init__(self, backends: List[CheckpointStorageBackend]):
        self.backends = backends
        self.replication_factor = min(3, len(backends))

    async def aput(
        self,
        thread_id: str,
        node_name: str,
        state: Dict[str, Any]
    ) -> str:
        """保存到多个后端"""
        checkpoint_id = f"{thread_id}:{node_name}:{uuid.uuid4().hex[:8]}"

        # 序列化状态
        state_bytes = pickle.dumps(state)
        compressed, checksum = StateCompressor.compress(state_bytes)

        metadata = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            thread_id=thread_id,
            node_name=node_name,
            checkpoint_type=CheckpointType.COMPRESSED,
            state_size=len(compressed),
            compressed=True,
            checksum=checksum
        )

        record = CheckpointRecord(
            metadata=metadata,
            state_data=compressed
        )

        # 保存到多个后端
        success_count = 0
        for backend in self.backends[:self.replication_factor]:
            if await backend.save_checkpoint(record):
                success_count += 1

        if success_count < self.replication_factor // 2 + 1:
            raise Exception(f"Failed to replicate to enough backends: {success_count}/{self.replication_factor}")

        return checkpoint_id

    async def aget(
        self,
        thread_id: str,
        node_name: str
    ) -> Optional[Dict[str, Any]]:
        """从多个后端加载"""
        for backend in self.backends:
            record = await backend.load_checkpoint(thread_id, node_name)
            if record:
                state_bytes = StateCompressor.decompress(
                    record.state_data,
                    record.metadata.checksum
                )
                return pickle.loads(state_bytes)

        return None


# ============================================================================
# 8. 使用示例
# ============================================================================

async def example_custom_checkpointer():
    """自定义Checkpointer示例"""

    # 1. 创建SQLite后端
    print("\n=== SQLite后端示例 ===")
    sqlite_backend = SQLiteCheckpointBackend("./checkpoints.db")
    checkpointer = CustomCheckpointer(
        backend=sqlite_backend,
        enable_compression=True,
        auto_cleanup=True,
        max_checkpoints_per_thread=5
    )

    # 2. 保存检查点
    print("\n保存检查点...")
    state1 = {
        "task_id": "task_001",
        "status": "processing",
        "progress": 25,
        "data": {"key1": "value1", "key2": "value2"}
    }
    checkpoint_id1 = await checkpointer.aput(
        thread_id="thread_001",
        node_name="node_1",
        state=state1
    )
    print(f"检查点1 ID: {checkpoint_id1}")

    # 3. 继续处理并保存另一个检查点
    print("\n保存检查点...")
    state2 = {
        "task_id": "task_001",
        "status": "processing",
        "progress": 50,
        "data": {"key1": "value1", "key2": "value2", "key3": "value3"}
    }
    checkpoint_id2 = await checkpointer.aput(
        thread_id="thread_001",
        node_name="node_2",
        state=state2
    )
    print(f"检查点2 ID: {checkpoint_id2}")

    # 4. 加载检查点
    print("\n加载检查点...")
    loaded_state = await checkpointer.aget("thread_001", "node_1")
    print(f"加载的状态: {loaded_state}")

    # 5. 列出检查点
    print("\n列出检查点...")
    checkpoints = await checkpointer.alist("thread_001")
    for cp in checkpoints:
        print(f"  {cp.checkpoint_id} - {cp.node_name} - {cp.created_at.strftime('%H:%M:%S')}")

    # 6. 显示统计信息
    print("\n=== 统计信息 ===")
    stats = checkpointer.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")

    # 7. 文件后端示例
    print("\n\n=== 文件后端示例 ===")
    file_backend = FileCheckpointBackend("./file_checkpoints")
    file_checkpointer = CustomCheckpointer(
        backend=file_backend,
        enable_compression=True
    )

    # 保存到文件
    checkpoint_id3 = await file_checkpointer.aput(
        thread_id="thread_002",
        node_name="node_1",
        state=state1
    )
    print(f"文件检查点 ID: {checkpoint_id3}")

    # 8. 分布式检查点示例
    print("\n\n=== 分布式检查点示例 ===")
    distributed = DistributedCheckpointer([
        sqlite_backend,
        file_backend
    ])

    distributed_id = await distributed.aput(
        thread_id="thread_003",
        node_name="node_1",
        state=state1
    )
    print(f"分布式检查点 ID: {distributed_id}")

    distributed_state = await distributed.aget("thread_003", "node_1")
    print(f"分布式加载状态: {distributed_state}")

    # 9. 清理示例
    print("\n\n=== 清理示例 ===")
    deleted_count = await checkpointer.acleanup("thread_001", keep_count=1)
    print(f"删除了 {deleted_count} 个旧检查点")


# ============================================================================
# 9. 高级功能：检查点合并
# ============================================================================

class CheckpointMerger:
    """检查点合并器

    合并多个检查点为增量检查点。
    """

    @staticmethod
    async def merge_checkpoints(
        base_state: Dict[str, Any],
        incremental_states: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """合并检查点"""
        merged = base_state.copy()

        for state in incremental_states:
            merged.update(state)

        return merged

    @staticmethod
    async def create_incremental_checkpoint(
        old_state: Dict[str, Any],
        new_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建增量检查点"""
        incremental = {}

        for key, new_value in new_state.items():
            old_value = old_state.get(key)
            if old_value != new_value:
                incremental[key] = {
                    "old": old_value,
                    "new": new_value
                }

        return {
            "incremental_changes": incremental,
            "base_hash": hashlib.sha256(
                json.dumps(old_state, sort_keys=True, default=str).encode()
            ).hexdigest()
        }


# ============================================================================
# 10. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_custom_checkpointer())
