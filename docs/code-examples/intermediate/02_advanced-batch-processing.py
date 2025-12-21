#!/usr/bin/env python3
"""
高级代码示例2: 高级批量处理系统
=================================

本示例展示如何构建一个功能完整的批量处理系统，
包括任务调度、并发控制、错误恢复、进度跟踪和结果聚合。

功能特性:
- 动态任务调度器
- 优先级队列管理
- 并发控制与限流
- 智能重试机制
- 实时进度跟踪
- 批量结果聚合
- 性能监控

作者: Claude Code
版本: 1.0
"""

import asyncio
import logging
from typing import (
    TypedDict, List, Optional, Dict, Any, Callable,
    Awaitable, Set, Union
)
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import uuid
from collections import defaultdict, deque
import heapq
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级 (数字越小优先级越高)"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class RetryStrategy(Enum):
    """重试策略"""
    FIXED_DELAY = "fixed_delay"        # 固定延迟
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # 指数退避
    LINEAR_BACKOFF = "linear_backoff"   # 线性退避
    ADAPTIVE = "adaptive"               # 自适应


@dataclass
class BatchTask:
    """批量任务"""
    task_id: str
    task_type: str
    priority: TaskPriority
    payload: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """优先级队列排序"""
        return (self.priority.value, self.created_at) < (other.priority.value, other.created_at)


@dataclass
class BatchJob:
    """批量作业"""
    job_id: str
    job_name: str
    tasks: List[BatchTask] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_tasks: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_progress(self):
        """更新进度"""
        if self.total_tasks == 0:
            self.progress = 0
        else:
            self.progress = (self.completed_tasks + self.failed_tasks) / self.total_tasks * 100


# ============================================================================
# 2. 任务处理器
# ============================================================================

class TaskProcessor:
    """任务处理器基类"""

    def __init__(self, processor_id: str):
        self.processor_id = processor_id
        self.logger = logging.getLogger(f"processor.{processor_id}")

    async def process(self, task: BatchTask) -> Dict[str, Any]:
        """处理任务 (子类实现)"""
        raise NotImplementedError

    async def validate_task(self, task: BatchTask) -> bool:
        """验证任务"""
        return True

    async def cleanup(self, task: BatchTask):
        """清理资源"""
        pass


class DataProcessingTaskProcessor(TaskProcessor):
    """数据处理任务处理器示例"""

    def __init__(self):
        super().__init__("data_processor")

    async def process(self, task: BatchTask) -> Dict[str, Any]:
        """处理数据任务"""
        self.logger.info(f"Processing task {task.task_id}")

        # 模拟处理时间
        processing_time = task.metadata.get("processing_time", 1.0)
        await asyncio.sleep(processing_time)

        # 模拟成功率 (90%)
        import random
        if random.random() < 0.9:
            return {
                "status": "success",
                "processed_records": task.payload.get("record_count", 100),
                "processing_time": processing_time,
                "output_size": task.payload.get("record_count", 100) * 1024,
            }
        else:
            raise Exception("Random processing error")


class FileProcessingTaskProcessor(TaskProcessor):
    """文件处理任务处理器示例"""

    def __init__(self):
        super().__init__("file_processor")

    async def process(self, task: BatchTask) -> Dict[str, Any]:
        """处理文件任务"""
        self.logger.info(f"Processing file task {task.task_id}")

        # 模拟文件处理
        file_path = task.payload.get("file_path")
        if not file_path:
            raise ValueError("File path is required")

        # 模拟处理
        await asyncio.sleep(0.5)

        return {
            "status": "success",
            "file_path": file_path,
            "processed_at": datetime.now().isoformat(),
            "output_path": f"{file_path}.processed",
        }


# ============================================================================
# 3. 高级批量调度器
# ============================================================================

