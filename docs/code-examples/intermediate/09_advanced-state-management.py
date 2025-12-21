#!/usr/bin/env python3
"""
高级代码示例9: 高级状态管理
=============================

本示例展示如何构建一个功能完整的高级状态管理系统，
用于ScholarFlow工作流中的复杂状态操作。

功能特性:
- 异步状态管理器
- 状态版本控制
- 状态压缩与优化
- 状态分区管理
- 状态变更追踪
- 状态验证器
- 状态快照与恢复

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
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import hashlib
import zlib
import pickle
from collections import defaultdict, deque
import uuid

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class StateOperation(Enum):
    """状态操作类型"""
    READ = "read"
    WRITE = "write"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    VALIDATE = "validate"


class CompressionType(Enum):
    """压缩类型"""
    NONE = "none"
    ZLIB = "zlib"
    GZIP = "gzip"
    PICKLE = "pickle"


@dataclass
class StateChange:
    """状态变更记录"""
    change_id: str
    operation: StateOperation
    field_path: str
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateVersion:
    """状态版本"""
    version_id: str
    state_hash: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    compressed: bool = False
    compression_type: Optional[CompressionType] = None


@dataclass
class StateSnapshot:
    """状态快照"""
    snapshot_id: str
    task_id: str
    version_id: str
    state_data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 2. 状态分区管理器
# ============================================================================

class StatePartition:
    """状态分区

    将状态数据分区管理，提高效率。
    """

    def __init__(self, partition_name: str):
        self.partition_name = partition_name
        self.data: Dict[str, Any] = {}
        self.access_count = 0
        self.last_access = datetime.now()

    def get(self, key: str, default: Any = None) -> Any:
        """获取值"""
        self.access_count += 1
        self.last_access = datetime.now()
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        """设置值"""
        self.data[key] = value
        self.access_count += 1
        self.last_access = datetime.now()

    def delete(self, key: str):
        """删除值"""
        if key in self.data:
            del self.data[key]
            self.access_count += 1
            self.last_access = datetime.now()

    def merge(self, other: Dict[str, Any]):
        """合并数据"""
        self.data.update(other)
        self.access_count += 1
        self.last_access = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.data.copy()

    def from_dict(self, data: Dict[str, Any]):
        """从字典加载"""
        self.data = data.copy()


class StatePartitionManager:
    """状态分区管理器"""

    def __init__(self):
        self.partitions: Dict[str, StatePartition] = {}
        self.access_order = deque(maxlen=1000)

    def get_partition(self, name: str) -> StatePartition:
        """获取分区"""
        if name not in self.partitions:
            self.partitions[name] = StatePartition(name)
        return self.partitions[name]

    def list_partitions(self) -> List[str]:
        """列出所有分区"""
        return list(self.partitions.keys())

    def get_partition_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取分区统计"""
        stats = {}
        for name, partition in self.partitions.items():
            stats[name] = {
                "size": len(partition.data),
                "access_count": partition.access_count,
                "last_access": partition.last_access.isoformat(),
            }
        return stats


# ============================================================================
# 3. 状态验证器
# ============================================================================

class StateValidator:
    """状态验证器

    验证状态数据的完整性和正确性。
    """

    def __init__(self):
        self.rules: List[Dict[str, Any]] = []

    def add_rule(
        self,
        field_path: str,
        validator_func: Callable,
        required: bool = False,
        error_message: str = "Validation failed"
    ):
        """添加验证规则"""
        self.rules.append({
            "field_path": field_path,
            "validator": validator_func,
            "required": required,
            "error_message": error_message,
        })

    def validate(self, state: Dict[str, Any]) -> Dict[str, List[str]]:
        """验证状态"""
        errors = defaultdict(list)

        for rule in self.rules:
            field_path = rule["field_path"]
            validator = rule["validator"]
            required = rule["required"]
            error_msg = rule["error_message"]

            # 获取字段值
            value = self._get_nested_value(state, field_path)

            # 检查必需字段
            if required and value is None:
                errors[field_path].append(f"Required field missing: {field_path}")
                continue

            # 跳过空值（除非是必需的）
            if value is None and not required:
                continue

            # 执行验证
            try:
                if not validator(value):
                    errors[field_path].append(error_msg)
            except Exception as e:
                errors[field_path].append(f"Validation error: {str(e)}")

        return dict(errors)

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """获取嵌套字典值"""
        keys = path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value


# ============================================================================
# 4. 状态压缩器
# ============================================================================

