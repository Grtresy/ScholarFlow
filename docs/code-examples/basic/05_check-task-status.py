#!/usr/bin/env python3
"""
基础示例 05: 检查任务状态
学习如何查询和监控任务执行状态
"""

import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


# 示例 1: 任务状态枚举
class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    PARSING = "parsing"
    SPLITTING = "splitting"
    STAGE1_PROCESSING = "stage1_processing"
    MERGING = "merging"
    HUMAN_REVIEW = "human_review"
    STAGE2_PROCESSING = "stage2_processing"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def is_finished(self) -> bool:
        """检查是否已完成（成功或失败）"""
        return self in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]

    def is_success(self) -> bool:
        """检查是否成功完成"""
        return self == TaskStatus.COMPLETED

    def get_progress(self) -> int:
        """根据状态获取进度百分比"""
        progress_map = {
            TaskStatus.PENDING: 0,
            TaskStatus.PROCESSING: 5,
            TaskStatus.PARSING: 10,
            TaskStatus.SPLITTING: 20,
            TaskStatus.STAGE1_PROCESSING: 40,
            TaskStatus.MERGING: 60,
            TaskStatus.HUMAN_REVIEW: 70,
            TaskStatus.STAGE2_PROCESSING: 80,
            TaskStatus.RENDERING: 90,
            TaskStatus.COMPLETED: 100,
            TaskStatus.FAILED: 0,
            TaskStatus.CANCELLED: 0,
        }
        return progress_map.get(self, 0)


# 示例 2: 任务状态数据类
class TaskInfo:
    """任务信息"""
    def __init__(self, task_id: str, status: str, data: Optional[Dict[str, Any]] = None):
        self.task_id = task_id
        self.status = TaskStatus(status)
        self.data = data or {}
        self.created_at = self.data.get('created_at', datetime.now().isoformat())
        self.updated_at = self.data.get('updated_at', datetime.now().isoformat())
        self.progress = self.data.get('progress_percentage', self.status.get_progress())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'status': self.status.value,
            'progress': self.progress,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            **self.data
        }

    def print_status(self):
        """打印状态"""
        status_icon = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.PROCESSING: "⚙️",
            TaskStatus.PARSING: "📄",
            TaskStatus.SPLITTING: "✂️",
            TaskStatus.STAGE1_PROCESSING: "🧠",
            TaskStatus.MERGING: "🔗",
            TaskStatus.HUMAN_REVIEW: "👤",
            TaskStatus.STAGE2_PROCESSING: "🎨",
            TaskStatus.RENDERING: "🎬",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.CANCELLED: "⛔",
        }.get(self.status, "❓")

        print(f"\n{status_icon} 任务: {self.task_id}")
        print(f"  状态: {self.status.value}")
        print(f"  进度: {self.progress}%")
        print(f"  创建: {self.created_at}")
        print(f"  更新: {self.updated_at}")

        # 显示额外信息
        if self.data:
            if 'current_node' in self.data:
                print(f"  当前节点: {self.data['current_node']}")
            if 'error_message' in self.data:
                print(f"  错误: {self.data['error_message']}")
            if 'output_path' in self.data:
                print(f"  输出: {self.data['output_path']}")