class AdvancedBatchScheduler:
    """高级批量调度器

    功能特性:
    - 优先级队列
    - 并发控制
    - 动态限流
    - 智能重试
    - 进度跟踪
    - 性能监控
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        max_queue_size: int = 1000,
        rate_limit: Optional[int] = None
    ):
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.rate_limit = rate_limit  # 每秒任务数

        # 任务队列 (优先级队列)
        self.task_queue: List[BatchTask] = []
        self.queue_index: Dict[str, int] = {}  # 任务ID到队列索引的映射

        # 运行中的任务
        self.running_tasks: Dict[str, BatchTask] = {}
        self.running_tasks_heap: List[tuple] = []  # (priority, start_time, task_id)

        # 任务处理器
        self.processors: Dict[str, TaskProcessor] = {}

        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "retried_tasks": 0,
            "average_latency": 0.0,
            "tasks_per_second": 0.0,
        }

        # 性能监控
        self.performance_history = deque(maxlen=100)
        self.start_time = time.time()

        # 控制标志
        self.is_running = False
        self._shutdown_event = asyncio.Event()

    def register_processor(self, processor: TaskProcessor):
        """注册任务处理器"""
        self.processors[processor.processor_id] = processor
        logger.info(f"Registered processor: {processor.processor_id}")

    async def submit_task(self, task: BatchTask) -> bool:
        """提交任务"""
        if len(self.task_queue) >= self.max_queue_size:
            raise Exception("Queue is full")

        # 计算调度时间
        if self.rate_limit:
            task.scheduled_at = await self._calculate_next_available_time()
        else:
            task.scheduled_at = datetime.now()

        # 添加到队列
        heapq.heappush(self.task_queue, task)
        self.queue_index[task.task_id] = len(self.task_queue) - 1
        self.stats["total_tasks"] += 1

        logger.info(f"Task {task.task_id} submitted with priority {task.priority}")

        return True

    async def submit_batch(self, batch: BatchJob) -> str:
        """提交批量作业"""
        batch.job_id = str(uuid.uuid4())
        batch.total_tasks = len(batch.tasks)
        batch.status = TaskStatus.RUNNING
        batch.started_at = datetime.now()

        logger.info(f"Submitting batch {batch.job_id} with {batch.total_tasks} tasks")

        # 提交所有任务
        for task in batch.tasks:
            await self.submit_task(task)

        return batch.job_id

    async def start(self):
        """启动调度器"""
        self.is_running = True
        logger.info("Batch scheduler started")

        # 启动主调度循环
        asyncio.create_task(self._scheduler_loop())

        # 启动性能监控
        asyncio.create_task(self._performance_monitor())

    async def stop(self):
        """停止调度器"""
        self.is_running = False
        self._shutdown_event.set()
        logger.info("Batch scheduler stopped")

    async def _scheduler_loop(self):
        """主调度循环"""
        while self.is_running:
            try:
                # 检查是否需要调度新任务
                if (
                    len(self.running_tasks) < self.max_concurrent
                    and self.task_queue
                ):
                    await self._dispatch_tasks()

                # 检查完成的任务
                await self._check_completed_tasks()

                # 处理重试任务
                await self._process_retry_tasks()

                # 短暂休眠
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _dispatch_tasks(self):
        """分发任务"""
        while (
            len(self.running_tasks) < self.max_concurrent
            and self.task_queue
        ):
            # 获取下一个可调度的任务
            task = await self._get_next_schedulable_task()
            if not task:
                break

            # 启动任务
            await self._execute_task(task)

    async def _get_next_schedulable_task(self) -> Optional[BatchTask]:
        """获取下一个可调度的任务"""
        if not self.task_queue:
            return None

        # 检查队列头部任务是否可调度
        task = self.task_queue[0]

        # 检查是否超过速率限制
        if self.rate_limit and task.scheduled_at:
            if datetime.now() < task.scheduled_at:
                return None

        # 从队列中移除
        return heapq.heappop(self.task_queue)

    async def _execute_task(self, task: BatchTask):
        """执行任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        # 添加到运行任务
        self.running_tasks[task.task_id] = task
        heapq.heappush(
            self.running_tasks_heap,
            (task.priority.value, task.started_at, task.task_id)
        )

        # 异步执行任务
        asyncio.create_task(self._run_task(task))

    async def _run_task(self, task: BatchTask):
        """运行任务"""
        try:
            # 获取处理器
            processor = self.processors.get(task.task_type)
            if not processor:
                raise ValueError(f"No processor for task type: {task.task_type}")

            # 验证任务
            if not await processor.validate_task(task):
                raise ValueError("Task validation failed")

            # 处理任务
            result = await processor.process(task)

            # 标记成功
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result

            self.stats["completed_tasks"] += 1

        except Exception as e:
            # 处理失败
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = str(e)

            self.stats["failed_tasks"] += 1

            # 检查是否需要重试
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.RETRYING
                task.retry_count += 1
                self.stats["retried_tasks"] += 1

                # 计算重试延迟
                task.scheduled_at = await self._calculate_retry_delay(task)

                # 重新入队
                heapq.heappush(self.task_queue, task)

        finally:
            # 从运行任务中移除
            self.running_tasks.pop(task.task_id, None)

    async def _check_completed_tasks(self):
        """检查已完成的任务"""
        # 简化实现：定期清理运行任务列表
        current_time = time.time()
        expired_tasks = []

        for priority, start_time, task_id in self.running_tasks_heap:
            # 清理超时的任务记录
            if current_time - start_time > 300:  # 5分钟
                expired_tasks.append((priority, start_time, task_id))

        for item in expired_tasks:
            self.running_tasks_heap.remove(item)

    async def _process_retry_tasks(self):
        """处理重试任务"""
        # 简化实现：重试任务已在调度时处理
        pass

    async def _calculate_retry_delay(self, task: BatchTask) -> datetime:
        """计算重试延迟"""
        if task.retry_strategy == RetryStrategy.FIXED_DELAY:
            delay = task.retry_delay
        elif task.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = task.retry_delay * (2 ** task.retry_count)
        elif task.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = task.retry_delay * (task.retry_count + 1)
        else:  # ADAPTIVE
            # 根据历史成功率调整延迟
            delay = task.retry_delay * (1.5 ** task.retry_count)

        return datetime.now() + timedelta(seconds=delay)

    async def _calculate_next_available_time(self) -> datetime:
        """计算下一个可用时间 (速率限制)"""
        if not self.rate_limit:
            return datetime.now()

        # 简化实现：基于历史速率计算
        return datetime.now() + timedelta(seconds=1.0 / self.rate_limit)

    async def _performance_monitor(self):
        """性能监控"""
        while self.is_running:
            # 计算性能指标
            elapsed_time = time.time() - self.start_time
            total_tasks = self.stats["completed_tasks"] + self.stats["failed_tasks"]

            if elapsed_time > 0:
                self.stats["tasks_per_second"] = total_tasks / elapsed_time

            # 记录历史
            self.performance_history.append({
                "timestamp": time.time(),
                "running_tasks": len(self.running_tasks),
                "queue_size": len(self.task_queue),
                "completed_tasks": self.stats["completed_tasks"],
                "failed_tasks": self.stats["failed_tasks"],
                "tasks_per_second": self.stats["tasks_per_second"],
            })

            await asyncio.sleep(5)  # 每5秒监控一次

    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            "is_running": self.is_running,
            "queue_size": len(self.task_queue),
            "running_tasks": len(self.running_tasks),
            "max_concurrent": self.max_concurrent,
            "stats": self.stats.copy(),
            "performance": {
                "tasks_per_second": self.stats["tasks_per_second"],
                "success_rate": (
                    self.stats["completed_tasks"] /
                    max(self.stats["total_tasks"], 1) * 100
                ),
            },
        }