class StateCompressor:
    """状态压缩器

    对状态数据进行压缩以节省存储空间。
    """

    @staticmethod
    def compress(
        data: Dict[str, Any],
        compression_type: CompressionType = CompressionType.ZLIB
    ) -> bytes:
        """压缩数据"""
        json_data = json.dumps(data, default=str).encode('utf-8')

        if compression_type == CompressionType.ZLIB:
            return zlib.compress(json_data)
        elif compression_type == CompressionType.GZIP:
            import gzip
            return gzip.compress(json_data)
        elif compression_type == CompressionType.PICKLE:
            return pickle.dumps(data)
        else:
            return json_data

    @staticmethod
    def decompress(
        compressed_data: bytes,
        compression_type: CompressionType = CompressionType.ZLIB
    ) -> Dict[str, Any]:
        """解压缩数据"""
        if compression_type == CompressionType.ZLIB:
            json_data = zlib.decompress(compressed_data)
        elif compression_type == CompressionType.GZIP:
            import gzip
            json_data = gzip.decompress(compressed_data)
        elif compression_type == CompressionType.PICKLE:
            return pickle.loads(compressed_data)
        else:
            json_data = compressed_data

        return json.loads(json_data.decode('utf-8'))

    @staticmethod
    def calculate_compression_ratio(
        original: bytes,
        compressed: bytes
    ) -> float:
        """计算压缩比"""
        if len(original) == 0:
            return 0.0
        return (1 - len(compressed) / len(original)) * 100


# ============================================================================
# 5. 高级状态管理器
# ============================================================================