# 示例 3: 模拟 API 客户端
class MockAPIClient:
    """模拟 API 客户端"""

    def __init__(self):
        # 模拟任务数据
        self.tasks = {
            "task-001": {
                "task_id": "task-001",
                "status": "completed",
                "progress_percentage": 100,
                "created_at": "2025-01-01T10:00:00",
                "updated_at": "2025-01-01T10:05:00",
                "output_path": "outputs/task-001.pptx",
            },
            "task-002": {
                "task_id": "task-002",
                "status": "stage1_processing",
                "progress_percentage": 45,
                "created_at": "2025-01-01T10:02:00",
                "updated_at": "2025-01-01T10:03:30",
                "current_node": "stage1_process",
                "chunks_processed": 3,
                "total_chunks": 6,
            },
            "task-003": {
                "task_id": "task-003",
                "status": "human_review",
                "progress_percentage": 70,
                "created_at": "2025-01-01T10:01:00",
                "updated_at": "2025-01-01T10:04:00",
                "current_node": "human_review",
                "merged_outline": "已生成大纲，等待审核",
            },
            "task-004": {
                "task_id": "task-004",
                "status": "failed",
                "progress_percentage": 0,
                "created_at": "2025-01-01T10:00:00",
                "updated_at": "2025-01-01T10:01:00",
                "error_message": "PDF 文件格式不支持",
            },
        }

    async def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务状态"""
        await asyncio.sleep(0.1)  # 模拟网络延迟

        task_data = self.tasks.get(task_id)
        if task_data:
            return TaskInfo(task_id, task_data['status'], task_data)
        return None

    async def list_tasks(self, status: Optional[str] = None) -> list:
        """列出所有任务"""
        await asyncio.sleep(0.1)

        tasks = []
        for task_id, task_data in self.tasks.items():
            if status is None or task_data['status'] == status:
                tasks.append(TaskInfo(task_id, task_data['status'], task_data))
        return tasks


# 示例 4: 单次状态查询
async def check_single_task(client: MockAPIClient, task_id: str):
    """查询单个任务状态"""
    print(f"\n{'=' * 60}")
    print(f"🔍 查询任务: {task_id}")
    print(f"{'=' * 60}")

    task = await client.get_task_status(task_id)

    if task:
        task.print_status()

        if task.status.is_finished():
            if task.status.is_success():
                print("\n🎉 任务已完成!")
            else:
                print(f"\n⚠️  任务失败: {task.data.get('error_message', '未知错误')}")
    else:
        print(f"\n❌ 任务不存在: {task_id}")


# 示例 5: 状态轮询
async def poll_task_status(client: MockAPIClient, task_id: str, interval: int = 2, timeout: int = 30):
    """
    轮询任务状态

    Args:
        client: API 客户端
        task_id: 任务 ID
        interval: 查询间隔（秒）
        timeout: 超时时间（秒）
    """
    print(f"\n⏱️  开始轮询任务: {task_id}")
    print(f"  间隔: {interval}秒")
    print(f"  超时: {timeout}秒")

    start_time = datetime.now()
    last_status = None
    poll_count = 0

    while True:
        poll_count += 1
        elapsed = (datetime.now() - start_time).total_seconds()

        print(f"\n{'─' * 60}")
        print(f"第 {poll_count} 次查询 (已等待 {elapsed:.0f}s)")
        print(f"{'─' * 60}")

        task = await client.get_task_status(task_id)

        if not task:
            print(f"❌ 任务不存在")
            break

        # 显示状态
        task.print_status()

        # 检查是否完成
        if task.status.is_finished():
            print(f"\n✅ 任务结束: {task.status.value}")
            break

        # 检查超时
        if elapsed >= timeout:
            print(f"\n⏰ 轮询超时")
            break

        # 状态变化检测
        if last_status and last_status != task.status:
            print(f"\n🔄 状态变化: {last_status} → {task.status.value}")

        last_status = task.status

        # 等待下次查询
        print(f"\n💤 等待 {interval} 秒后继续...")
        await asyncio.sleep(interval)

    print(f"\n📊 轮询结束，总计 {poll_count} 次查询")


# 示例 6: 批量状态查询
async def batch_check_tasks(client: MockAPIClient, task_ids: list):
    """批量查询任务状态"""
    print(f"\n{'=' * 60}")
    print(f"📋 批量查询 {len(task_ids)} 个任务")
    print(f"{'=' * 60}")

    # 并发查询
    tasks = await asyncio.gather(*[client.get_task_status(tid) for tid in task_ids])

    # 分类统计
    completed = []
    running = []
    failed = []
    not_found = []

    for task in tasks:
        if not task:
            not_found.append("unknown")
            continue

        if task.status.is_success():
            completed.append(task)
        elif task.status == TaskStatus.FAILED:
            failed.append(task)
        else:
            running.append(task)

    # 显示统计
    print(f"\n📊 查询结果:")
    print(f"  ✅ 已完成: {len(completed)}")
    print(f"  ⏳ 运行中: {len(running)}")
    print(f"  ❌ 失败: {len(failed)}")
    print(f"  ❓ 未找到: {len(not_found)}")

    # 显示详情
    if running:
        print(f"\n⏳ 运行中的任务:")
        for task in running:
            print(f"  - {task.task_id}: {task.status.value} ({task.progress}%)")

    if failed:
        print(f"\n❌ 失败的任务:")
        for task in failed:
            print(f"  - {task.task_id}: {task.data.get('error_message', '未知错误')}")

    return {
        'completed': completed,
        'running': running,
        'failed': failed,
        'not_found': not_found,
    }


# 示例 7: 实时状态监控
async def monitor_tasks_realtime(client: MockAPIClient, task_ids: list):
    """实时监控多个任务"""
    print(f"\n{'=' * 60}")
    print(f"👁️  实时监控 {len(task_ids)} 个任务")
    print(f"{'=' * 60}")

    task_statuses = {tid: None for tid in task_ids}

    while True:
        # 获取所有任务状态
        tasks = await asyncio.gather(*[client.get_task_status(tid) for tid in task_ids])

        # 更新状态并检查变化
        all_finished = True
        has_changes = False

        print(f"\n{'=' * 60}")
        print(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'=' * 60}")

        for i, task in enumerate(tasks):
            task_id = task_ids[i]
            new_status = task.status.value if task else "not_found"

            # 检查状态变化
            if task_statuses[task_id] != new_status:
                has_changes = True
                if task:
                    task.print_status()
                else:
                    print(f"❓ 任务不存在: {task_id}")

            task_statuses[task_id] = new_status

            # 检查是否还有运行中的任务
            if task and not task.status.is_finished():
                all_finished = False

        # 如果所有任务都完成，退出监控
        if all_finished:
            print(f"\n✅ 所有任务已完成，停止监控")
            break

        # 如果没有状态变化，显示提示
        if not has_changes:
            print(f"⏳ 暂无状态变化...")

        # 等待
        await asyncio.sleep(3)


def main():
    """主函数"""
    print("=" * 60)
    print("📊 ScholarFlow 任务状态查询示例")
    print("=" * 60)

    # 创建模拟客户端
    client = MockAPIClient()

    # 示例 1: 单次查询
    asyncio.run(check_single_task(client, "task-001"))

    # 示例 2: 轮询查询
    asyncio.run(poll_task_status(client, "task-002", interval=1, timeout=10))

    # 示例 3: 批量查询
    task_ids = ["task-001", "task-002", "task-003", "task-004"]
    asyncio.run(batch_check_tasks(client, task_ids))

    # 示例 4: 实时监控
    asyncio.run(monitor_tasks_realtime(client, ["task-002", "task-003"]))

    print("\n" + "=" * 60)
    print("✨ 任务状态查询示例完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()


"""
💡 学习要点:

1. 任务状态管理
   - 使用枚举定义状态
   - 状态辅助方法（is_finished, is_success）
   - 进度映射

2. 状态查询
   - 单次查询
   - 轮询机制
   - 批量查询

3. 状态变化检测
   - 记录上次状态
   - 对比状态变化
   - 实时更新

4. 超时处理
   - 设置超时时间
   - 定期检查超时
   - 优雅退出

📝 扩展练习:

1. 添加 WebSocket 实时推送
2. 实现状态持久化
3. 添加任务历史记录
4. 实现状态通知
5. 添加任务过滤和排序

🔗 相关文档:

- 任务状态 API: 见第14章
- aiohttp: https://docs.aiohttp.org/
"""