# ============================================================================
# 4. 批量作业管理器
# ============================================================================

class BatchJobManager:
    """批量作业管理器"""

    def __init__(self, scheduler: AdvancedBatchScheduler):
        self.scheduler = scheduler
        self.jobs: Dict[str, BatchJob] = {}

    async def create_job(
        self,
        job_name: str,
        task_configs: List[Dict[str, Any]]
    ) -> str:
        """创建批量作业"""
        job = BatchJob(
            job_id=str(uuid.uuid4()),
            job_name=job_name,
        )

        # 创建任务
        for config in task_configs:
            task = BatchTask(
                task_id=str(uuid.uuid4()),
                task_type=config["task_type"],
                priority=TaskPriority(config.get("priority", "NORMAL")),
                payload=config["payload"],
                max_retries=config.get("max_retries", 3),
                retry_delay=config.get("retry_delay", 1.0),
                retry_strategy=RetryStrategy(
                    config.get("retry_strategy", "EXPONENTIAL_BACKOFF")
                ),
            )
            job.tasks.append(task)

        # 保存作业
        self.jobs[job.job_id] = job

        # 提交到调度器
        await self.scheduler.submit_batch(job)

        logger.info(f"Created job {job.job_id} with {len(job.tasks)} tasks")

        return job.job_id

    async def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """获取作业状态"""
        job = self.jobs.get(job_id)
        if not job:
            return None

        # 从调度器获取最新统计
        job.completed_tasks = self.scheduler.stats["completed_tasks"]
        job.failed_tasks = self.scheduler.stats["failed_tasks"]
        job.update_progress()

        # 检查是否完成
        if job.completed_tasks + job.failed_tasks >= job.total_tasks:
            job.status = TaskStatus.COMPLETED if job.failed_tasks == 0 else TaskStatus.FAILED
            job.completed_at = datetime.now()

        return job

    async def list_jobs(self, status: Optional[TaskStatus] = None) -> List[BatchJob]:
        """列出作业"""
        jobs = list(self.jobs.values())

        if status:
            jobs = [job for job in jobs if job.status == status]

        return jobs