class AdvancedStateManager:
    """高级状态管理器

    功能特性:
    - 异步状态操作
    - 版本控制
    - 分区管理
    - 变更追踪
    - 状态验证
    - 压缩优化
    - 快照管理
    """

    def __init__(
        self,
        task_id: str,
        enable_versioning: bool = True,
        enable_compression: bool = True,
        compression_type: CompressionType = CompressionType.ZLIB
    ):
        self.task_id = task_id
        self.enable_versioning = enable_versioning
        self.enable_compression = enable_compression
        self.compression_type = compression_type

        # 核心组件
        self.partition_manager = StatePartitionManager()
        self.validator = StateValidator()
        self.compressor = StateCompressor()

        # 状态存储
        self.current_state: Dict[str, Any] = {}
        self.state_history: deque = deque(maxlen=100)
        self.change_log: List[StateChange] = []
        self.versions: List[StateVersion] = []
        self.snapshots: Dict[str, StateSnapshot] = {}

        # 统计信息
        self.stats = {
            "reads": 0,
            "writes": 0,
            "updates": 0,
            "validations": 0,
            "compressions": 0,
            "snapshots": 0,
        }

        # 设置默认验证规则
        self._setup_default_validators()

    def _setup_default_validators(self):
        """设置默认验证器"""
        # 必需字段验证
        self.validator.add_rule(
            "task_id",
            lambda x: x is not None,
            required=True,
            error_message="Task ID is required"
        )

        # 状态值验证
        self.validator.add_rule(
            "status",
            lambda x: x in ["pending", "processing", "completed", "error"],
            required=True,
            error_message="Invalid status value"
        )

        # 数字范围验证
        self.validator.add_rule(
            "progress",
            lambda x: 0 <= x <= 100 if x is not None else True,
            required=False,
            error_message="Progress must be between 0 and 100"
        )

    async def set_state(
        self,
        field_path: str,
        value: Any,
        validate: bool = True,
        track_change: bool = True
    ) -> bool:
        """设置状态值"""
        # 记录旧值
        old_value = self._get_nested_value(self.current_state, field_path)

        # 设置新值
        self._set_nested_value(self.current_state, field_path, value)

        # 记录变更
        if track_change:
            change = StateChange(
                change_id=str(uuid.uuid4()),
                operation=StateOperation.WRITE,
                field_path=field_path,
                old_value=old_value,
                new_value=value
            )
            self.change_log.append(change)

        # 验证
        if validate:
            errors = self.validator.validate(self.current_state)
            if errors:
                logger.warning(f"Validation errors: {errors}")

        # 更新统计
        self.stats["writes"] += 1

        # 创建版本（可选）
        if self.enable_versioning:
            await self._create_version()

        return True

    async def get_state(
        self,
        field_path: Optional[str] = None,
        default: Any = None
    ) -> Any:
        """获取状态值"""
        self.stats["reads"] += 1

        if field_path is None:
            return self.current_state.copy()

        return self._get_nested_value(self.current_state, field_path) or default

    async def update_state(
        self,
        updates: Dict[str, Any],
        validate: bool = True,
        track_change: bool = True
    ) -> bool:
        """批量更新状态"""
        old_state = self.current_state.copy()

        for field_path, value in updates.items():
            await self.set_state(
                field_path,
                value,
                validate=False,
                track_change=track_change
            )

        # 验证整个状态
        if validate:
            errors = self.validator.validate(self.current_state)
            if errors:
                # 回滚
                self.current_state = old_state
                raise ValueError(f"Validation failed: {errors}")

        self.stats["updates"] += 1
        return True

    async def merge_state(
        self,
        other_state: Dict[str, Any],
        strategy: str = "overwrite"  # overwrite/merge/preserve
    ):
        """合并状态"""
        if strategy == "overwrite":
            self.current_state.update(other_state)
        elif strategy == "merge":
            # 深度合并
            self._deep_merge(self.current_state, other_state)
        elif strategy == "preserve":
            # 保留现有值
            for key, value in other_state.items():
                if key not in self.current_state:
                    self.current_state[key] = value

        self.stats["updates"] += 1

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]):
        """深度合并字典"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    async def validate_state(self) -> Dict[str, List[str]]:
        """验证当前状态"""
        self.stats["validations"] += 1
        return self.validator.validate(self.current_state)

    async def create_snapshot(
        self,
        name: Optional[str] = None,
        compress: Optional[bool] = None
    ) -> str:
        """创建状态快照"""
        snapshot_id = name or f"snapshot_{uuid.uuid4().hex[:8]}"
        compress = compress if compress is not None else self.enable_compression

        # 准备快照数据
        snapshot_data = {
            "task_id": self.task_id,
            "state": self.current_state,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "compression": compress,
            }
        }

        # 压缩（可选）
        compressed_data = None
        if compress:
            snapshot_data["state"] = self.compressor.compress(
                snapshot_data["state"],
                self.compression_type
            )
            self.stats["compressions"] += 1

        # 创建快照
        snapshot = StateSnapshot(
            snapshot_id=snapshot_id,
            task_id=self.task_id,
            version_id=str(uuid.uuid4()),
            state_data=snapshot_data,
            size_bytes=len(str(snapshot_data))
        )

        self.snapshots[snapshot_id] = snapshot
        self.stats["snapshots"] += 1

        logger.info(f"Created snapshot: {snapshot_id}")
        return snapshot_id

    async def restore_snapshot(self, snapshot_id: str) -> bool:
        """恢复快照"""
        if snapshot_id not in self.snapshots:
            raise ValueError(f"Snapshot not found: {snapshot_id}")

        snapshot = self.snapshots[snapshot_id]
        snapshot_data = snapshot.state_data

        # 解压缩（如果需要）
        if snapshot_data["metadata"].get("compression"):
            # 这里需要根据实际情况处理
            pass

        self.current_state = snapshot_data["state"]
        logger.info(f"Restored snapshot: {snapshot_id}")
        return True

    async def _create_version(self):
        """创建状态版本"""
        if not self.enable_versioning:
            return

        # 计算状态哈希
        state_str = json.dumps(self.current_state, sort_keys=True, default=str)
        state_hash = hashlib.sha256(state_str.encode()).hexdigest()

        version = StateVersion(
            version_id=str(uuid.uuid4()),
            state_hash=state_hash,
            metadata={
                "task_id": self.task_id,
                "changes": len(self.change_log),
            }
        )

        self.versions.append(version)

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """获取嵌套字典值"""
        keys = path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value

    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any):
        """设置嵌套字典值"""
        keys = path.split(".")
        current = data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "partitions": self.partition_manager.get_partition_stats(),
            "change_log_size": len(self.change_log),
            "versions_count": len(self.versions),
            "snapshots_count": len(self.snapshots),
            "current_state_size": len(str(self.current_state)),
        }

    def get_history(self, limit: int = 10) -> List[StateChange]:
        """获取变更历史"""
        return list(self.change_log)[-limit:]


# ============================================================================
# 6. 状态存储后端
# ============================================================================

class StateStorageBackend(ABC):
    """状态存储后端基类"""

    @abstractmethod
    async def save(self, task_id: str, state: Dict[str, Any]):
        """保存状态"""
        pass

    @abstractmethod
    async def load(self, task_id: str) -> Optional[Dict[str, Any]]:
        """加载状态"""
        pass

    @abstractmethod
    async def delete(self, task_id: str):
        """删除状态"""
        pass


class MemoryStateBackend(StateStorageBackend):
    """内存状态存储后端"""

    def __init__(self):
        self.storage: Dict[str, Dict[str, Any]] = {}

    async def save(self, task_id: str, state: Dict[str, Any]):
        """保存状态"""
        self.storage[task_id] = state.copy()

    async def load(self, task_id: str) -> Optional[Dict[str, Any]]:
        """加载状态"""
        return self.storage.get(task_id)

    async def delete(self, task_id: str):
        """删除状态"""
        self.storage.pop(task_id, None)


class FileStateBackend(StateStorageBackend):
    """文件状态存储后端"""

    def __init__(self, storage_dir: str = "./state_storage"):
        self.storage_dir = storage_dir
        import os
        os.makedirs(storage_dir, exist_ok=True)

    async def save(self, task_id: str, state: Dict[str, Any]):
        """保存状态"""
        import os
        file_path = os.path.join(self.storage_dir, f"{task_id}.json")
        with open(file_path, 'w') as f:
            json.dump(state, f, indent=2, default=str)

    async def load(self, task_id: str) -> Optional[Dict[str, Any]]:
        """加载状态"""
        import os
        file_path = os.path.join(self.storage_dir, f"{task_id}.json")
        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r') as f:
            return json.load(f)

    async def delete(self, task_id: str):
        """删除状态"""
        import os
        file_path = os.path.join(self.storage_dir, f"{task_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)


# ============================================================================
# 7. 使用示例
# ============================================================================

async def example_advanced_state():
    """高级状态管理示例"""

    # 1. 创建状态管理器
    state_manager = AdvancedStateManager(
        task_id="task_001",
        enable_versioning=True,
        enable_compression=True
    )

    # 2. 设置初始状态
    print("\n=== 设置初始状态 ===")
    await state_manager.set_state("task_id", "task_001")
    await state_manager.set_state("status", "processing")
    await state_manager.set_state("progress", 0)
    await state_manager.set_state("metadata.author", "Claude")
    await state_manager.set_state("metadata.version", 1)

    # 3. 批量更新状态
    print("\n=== 批量更新状态 ===")
    await state_manager.update_state({
        "progress": 25,
        "current_node": "parse_pdf",
        "nodes_completed": ["initialize"],
        "error": None,
    })

    # 4. 验证状态
    print("\n=== 验证状态 ===")
    errors = await state_manager.validate_state()
    if errors:
        print(f"验证错误: {errors}")
    else:
        print("状态验证通过")

    # 5. 创建快照
    print("\n=== 创建快照 ===")
    snapshot_id = await state_manager.create_snapshot("checkpoint_25_percent")
    print(f"快照ID: {snapshot_id}")

    # 6. 继续处理
    print("\n=== 继续处理 ===")
    await state_manager.update_state({
        "progress": 50,
        "current_node": "split_markdown",
        "nodes_completed": ["initialize", "parse_pdf"],
    })

    # 7. 创建另一个快照
    print("\n=== 创建快照 ===")
    snapshot_id2 = await state_manager.create_snapshot("checkpoint_50_percent")

    # 8. 恢复快照
    print("\n=== 恢复快照 ===")
    await state_manager.restore_snapshot(snapshot_id)
    print("恢复到25%进度")

    # 9. 合并状态
    print("\n=== 合并状态 ===")
    other_state = {
        "additional_info": "Merged data",
        "tags": ["important", "reviewed"]
    }
    await state_manager.merge_state(other_state, strategy="merge")

    # 10. 显示统计信息
    print("\n=== 统计信息 ===")
    stats = state_manager.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")

    # 11. 显示变更历史
    print("\n=== 变更历史 ===")
    history = state_manager.get_history(limit=5)
    for change in history:
        print(f"{change.timestamp.strftime('%H:%M:%S')} - "
              f"{change.operation.value}: {change.field_path}")

    # 12. 分区管理示例
    print("\n=== 分区管理 ===")
    partition_manager = state_manager.partition_manager

    # 获取不同分区
    task_partition = partition_manager.get_partition("task")
    task_partition.set("title", "Example Task")
    task_partition.set("description", "This is a test task")

    # 显示分区统计
    partition_stats = partition_manager.get_partition_stats()
    print("分区统计:")
    for name, stats in partition_stats.items():
        print(f"  {name}: {stats}")


# ============================================================================
# 8. 高级功能：状态迁移
# ============================================================================

class StateMigrationManager:
    """状态迁移管理器

    管理系统状态的迁移和版本升级。
    """

    def __init__(self):
        self.migrations: Dict[str, Callable] = {}

    def register_migration(self, version: str, migration_func: Callable):
        """注册迁移函数"""
        self.migrations[version] = migration_func
        logger.info(f"Registered migration for version {version}")

    async def migrate(self, state: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
        """执行状态迁移"""
        current_version = from_version

        while current_version != to_version:
            if current_version not in self.migrations:
                raise ValueError(f"No migration found for version {current_version}")

            migration_func = self.migrations[current_version]
            state = await migration_func(state)
            logger.info(f"Migrated from {current_version} to next version")

            # 更新版本（这里需要根据实际版本规划调整）
            current_version = self._get_next_version(current_version)

        return state

    def _get_next_version(self, version: str) -> str:
        """获取下一个版本（简化实现）"""
        parts = version.split(".")
        if len(parts) == 2:
            major, minor = parts
            return f"{major}.{int(minor) + 1}"
        return version


# ============================================================================
# 9. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_advanced_state())
