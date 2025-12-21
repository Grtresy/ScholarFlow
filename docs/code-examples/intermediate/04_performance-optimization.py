#!/usr/bin/env python3
"""
高级代码示例4: 性能优化技术
============================

本示例展示各种性能优化技术，包括：
- 异步并发控制
- 内存池管理
- 连接池复用
- 缓存策略
- 数据流优化
- 资源限制
- 性能监控

作者: Claude Code
版本: 1.0
"""

import asyncio
import logging
from typing import (
    TypedDict, List, Optional, Dict, Any, Callable,
    Awaitable, Set, Union, Generic, TypeVar
)
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import time
import weakref
from collections import deque, defaultdict
import resource
import psutil
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import aiofiles
import aiofiles.os
import pickle
import gzip

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 异步并发控制器
# ============================================================================

class ConcurrencyController:
    """异步并发控制器

    智能控制并发数量，避免资源过载。
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        max_memory_mb: int = 512,
        max_cpu_percent: float = 80.0
    ):
        self.max_concurrent = max_concurrent
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent

        self.active_tasks: Set[asyncio.Task] = set()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.stats = {
            "tasks_executed": 0,
            "tasks_rejected": 0,
            "average_wait_time": 0.0,
        }

    async def acquire(self) -> bool:
        """获取执行许可"""

        # 检查系统资源
        if not self._check_system_resources():
            self.stats["tasks_rejected"] += 1
            return False

        # 等待信号量
        start_time = time.time()
        await self.semaphore.acquire()

        # 创建任务跟踪
        task = asyncio.current_task()
        self.active_tasks.add(task)

        # 更新统计
        wait_time = time.time() - start_time
        self._update_wait_time_stats(wait_time)

        return True

    def release(self):
        """释放许可"""

        task = asyncio.current_task()
        self.active_tasks.discard(task)

        self.semaphore.release()

    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """执行函数（带并发控制）"""

        if not await self.acquire():
            raise Exception("System resources exceeded, task rejected")

        try:
            self.stats["tasks_executed"] += 1
            return await func(*args, **kwargs)
        finally:
            self.release()

    def _check_system_resources(self) -> bool:
        """检查系统资源"""

        # 检查内存
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_gb = memory.available / (1024**3)

        if memory_percent > 90 or memory_available_gb < 0.5:
            logger.warning(f"Memory usage too high: {memory_percent}%")
            return False

        # 检查CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        if cpu_percent > self.max_cpu_percent:
            logger.warning(f"CPU usage too high: {cpu_percent}%")
            return False

        # 检查并发数
        if len(self.active_tasks) >= self.max_concurrent:
            logger.warning(f"Max concurrent tasks reached: {self.max_concurrent}")
            return False

        return True

    def _update_wait_time_stats(self, wait_time: float):
        """更新等待时间统计"""
        current_avg = self.stats["average_wait_time"]
        total_tasks = self.stats["tasks_executed"]

        # 增量更新平均值
        self.stats["average_wait_time"] = (
            (current_avg * (total_tasks - 1) + wait_time) / total_tasks
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "active_tasks": len(self.active_tasks),
            "max_concurrent": self.max_concurrent,
            "memory_usage_mb": psutil.Process().memory_info().rss / (1024**2),
            "cpu_percent": psutil.cpu_percent(),
        }


# ============================================================================
# 2. 内存池管理
# ============================================================================

T = TypeVar('T')


class MemoryPool(Generic[T]):
    """内存池

    重用对象以减少GC压力。
    """

    def __init__(self, create_func: Callable[[], T], reset_func: Callable[[T], None], max_size: int = 100):
        self.create_func = create_func
        self.reset_func = reset_func
        self.max_size = max_size

        self._pool: deque[T] = deque(maxlen=max_size)
        self._all_objects: Set[T] = set()  # 使用弱引用跟踪所有对象
        self.stats = {
            "created": 0,
            "reused": 0,
            "total_allocated": 0,
        }

    def acquire(self) -> T:
        """获取对象"""
        if self._pool:
            obj = self._pool.popleft()
            self.stats["reused"] += 1
            return obj
        else:
            obj = self.create_func()
            self._all_objects.add(obj)
            self.stats["created"] += 1
            self.stats["total_allocated"] += 1
            return obj

    def release(self, obj: T):
        """释放对象"""
        try:
            # 重置对象状态
            self.reset_func(obj)

            # 添加回池中
            if len(self._pool) < self.max_size:
                self._pool.append(obj)

        except Exception as e:
            logger.warning(f"Failed to release object to pool: {e}")

    def clear(self):
        """清空池"""
        self._pool.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "pool_size": len(self._pool),
            "max_size": self.max_size,
            "reuse_rate": self.stats["reused"] / max(self.stats["total_allocated"], 1),
        }


# 示例：数据缓冲区池
@dataclass
class DataBuffer:
    """数据缓冲区"""
    data: bytearray = field(default_factory=bytearray)
    size: int = 0

    def clear(self):
        """清空缓冲区"""
        self.data.clear()
        self.size = 0

    def write(self, data: bytes):
        """写入数据"""
        self.data.extend(data)
        self.size = len(self.data)

    def read(self, size: int) -> bytes:
        """读取数据"""
        result = bytes(self.data[:size])
        del self.data[:size]
        self.size = len(self.data)
        return result


# ============================================================================
# 3. 连接池管理
# ============================================================================

@dataclass
class Connection:
    """连接对象"""
    conn_id: str
    is_active: bool = True
    last_used: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConnectionPool:
    """连接池

    管理数据库或网络连接的复用。
    """

    def __init__(
        self,
        create_connection: Callable[[], Connection],
        validate_connection: Callable[[Connection], bool],
        max_size: int = 20,
        idle_timeout: int = 300
    ):
        self.create_connection = create_connection
        self.validate_connection = validate_connection
        self.max_size = max_size
        self.idle_timeout = idle_timeout

        self._available: deque[Connection] = deque(maxlen=max_size)
        self._in_use: Set[Connection] = set()
        self._lock = asyncio.Lock()

        self.stats = {
            "connections_created": 0,
            "connections_reused": 0,
            "connections_failed": 0,
            "total_wait_time": 0.0,
        }

    async def acquire(self) -> Connection:
        """获取连接"""
        async with self._lock:
            start_time = time.time()

            # 查找可用连接
            while self._available:
                conn = self._available.popleft()

                # 检查连接是否有效
                if self._is_connection_valid(conn):
                    self._in_use.add(conn)
                    wait_time = time.time() - start_time
                    self.stats["total_wait_time"] += wait_time
                    return conn

            # 创建新连接
            if len(self._in_use) + len(self._available) < self.max_size:
                conn = self.create_connection()
                if self.validate_connection(conn):
                    self._in_use.add(conn)
                    self.stats["connections_created"] += 1
                    wait_time = time.time() - start_time
                    self.stats["total_wait_time"] += wait_time
                    return conn
                else:
                    self.stats["connections_failed"] += 1
                    raise Exception("Failed to create valid connection")

            raise Exception("Connection pool exhausted")

    async def release(self, conn: Connection):
        """释放连接"""
        async with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)

                # 检查连接是否仍然有效
                if self._is_connection_valid(conn):
                    self._available.append(conn)
                    self.stats["connections_reused"] += 1

    def _is_connection_valid(self, conn: Connection) -> bool:
        """检查连接是否有效"""

        # 检查是否标记为非活跃
        if not conn.is_active:
            return False

        # 检查空闲超时
        idle_time = (datetime.now() - conn.last_used).total_seconds()
        if idle_time > self.idle_timeout:
            return False

        # 验证连接
        if not self.validate_connection(conn):
            return False

        return True

    async def cleanup(self):
        """清理无效连接"""
        async with self._lock:
            # 清理无效连接
            valid_available = deque(maxlen=self.max_size)
            while self._available:
                conn = self._available.popleft()
                if self._is_connection_valid(conn):
                    valid_available.append(conn)

            self._available = valid_available

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "available": len(self._available),
            "in_use": len(self._in_use),
            "total": len(self._available) + len(self._in_use),
            "max_size": self.max_size,
            "average_wait_time": (
                self.stats["total_wait_time"] / max(self.stats["connections_created"], 1)
            ),
            "reuse_rate": (
                self.stats["connections_reused"] / max(
                    self.stats["connections_created"], 1
                )
            ),
        }


# ============================================================================
# 4. 智能缓存
# ============================================================================

class SmartCache:
    """智能缓存

    支持多级缓存、LRU淘汰和压缩。
    """

    def __init__(
        self,
        max_memory_mb: int = 128,
        max_items: int = 1000,
        enable_compression: bool = True,
        compression_threshold: int = 1024
    ):
        self.max_memory = max_memory_mb * 1024 * 1024
        self.max_items = max_items
        self.enable_compression = enable_compression
        self.compression_threshold = compression_threshold

        self._cache: Dict[str, Any] = {}
        self._access_order: deque = deque(maxlen=max_items)
        self._sizes: Dict[str, int] = {}
        self._access_count: Dict[str, int] = defaultdict(int)

        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "compressions": 0,
            "total_size": 0,
        }

    def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        if key not in self._cache:
            self.stats["misses"] += 1
            return None

        # 更新访问信息
        self._access_order.append(key)
        self._access_count[key] += 1
        self.stats["hits"] += 1

        value = self._cache[key]

        # 解压缩（如果需要）
        if isinstance(value, bytes) and value.startswith(b"COMPRESSED:"):
            self.stats["compressions"] += 1
            compressed_data = value[10:]  # 移除前缀
            value = gzip.decompress(compressed_data)

        return value

    def set(self, key: str, value: Any) -> None:
        """设置缓存项"""

        # 计算大小
        size = self._calculate_size(value)

        # 检查内存限制
        if size > self.max_memory:
            logger.warning(f"Item too large for cache: {size} bytes")
            return

        # 检查是否需要淘汰
        while (
            len(self._cache) >= self.max_items
            or self.stats["total_size"] + size > self.max_memory
        ):
            self._evict_lru()

        # 压缩大对象
        if self.enable_compression and size > self.compression_threshold:
            compressed = gzip.compress(pickle.dumps(value))
            value = b"COMPRESSED:" + compressed
            self.stats["compressions"] += 1

        # 设置缓存
        self._cache[key] = value
        self._access_order.append(key)
        self._access_count[key] = 1
        self._sizes[key] = size
        self.stats["total_size"] += size

    def _calculate_size(self, value: Any) -> int:
        """计算对象大小"""
        return len(pickle.dumps(value))

    def _evict_lru(self):
        """淘汰最少使用的项"""
        if not self._access_order:
            return

        # 获取最少使用的键
        key = self._access_order[0]

        # 从缓存中移除
        del self._cache[key]
        self._access_order.popleft()
        del self._access_count[key]
        removed_size = self._sizes.pop(key, 0)
        self.stats["total_size"] -= removed_size
        self.stats["evictions"] += 1

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._access_order.clear()
        self._sizes.clear()
        self.stats["total_size"] = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_requests = self.stats["hits"] + self.stats["misses"]

        return {
            **self.stats,
            "hit_rate": self.stats["hits"] / max(total_requests, 1),
            "items": len(self._cache),
            "total_requests": total_requests,
            "memory_usage_mb": self.stats["total_size"] / (1024 * 1024),
        }


# ============================================================================
# 5. 流式数据处理器
# ============================================================================

class StreamingProcessor:
    """流式数据处理器

    高效处理大文件或数据流。
    """

    def __init__(
        self,
        chunk_size: int = 8192,
        buffer_pool: Optional[MemoryPool[DataBuffer]] = None
    ):
        self.chunk_size = chunk_size
        self.buffer_pool = buffer_pool or MemoryPool(
            create_func=lambda: DataBuffer(),
            reset_func=lambda b: b.clear(),
            max_size=10
        )

        self.stats = {
            "bytes_processed": 0,
            "chunks_processed": 0,
            "average_throughput": 0.0,
        }

    async def process_file(
        self,
        input_path: str,
        output_path: str,
        processor_func: Callable[[bytes], bytes]
    ) -> None:
        """流式处理文件"""

        start_time = time.time()

        async with aiofiles.open(input_path, 'rb') as infile, \
                   aiofiles.open(output_path, 'wb') as outfile:

            # 获取缓冲区
            buffer = self.buffer_pool.acquire()

            try:
                while True:
                    # 读取数据块
                    chunk = await infile.read(self.chunk_size)

                    if not chunk:
                        break

                    # 处理数据
                    processed = processor_func(chunk)

                    # 写入输出
                    await outfile.write(processed)

                    # 更新统计
                    self.stats["bytes_processed"] += len(chunk)
                    self.stats["chunks_processed"] += 1

                    # 更新吞吐量
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 0:
                        self.stats["average_throughput"] = (
                            self.stats["bytes_processed"] / elapsed_time
                        )

            finally:
                # 释放缓冲区
                self.buffer_pool.release(buffer)

    async def batch_process(
        self,
        items: List[Any],
        batch_size: int,
        process_func: Callable[[List[Any]], List[Any]]
    ) -> List[Any]:
        """批量流式处理"""

        results = []
        buffer = self.buffer_pool.acquire()

        try:
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                processed = await asyncio.get_event_loop().run_in_executor(
                    None, process_func, batch
                )
                results.extend(processed)

        finally:
            self.buffer_pool.release(buffer)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "throughput_mbps": self.stats["average_throughput"] / (1024 * 1024),
        }


# ============================================================================
# 6. 性能监控器
# ============================================================================

class PerformanceMonitor:
    """性能监控器

    实时监控系统性能指标。
    """

    def __init__(self, sample_interval: float = 1.0):
        self.sample_interval = sample_interval
        self.metrics_history: deque = deque(maxlen=3600)  # 保存1小时数据
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None

        self.metrics = {
            "cpu_percent": 0.0,
            "memory_usage_mb": 0.0,
            "memory_percent": 0.0,
            "disk_io_read": 0.0,
            "disk_io_write": 0.0,
            "network_io_sent": 0.0,
            "network_io_recv": 0.0,
            "active_tasks": 0,
            "event_loop_latency": 0.0,
        }

    async def start(self):
        """开始监控"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """停止监控"""
        self.is_monitoring = False

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self):
        """监控循环"""
        process = psutil.Process()

        while self.is_monitoring:
            try:
                # 收集指标
                self.metrics["cpu_percent"] = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory()
                self.metrics["memory_usage_mb"] = process.memory_info().rss / (1024 * 1024)
                self.metrics["memory_percent"] = memory.percent

                # IO统计
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    self.metrics["disk_io_read"] = disk_io.read_bytes / (1024 * 1024)
                    self.metrics["disk_io_write"] = disk_io.write_bytes / (1024 * 1024)

                network_io = psutil.net_io_counters()
                if network_io:
                    self.metrics["network_io_sent"] = network_io.bytes_sent / (1024 * 1024)
                    self.metrics["network_io_recv"] = network_io.bytes_recv / (1024 * 1024)

                # 任务统计
                self.metrics["active_tasks"] = len(asyncio.all_tasks())

                # 事件循环延迟
                start = time.time()
                await asyncio.sleep(0)
                self.metrics["event_loop_latency"] = (time.time() - start) * 1000

                # 保存历史
                self.metrics_history.append({
                    "timestamp": time.time(),
                    "metrics": self.metrics.copy(),
                })

                await asyncio.sleep(self.sample_interval)

            except Exception as e:
                logger.error(f"Performance monitoring error: {e}", exc_info=True)
                await asyncio.sleep(self.sample_interval)

    def get_current_metrics(self) -> Dict[str, float]:
        """获取当前指标"""
        return self.metrics.copy()

    def get_historical_metrics(self, duration_seconds: int) -> List[Dict[str, Any]]:
        """获取历史指标"""
        cutoff_time = time.time() - duration_seconds

        return [
            data for data in self.metrics_history
            if data["timestamp"] > cutoff_time
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.metrics_history:
            return {}

        metrics_data = [data["metrics"] for data in self.metrics_history]

        # 计算平均值
        avg_metrics = {}
        for metric_name in self.metrics.keys():
            values = [m[metric_name] for m in metrics_data if metric_name in m]
            if values:
                avg_metrics[f"avg_{metric_name}"] = sum(values) / len(values)

        return {
            "sample_count": len(self.metrics_history),
            "duration_seconds": (
                self.metrics_history[-1]["timestamp"] - self.metrics_history[0]["timestamp"]
                if len(self.metrics_history) > 1 else 0
            ),
            "average_metrics": avg_metrics,
            "current_metrics": self.metrics,
        }


# ============================================================================
# 7. 性能优化示例
# ============================================================================

async def example_performance_optimization():
    """性能优化示例"""

    print("=== Performance Optimization Example ===\n")

    # 1. 演示并发控制
    print("1. Concurrency Control")
    controller = ConcurrencyController(max_concurrent=5)

    async def cpu_intensive_task(task_id: int):
        """CPU密集型任务"""
        await asyncio.sleep(0.1)  # 模拟处理
        return f"Task {task_id} completed"

    tasks = []
    for i in range(10):
        task = controller.execute(cpu_intensive_task, i)
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    print(f"Executed {len(results)} tasks")
    print(f"Controller stats: {controller.get_stats()}\n")

    # 2. 演示内存池
    print("2. Memory Pool")
    buffer_pool = MemoryPool(
        create_func=lambda: DataBuffer(),
        reset_func=lambda b: b.clear(),
        max_size=5
    )

    buffers = []
    for i in range(10):
        buf = buffer_pool.acquire()
        buf.write(f"Data {i}".encode())
        buffers.append(buf)

    for buf in buffers:
        buffer_pool.release(buf)

    print(f"Buffer pool stats: {buffer_pool.get_stats()}\n")

    # 3. 演示智能缓存
    print("3. Smart Cache")
    cache = SmartCache(max_items=100)

    # 缓存数据
    cache.set("key1", "value1")
    cache.set("key2", "x" * 10000)  # 大对象

    # 检索数据
    print(f"Cache hit key1: {cache.get('key1')}")
    print(f"Cache miss key3: {cache.get('key3')}")
    print(f"Cache stats: {cache.get_stats()}\n")

    # 4. 演示流式处理
    print("4. Streaming Processing")
    processor = StreamingProcessor(chunk_size=1024)

    # 创建测试文件
    test_data = b"x" * 100000  # 100KB
    with open("/tmp/test_input.bin", "wb") as f:
        f.write(test_data)

    # 流式处理
    await processor.process_file(
        "/tmp/test_input.bin",
        "/tmp/test_output.bin",
        lambda chunk: chunk.upper()
    )

    print(f"Processor stats: {processor.get_stats()}\n")

    # 5. 演示性能监控
    print("5. Performance Monitoring")
    monitor = PerformanceMonitor(sample_interval=0.5)

    await monitor.start()

    # 运行一些任务
    await asyncio.gather(*[cpu_intensive_task(i) for i in range(20)])

    # 等待监控收集数据
    await asyncio.sleep(2)

    stats = monitor.get_statistics()
    print(f"Performance stats: {json.dumps(stats, indent=2)}")

    await monitor.stop()


# ============================================================================
# 8. 高级功能：自适应限流
# ============================================================================

class AdaptiveRateLimiter:
    """自适应限流器

    根据系统负载动态调整限流速率。
    """

    def __init__(
        self,
        initial_rate: int = 10,
        min_rate: int = 1,
        max_rate: int = 100,
        adaptation_factor: float = 1.2
    ):
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.adaptation_factor = adaptation_factor

        self.request_times: deque = deque(maxlen=100)
        self.success_times: deque = deque(maxlen=100)
        self.failure_times: deque = deque(maxlen=100)

    async def acquire(self) -> bool:
        """获取执行许可"""

        now = time.time()
        self.request_times.append(now)

        # 检查是否超过当前速率
        recent_requests = [
            t for t in self.request_times
            if now - t < 1.0
        ]

        if len(recent_requests) > self.current_rate:
            return False

        return True

    def record_success(self):
        """记录成功"""
        self.success_times.append(time.time())

    def record_failure(self):
        """记录失败"""
        self.failure_times.append(time.time())

    async def adapt(self):
        """自适应调整速率"""

        now = time.time()

        # 计算成功率
        recent_successes = [
            t for t in self.success_times
            if now - t < 10.0
        ]
        recent_failures = [
            t for t in self.failure_times
            if now - t < 10.0
        ]

        total_recent = len(recent_successes) + len(recent_failures)

        if total_recent < 10:  # 数据不足
            return

        success_rate = len(recent_successes) / total_recent

        # 调整速率
        if success_rate < 0.5:  # 成功率低，降低速率
            self.current_rate = max(
                self.min_rate,
                int(self.current_rate / self.adaptation_factor)
            )
        elif success_rate > 0.9:  # 成功率高，提高速率
            self.current_rate = min(
                self.max_rate,
                int(self.current_rate * self.adaptation_factor)
            )


# ============================================================================
# 9. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_performance_optimization())
