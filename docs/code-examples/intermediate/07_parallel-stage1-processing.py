#!/usr/bin/env python3
"""
高级代码示例7: 并行Stage1处理系统
===================================

本示例展示如何构建一个高性能的并行处理系统，
用于ScholarFlow的Stage1阶段（并行生成多个章节的大纲）。

功能特性:
- 动态工作负载分配
- 智能任务调度
- 内存管理
- 进度监控
- 失败恢复
- 结果聚合
- 性能优化

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
import uuid
from collections import defaultdict, deque
import heapq
import time
import psutil
import gc

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


class ChunkType(Enum):
    """分块类型"""
    INTRODUCTION = "introduction"
    METHODOLOGY = "methodology"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    OTHER = "other"


@dataclass
class ProcessingChunk:
    """处理分块"""
    chunk_id: str
    content: str
    chunk_type: ChunkType
    estimated_tokens: int
    priority: int
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Stage1Task:
    """Stage1任务"""
    task_id: str
    chunk: ProcessingChunk
    style: str  # academic/popular/business
    max_retries: int = 3
    timeout: float = 120.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Stage1Result:
    """Stage1结果"""
    task_id: str
    chunk_id: str
    outline: str
    tokens_used: int
    processing_time: float
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParallelJob:
    """并行作业"""
    job_id: str
    tasks: List[Stage1Task]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    results: List[Stage1Result] = field(default_factory=list)
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 2. 内存管理器
# ============================================================================

class MemoryManager:
    """内存管理器

    监控系统内存使用，防止OOM错误。
    """

    def __init__(self, max_memory_percent: float = 80.0):
        self.max_memory_percent = max_memory_percent
        self.gc_threshold = 500  # 触发GC的对象数量
        self.last_gc_time = time.time()

    def check_memory(self) -> Dict[str, float]:
        """检查内存使用"""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent,
        }

    async def ensure_memory(self, required_mb: int = 100) -> bool:
        """确保有足够内存"""
        memory = self.check_memory()
        available_mb = memory["available"] / (1024 * 1024)

        if available_mb < required_mb:
            logger.warning(f"Low memory: {available_mb:.1f}MB available, need {required_mb}MB")
            await self.cleanup()
            return False

        return True

    async def cleanup(self):
        """清理内存"""
        logger.info("Performing memory cleanup...")

        # 强制垃圾回收
        collected = gc.collect()
        logger.info(f"Garbage collected {collected} objects")

        self.last_gc_time = time.time()

        # 检查清理后的内存
        memory = self.check_memory()
        logger.info(f"Memory usage after cleanup: {memory['percent']:.1f}%")


# ============================================================================
# 3. 智能任务调度器
# ============================================================================

class IntelligentTaskScheduler:
    """智能任务调度器

    根据任务大小、类型和系统负载动态分配任务。
    """

    def __init__(
        self,
        max_workers: int = 4,
        memory_manager: Optional[MemoryManager] = None
    ):
        self.max_workers = max_workers
        self.memory_manager = memory_manager or MemoryManager()
        self.task_queue: List[Stage1Task] = []
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.completed_tasks: List[Stage1Result] = []
        self.failed_tasks: List[Stage1Task] = []

        # 负载监控
        self.cpu_samples = deque(maxlen=100)
        self.memory_samples = deque(maxlen=100)

    def _calculate_task_priority(self, task: Stage1Task) -> float:
        """计算任务优先级"""
        chunk = task.chunk

        # 基础优先级
        base_priority = chunk.priority

        # 根据类型调整
        type_weights = {
            ChunkType.INTRODUCTION: 1.5,  # 引言优先
            ChunkType.CONCLUSION: 1.3,    # 结论优先
            ChunkType.METHODOLOGY: 1.1,
            ChunkType.RESULTS: 1.0,
            ChunkType.DISCUSSION: 0.9,
            ChunkType.OTHER: 0.8,
        }
        type_multiplier = type_weights.get(chunk.chunk_type, 1.0)

        # 根据令牌数调整（大任务优先级稍低）
        size_factor = max(0.5, 1.0 - chunk.estimated_tokens / 10000)

        return base_priority * type_multiplier * size_factor

    def add_task(self, task: Stage1Task):
        """添加任务"""
        priority = self._calculate_task_priority(task)
        heapq.heappush(self.task_queue, (-priority, time.time(), task))
        logger.info(f"Added task {task.task_id} with priority {priority:.2f}")

    async def schedule_task(self, task: Stage1Task) -> Stage1Result:
        """调度单个任务"""
        # 检查内存
        if not await self.memory_manager.ensure_memory(100):
            logger.warning("Low memory, proceeding anyway...")

        start_time = time.time()

        try:
            # 模拟LLM处理
            await asyncio.sleep(task.timeout / 4)  # 实际是调用LLM

            # 模拟成功率 (95%)
            import random
            if random.random() < 0.95:
                result = Stage1Result(
                    task_id=task.task_id,
                    chunk_id=task.chunk.chunk_id,
                    outline=f"Generated outline for {task.chunk.chunk_type.value}",
                    tokens_used=random.randint(200, 800),
                    processing_time=time.time() - start_time,
                    success=True
                )
                logger.info(f"Task {task.task_id} completed successfully")
                return result
            else:
                raise Exception("Simulated processing error")

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            return Stage1Result(
                task_id=task.task_id,
                chunk_id=task.chunk.chunk_id,
                outline="",
                tokens_used=0,
                processing_time=time.time() - start_time,
                success=False,
                error=str(e)
            )

    async def run_parallel(self, tasks: List[Stage1Task]) -> List[Stage1Result]:
        """并行运行任务"""
        # 添加所有任务
        for task in tasks:
            self.add_task(task)

        # 创建工作池
        semaphore = asyncio.Semaphore(self.max_workers)
        results = []

        async def worker():
            while self.task_queue:
                # 获取任务
                if not self.task_queue:
                    break

                priority, added_time, task = heapq.heappop(self.task_queue)

                async with semaphore:
                    result = await self.schedule_task(task)
                    results.append(result)

        # 启动工作协程
        workers = [asyncio.create_task(worker()) for _ in range(self.max_workers)]
        await asyncio.gather(*workers)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "queue_size": len(self.task_queue),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "max_workers": self.max_workers,
            "memory_usage": self.memory_manager.check_memory(),
        }


# ============================================================================
# 4. 进度监控器
# ============================================================================

class ProgressMonitor:
    """进度监控器

    实时监控并行处理进度，提供详细的进度报告。
    """

    def __init__(self, total_tasks: int):
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.start_time = time.time()
        self.history = deque(maxlen=100)

    def update(self, completed: int = 0, failed: int = 0):
        """更新进度"""
        self.completed_tasks += completed
        self.failed_tasks += failed

        # 记录历史
        self.history.append({
            "timestamp": time.time(),
            "completed": self.completed_tasks,
            "failed": self.failed_tasks,
            "total": self.completed_tasks + self.failed_tasks,
        })

    def get_progress(self) -> Dict[str, Any]:
        """获取进度信息"""
        completed = self.completed_tasks + self.failed_tasks
        progress_percent = (completed / self.total_tasks) * 100 if self.total_tasks > 0 else 0

        # 计算ETA
        elapsed_time = time.time() - self.start_time
        if completed > 0:
            avg_time_per_task = elapsed_time / completed
            remaining_tasks = self.total_tasks - completed
            eta_seconds = remaining_tasks * avg_time_per_task
            eta = timedelta(seconds=int(eta_seconds))
        else:
            eta = None

        # 计算速度
        if len(self.history) >= 2:
            recent = list(self.history)[-5:]  # 最近5个样本
            time_diff = recent[-1]["timestamp"] - recent[0]["timestamp"]
            task_diff = recent[-1]["total"] - recent[0]["total"]
            speed = task_diff / time_diff if time_diff > 0 else 0
        else:
            speed = 0

        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "progress_percent": progress_percent,
            "elapsed_time": timedelta(seconds=int(elapsed_time)),
            "estimated_remaining": eta,
            "tasks_per_second": speed,
        }

    def print_progress(self):
        """打印进度"""
        progress = self.get_progress()
        print(
            f"\r进度: {progress['completed_tasks']}/{progress['total_tasks']} "
            f"({progress['progress_percent']:.1f}%) "
            f"速度: {progress['tasks_per_second']:.2f} tasks/s "
            f"剩余时间: {progress['estimated_remaining']}",
            end=""
        )


# ============================================================================
# 5. 结果聚合器
# ============================================================================

class ResultAggregator:
    """结果聚合器

    收集和聚合并行处理的结果。
    """

    def __init__(self, style: str):
        self.style = style
        self.results: List[Stage1Result] = []
        self.merged_outline = ""

    def add_result(self, result: Stage1Result):
        """添加结果"""
        self.results.append(result)

    def merge_results(self) -> str:
        """合并结果为统一大纲"""
        if not self.results:
            return ""

        # 按优先级排序
        sorted_results = sorted(
            self.results,
            key=lambda r: r.chunk_id  # 可以根据优先级调整
        )

        # 合并大纲
        merged_parts = []
        for result in sorted_results:
            if result.success and result.outline:
                merged_parts.append(f"\n## {result.chunk_id}\n{result.outline}")

        self.merged_outline = "\n".join(merged_parts)
        return self.merged_outline

    def get_summary(self) -> Dict[str, Any]:
        """获取聚合摘要"""
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        total_tokens = sum(r.tokens_used for r in successful)
        total_time = sum(r.processing_time for r in successful)

        return {
            "total_results": len(self.results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / max(len(self.results), 1) * 100,
            "total_tokens": total_tokens,
            "total_processing_time": total_time,
            "average_tokens_per_task": total_tokens / max(len(successful), 1),
            "average_time_per_task": total_time / max(len(successful), 1),
        }


# ============================================================================
# 6. 主并行处理系统
# ============================================================================

class ParallelStage1Processor:
    """并行Stage1处理器

    统一管理并行处理流程。
    """

    def __init__(
        self,
        max_workers: int = 4,
        style: str = "academic"
    ):
        self.max_workers = max_workers
        self.style = style
        self.scheduler = IntelligentTaskScheduler(max_workers)
        self.memory_manager = self.scheduler.memory_manager

    async def process_chunks(
        self,
        chunks: List[ProcessingChunk],
        style: Optional[str] = None
    ) -> Dict[str, Any]:
        """处理分块列表"""

        # 创建任务
        tasks = [
            Stage1Task(
                task_id=str(uuid.uuid4()),
                chunk=chunk,
                style=style or self.style
            )
            for chunk in chunks
        ]

        print(f"\n开始并行处理 {len(tasks)} 个任务 (最大并发: {self.max_workers})")

        # 创建进度监控器
        monitor = ProgressMonitor(len(tasks))

        # 开始处理
        start_time = time.time()

        # 并行执行
        results = await self.scheduler.run_parallel(tasks)

        # 更新进度
        monitor.update(completed=len([r for r in results if r.success]))
        monitor.update(failed=len([r for r in results if not r.success]))

        # 聚合结果
        aggregator = ResultAggregator(style or self.style)
        for result in results:
            aggregator.add_result(result)

        merged_outline = aggregator.merge_results()

        total_time = time.time() - start_time

        print(f"\n处理完成! 总用时: {total_time:.2f}s")

        return {
            "job_id": str(uuid.uuid4()),
            "total_tasks": len(tasks),
            "results": results,
            "merged_outline": merged_outline,
            "summary": aggregator.get_summary(),
            "stats": self.scheduler.get_stats(),
            "processing_time": total_time,
        }


# ============================================================================
# 7. 使用示例
# ============================================================================

async def example_parallel_stage1():
    """并行Stage1处理示例"""

    # 1. 创建示例分块
    chunks = [
        ProcessingChunk(
            chunk_id=f"chunk_{i:03d}",
            content=f"This is the content of chunk {i}" * 100,
            chunk_type=ChunkType.INTRODUCTION if i == 0 else ChunkType.OTHER,
            estimated_tokens=500 + i * 100,
            priority=1
        )
        for i in range(20)
    ]

    # 2. 创建处理器
    processor = ParallelStage1Processor(
        max_workers=4,
        style="academic"
    )

    # 3. 执行并行处理
    print("=== 开始并行Stage1处理 ===")
    result = await processor.process_chunks(chunks)

    # 4. 显示结果
    print("\n=== 处理结果摘要 ===")
    summary = result["summary"]
    print(f"总任务数: {summary['total_results']}")
    print(f"成功: {summary['successful']}")
    print(f"失败: {summary['failed']}")
    print(f"成功率: {summary['success_rate']:.1f}%")
    print(f"总Token数: {summary['total_tokens']}")
    print(f"总处理时间: {summary['total_processing_time']:.2f}s")
    print(f"平均每任务: {summary['average_time_per_task']:.2f}s")

    # 5. 显示统计信息
    print("\n=== 系统统计 ===")
    stats = result["stats"]
    for key, value in stats.items():
        print(f"{key}: {value}")

    # 6. 显示合并大纲预览
    print("\n=== 合并大纲预览 ===")
    outline = result["merged_outline"]
    print(outline[:500] + "..." if len(outline) > 500 else outline)

    return result


# ============================================================================
# 8. 高级功能：动态负载调整
# ============================================================================

class DynamicLoadBalancer:
    """动态负载均衡器

    根据系统负载动态调整并发数。
    """

    def __init__(self, processor: ParallelStage1Processor):
        self.processor = processor
        self.target_cpu_percent = 70.0
        self.adjustment_interval = 5  # 每5秒调整一次

    async def monitor_and_adjust(self):
        """监控并调整负载"""
        while True:
            # 获取系统负载
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            # 调整策略
            if cpu_percent > self.target_cpu_percent * 1.2:
                # 负载过高，减少工作进程
                if self.processor.max_workers > 1:
                    self.processor.max_workers -= 1
                    self.processor.scheduler.max_workers = self.processor.max_workers
                    logger.info(f"Reduced workers to {self.processor.max_workers}")

            elif cpu_percent < self.target_cpu_percent * 0.6:
                # 负载较低，增加工作进程
                if self.processor.max_workers < 8:  # 最大8个
                    self.processor.max_workers += 1
                    self.processor.scheduler.max_workers = self.processor.max_workers
                    logger.info(f"Increased workers to {self.processor.max_workers}")

            await asyncio.sleep(self.adjustment_interval)


# ============================================================================
# 9. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_parallel_stage1())