# ============================================================================
# 5. 使用示例
# ============================================================================

async def example_advanced_batch_processing():
    """高级批量处理示例"""

    # 1. 创建调度器
    scheduler = AdvancedBatchScheduler(
        max_concurrent=5,
        max_queue_size=100,
        rate_limit=10  # 每秒最多10个任务
    )

    # 2. 注册处理器
    scheduler.register_processor(DataProcessingTaskProcessor())
    scheduler.register_processor(FileProcessingTaskProcessor())

    # 3. 创建作业管理器
    job_manager = BatchJobManager(scheduler)

    # 4. 启动调度器
    await scheduler.start()

    try:
        # 5. 创建批量作业
        task_configs = [
            {
                "task_type": "data_processor",
                "priority": "HIGH",
                "payload": {
                    "record_count": 1000,
                    "processing_time": 0.5,
                },
                "max_retries": 3,
            },
            {
                "task_type": "data_processor",
                "priority": "NORMAL",
                "payload": {
                    "record_count": 500,
                    "processing_time": 0.3,
                },
                "max_retries": 2,
            },
            {
                "task_type": "file_processor",
                "priority": "LOW",
                "payload": {
                    "file_path": "/path/to/file1.txt",
                },
                "max_retries": 1,
            },
        ]

        job_id = await job_manager.create_job(
            job_name="Example Batch Job",
            task_configs=task_configs
        )

        print(f"Created job: {job_id}")

        # 6. 监控作业进度
        for _ in range(50):  # 监控5秒
            await asyncio.sleep(0.1)
            job = await job_manager.get_job_status(job_id)

            if job:
                print(f"\rJob Progress: {job.progress:.1f}% "
                      f"({job.completed_tasks}/{job.total_tasks} completed, "
                      f"{job.failed_tasks} failed)", end="")

            # 检查是否完成
            if job and job.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break

        print("\n")

        # 7. 显示最终结果
        job = await job_manager.get_job_status(job_id)
        if job:
            print(f"\n=== Job Summary ===")
            print(f"Job ID: {job.job_id}")
            print(f"Status: {job.status.value}")
            print(f"Total Tasks: {job.total_tasks}")
            print(f"Completed: {job.completed_tasks}")
            print(f"Failed: {job.failed_tasks}")
            print(f"Progress: {job.progress:.1f}%")

        # 8. 显示调度器统计
        print(f"\n=== Scheduler Stats ===")
        stats = scheduler.get_status()
        for key, value in stats.items():
            print(f"{key}: {value}")

    finally:
        # 9. 停止调度器
        await scheduler.stop()


# ============================================================================
# 6. 高级功能：智能负载均衡
# ============================================================================

class IntelligentLoadBalancer:
    """智能负载均衡器

    根据任务特性和系统负载动态分配任务。
    """

    def __init__(self, schedulers: List[AdvancedBatchScheduler]):
        self.schedulers = schedulers
        self.current_index = 0

    async def select_scheduler(self, task: BatchTask) -> AdvancedBatchScheduler:
        """选择最合适的调度器"""

        # 策略1: 轮询
        if task.priority == TaskPriority.LOW:
            scheduler = self.schedulers[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.schedulers)
            return scheduler

        # 策略2: 选择负载最低的
        best_scheduler = min(
            self.schedulers,
            key=lambda s: len(s.running_tasks) / s.max_concurrent
        )

        return best_scheduler

    async def submit_task(self, task: BatchTask) -> bool:
        """智能提交任务"""
        scheduler = await self.select_scheduler(task)
        return await scheduler.submit_task(task)


# ============================================================================
# 7. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_advanced_batch_processing())
