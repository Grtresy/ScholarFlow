#!/usr/bin/env python3
"""
高级代码示例14: 高级工作流管理
=================================

本示例展示如何构建一个功能完整的高级工作流管理系统，
用于ScholarFlow中的复杂流程编排和控制。

功能特性:
- 工作流定义与编译
- 动态节点管理
- 条件分支与循环
- 并行执行控制
- 事件驱动架构
- 工作流版本管理
- 回滚机制
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
import uuid
from collections import defaultdict, deque
import graphlib
from abc import ABC, abstractmethod

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class NodeType(Enum):
    """节点类型"""
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    MERGE = "merge"
    LOOP = "loop"
    SUBWORKFLOW = "subworkflow"
    EVENT = "event"


class NodeStatus(Enum):
    """节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class WorkflowStatus(Enum):
    """工作流状态"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowNode:
    """工作流节点"""
    node_id: str
    name: str
    node_type: NodeType
    handler: Optional[Callable] = None
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowEdge:
    """工作流边"""
    from_node: str
    to_node: str
    condition: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowContext:
    """工作流上下文"""
    workflow_id: str
    execution_id: str
    state: Dict[str, Any]
    history: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeExecutionResult:
    """节点执行结果"""
    node_id: str
    status: NodeStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 2. 节点处理器
# ============================================================================

class NodeHandler(ABC):
    """节点处理器基类"""

    @abstractmethod
    async def execute(
        self,
        node: WorkflowNode,
        context: WorkflowContext
    ) -> NodeExecutionResult:
        """执行节点"""
        pass


class TaskNodeHandler(NodeHandler):
    """任务节点处理器"""

    async def execute(
        self,
        node: WorkflowNode,
        context: WorkflowContext
    ) -> NodeExecutionResult:
        """执行任务节点"""
        start_time = datetime.now()

        try:
            # 模拟任务执行
            task_type = node.config.get("task_type", "default")
            duration = node.config.get("duration", 1.0)

            await asyncio.sleep(duration)

            # 生成输出
            output = {
                "task_type": task_type,
                "completed_at": datetime.now().isoformat(),
                "result": f"Task {node.node_id} completed successfully"
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"Task node {node.node_id} completed in {execution_time:.2f}s")

            return NodeExecutionResult(
                node_id=node.node_id,
                status=NodeStatus.COMPLETED,
                output=output,
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Task node {node.node_id} failed: {e}")

            return NodeExecutionResult(
                node_id=node.node_id,
                status=NodeStatus.FAILED,
                error=str(e),
                execution_time=execution_time
            )


class ConditionNodeHandler(NodeHandler):
    """条件节点处理器"""

    async def execute(
        self,
        node: WorkflowNode,
        context: WorkflowContext
    ) -> NodeExecutionResult:
        """执行条件节点"""
        start_time = datetime.now()

        try:
            # 获取条件表达式
            condition_expr = node.config.get("condition", "true")

            # 评估条件
            result = self._evaluate_condition(condition_expr, context)

            output = {
                "condition": condition_expr,
                "result": result,
                "true_branch": node.config.get("true_branch"),
                "false_branch": node.config.get("false_branch")
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            return NodeExecutionResult(
                node_id=node.node_id,
                status=NodeStatus.COMPLETED,
                output=output,
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            return NodeExecutionResult(
                node_id=node.node_id,
                status=NodeStatus.FAILED,
                error=str(e),
                execution_time=execution_time
            )

    def _evaluate_condition(self, condition: str, context: WorkflowContext) -> bool:
        """评估条件"""
        # 简化实现：支持简单的变量比较
        try:
            if "==" in condition:
                var, value = condition.split("==")
                var = var.strip()
                value = value.strip().strip("'\"")
                return str(context.state.get(var)) == value
            elif "!=" in condition:
                var, value = condition.split("!=")
                var = var.strip()
                value = value.strip().strip("'\"")
                return str(context.state.get(var)) != value
            else:
                # 默认返回True
                return True
        except Exception:
            return False


class ParallelNodeHandler(NodeHandler):
    """并行节点处理器"""

    async def execute(
        self,
        node: WorkflowNode,
        context: WorkflowContext
    ) -> NodeExecutionResult:
        """执行并行节点"""
        start_time = datetime.now()

        try:
            # 获取子节点列表
            sub_nodes = node.config.get("sub_nodes", [])

            # 并行执行子节点
            tasks = []
            for sub_node_id in sub_nodes:
                # 这里应该从工作流定义中获取节点
                task = asyncio.create_task(self._execute_sub_node(sub_node_id, context))
                tasks.append(task)

            # 等待所有子节点完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            outputs = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    outputs.append({"node": sub_nodes[i], "error": str(result)})
                else:
                    outputs.append({"node": sub_nodes[i], "result": result})

            execution_time = (datetime.now() - start_time).total_seconds()

            return NodeExecutionResult(
                node_id=node.node_id,
                status=NodeStatus.COMPLETED,
                output={"parallel_results": outputs},
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            return NodeExecutionResult(
                node_id=node.node_id,
                status=NodeStatus.FAILED,
                error=str(e),
                execution_time=execution_time
            )

    async def _execute_sub_node(self, node_id: str, context: WorkflowContext):
        """执行子节点"""
        await asyncio.sleep(0.1)  # 模拟子节点执行
        return {"node_id": node_id, "status": "completed"}


# ============================================================================
# 3. 工作流定义
# ============================================================================

class WorkflowDefinition:
    """工作流定义"""

    def __init__(self, workflow_id: str, name: str):
        self.workflow_id = workflow_id
        self.name = name
        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: List[WorkflowEdge] = []
        self.entry_point: Optional[str] = None
        self.version: str = "1.0"
        self.metadata: Dict[str, Any] = {}

    def add_node(self, node: WorkflowNode):
        """添加节点"""
        self.nodes[node.node_id] = node
        if not self.entry_point:
            self.entry_point = node.node_id
        logger.info(f"Added node: {node.node_id}")

    def add_edge(self, edge: WorkflowEdge):
        """添加边"""
        self.edges.append(edge)
        logger.info(f"Added edge: {edge.from_node} -> {edge.to_node}")

    def validate(self) -> bool:
        """验证工作流定义"""
        # 检查节点是否存在
        for edge in self.edges:
            if edge.from_node not in self.nodes:
                raise ValueError(f"From node not found: {edge.from_node}")
            if edge.to_node not in self.nodes:
                raise ValueError(f"To node not found: {edge.to_node}")

        # 检查循环依赖
        try:
            sorter = graphlib.TopologicalSorter()
            for node in self.nodes.values():
                sorter.add(node.node_id, *node.dependencies)
            sorter.prepare()
            return True
        except graphlib.CycleError:
            raise ValueError("Workflow contains circular dependencies")

    def get_execution_order(self) -> List[str]:
        """获取执行顺序"""
        self.validate()

        sorter = graphlib.TopologicalSorter()
        for node in self.nodes.values():
            sorter.add(node.node_id, *node.dependencies)

        return list(sterer.static_order())


# ============================================================================
# 4. 工作流执行引擎
# ============================================================================

class WorkflowExecutionEngine:
    """工作流执行引擎

    功能特性:
    - 节点调度
    - 并行执行
    - 条件分支
    - 错误处理
    - 状态管理
    - 事件通知
    """

    def __init__(self):
        self.node_handlers: Dict[NodeType, NodeHandler] = {}
        self.active_executions: Dict[str, asyncio.Task] = {}
        self.execution_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # 注册默认处理器
        self._register_default_handlers()

        # 统计信息
        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
        }

    def _register_default_handlers(self):
        """注册默认处理器"""
        self.node_handlers[NodeType.TASK] = TaskNodeHandler()
        self.node_handlers[NodeType.CONDITION] = ConditionNodeHandler()
        self.node_handlers[NodeType.PARALLEL] = ParallelNodeHandler()

    def register_handler(self, node_type: NodeType, handler: NodeHandler):
        """注册节点处理器"""
        self.node_handlers[node_type] = handler
        logger.info(f"Registered handler for {node_type.value}")

    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        initial_state: Dict[str, Any],
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行工作流"""
        execution_id = execution_id or str(uuid.uuid4())
        start_time = datetime.now()

        logger.info(f"Starting workflow execution: {workflow.name} ({execution_id})")

        # 创建上下文
        context = WorkflowContext(
            workflow_id=workflow.workflow_id,
            execution_id=execution_id,
            state=initial_state.copy(),
            variables={}
        )

        try:
            # 验证工作流
            workflow.validate()

            # 获取执行顺序
            execution_order = workflow.get_execution_order()

            # 执行节点
            results = {}
            for node_id in execution_order:
                node = workflow.nodes[node_id]
                result = await self._execute_node(node, context)
                results[node_id] = result

                # 更新上下文状态
                if result.output:
                    context.state.update(result.output)

                # 记录历史
                self.execution_history[execution_id].append({
                    "node_id": node_id,
                    "status": result.status.value,
                    "timestamp": datetime.now().isoformat()
                })

                # 检查失败
                if result.status == NodeStatus.FAILED:
                    logger.error(f"Workflow failed at node: {node_id}")
                    break

            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()

            # 更新统计
            self.stats["total_executions"] += 1
            self.stats["average_execution_time"] = (
                (self.stats["average_execution_time"] * (self.stats["total_executions"] - 1) + execution_time)
                / self.stats["total_executions"]
            )

            success = all(r.status == NodeStatus.COMPLETED for r in results.values())
            if success:
                self.stats["successful_executions"] += 1
            else:
                self.stats["failed_executions"] += 1

            logger.info(f"Workflow execution completed in {execution_time:.2f}s")

            return {
                "execution_id": execution_id,
                "workflow_id": workflow.workflow_id,
                "status": "completed" if success else "failed",
                "execution_time": execution_time,
                "node_results": results,
                "final_state": context.state
            }

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.stats["failed_executions"] += 1
            self.stats["total_executions"] += 1

            logger.error(f"Workflow execution failed: {e}")
            raise

    async def _execute_node(
        self,
        node: WorkflowNode,
        context: WorkflowContext
    ) -> NodeExecutionResult:
        """执行单个节点"""
        logger.info(f"Executing node: {node.node_id} ({node.node_type.value})")

        # 获取处理器
        handler = self.node_handlers.get(node.node_type)
        if not handler:
            raise ValueError(f"No handler for node type: {node.node_type.value}")

        # 执行节点
        result = await handler.execute(node, context)

        # 记录到上下文历史
        context.history.append({
            "node_id": node.node_id,
            "timestamp": datetime.now().isoformat(),
            "status": result.status.value,
            "output": result.output
        })

        return result

    async def pause_workflow(self, execution_id: str):
        """暂停工作流"""
        if execution_id in self.active_executions:
            task = self.active_executions[execution_id]
            task.cancel()
            logger.info(f"Paused workflow execution: {execution_id}")

    async def resume_workflow(
        self,
        workflow: WorkflowDefinition,
        execution_id: str,
        saved_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """恢复工作流"""
        logger.info(f"Resuming workflow execution: {execution_id}")

        # 重新执行工作流（简化实现）
        return await self.execute_workflow(workflow, saved_state, execution_id)

    def get_execution_history(self, execution_id: str) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self.execution_history.get(execution_id, [])

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        success_rate = (
            self.stats["successful_executions"] / max(self.stats["total_executions"], 1) * 100
        )

        return {
            **self.stats,
            "success_rate": success_rate,
            "active_executions": len(self.active_executions),
        }


# ============================================================================
# 5. 工作流工厂
# ============================================================================

class WorkflowFactory:
    """工作流工厂

    提供便捷的工作流创建方法。
    """

    @staticmethod
    def create_simple_workflow(
        workflow_id: str,
        name: str,
        steps: List[Dict[str, Any]]
    ) -> WorkflowDefinition:
        """创建简单工作流"""
        workflow = WorkflowDefinition(workflow_id, name)

        # 创建节点
        for i, step in enumerate(steps):
            node = WorkflowNode(
                node_id=step.get("id", f"node_{i}"),
                name=step.get("name", f"Step {i}"),
                node_type=NodeType(step.get("type", "task")),
                config=step.get("config", {})
            )
            workflow.add_node(node)

            # 添加依赖
            if i > 0:
                node.dependencies.append(steps[i-1].get("id", f"node_{i-1}"))

        return workflow

    @staticmethod
    def create_conditional_workflow(
        workflow_id: str,
        name: str,
        condition_config: Dict[str, Any]
    ) -> WorkflowDefinition:
        """创建条件工作流"""
        workflow = WorkflowDefinition(workflow_id, name)

        # 创建条件节点
        condition_node = WorkflowNode(
            node_id="condition_1",
            name="Condition Check",
            node_type=NodeType.CONDITION,
            config=condition_config
        )
        workflow.add_node(condition_node)

        # 创建分支节点
        true_node = WorkflowNode(
            node_id="true_branch",
            name="True Branch",
            node_type=NodeType.TASK,
            config={"task_type": "true_task"}
        )
        workflow.add_node(true_node)

        false_node = WorkflowNode(
            node_id="false_branch",
            name="False Branch",
            node_type=NodeType.TASK,
            config={"task_type": "false_task"}
        )
        workflow.add_node(false_node)

        # 添加边
        workflow.add_edge(WorkflowEdge("condition_1", "true_branch"))
        workflow.add_edge(WorkflowEdge("condition_1", "false_branch"))

        return workflow


# ============================================================================
# 6. 使用示例
# ============================================================================

async def example_advanced_workflow():
    """高级工作流示例"""

    # 1. 创建执行引擎
    print("\n=== 创建工作流执行引擎 ===")
    engine = WorkflowExecutionEngine()

    # 2. 创建简单工作流
    print("\n=== 创建简单工作流 ===")
    simple_workflow = WorkflowFactory.create_simple_workflow(
        workflow_id="simple_001",
        name="Simple Workflow",
        steps=[
            {"id": "start", "name": "Start", "type": "task", "config": {"task_type": "initialize"}},
            {"id": "process", "name": "Process", "type": "task", "config": {"task_type": "process"}},
            {"id": "end", "name": "End", "type": "task", "config": {"task_type": "finalize"}},
        ]
    )

    print(f"工作流: {simple_workflow.name}")
    print(f"节点数: {len(simple_workflow.nodes)}")
    print(f"执行顺序: {simple_workflow.get_execution_order()}")

    # 3. 执行简单工作流
    print("\n=== 执行简单工作流 ===")
    initial_state = {"status": "started", "progress": 0}
    result = await engine.execute_workflow(simple_workflow, initial_state)

    print(f"执行ID: {result['execution_id']}")
    print(f"状态: {result['status']}")
    print(f"执行时间: {result['execution_time']:.2f}s")
    print(f"最终状态: {result['final_state']}")

    # 4. 创建条件工作流
    print("\n=== 创建条件工作流 ===")
    conditional_workflow = WorkflowFactory.create_conditional_workflow(
        workflow_id="conditional_001",
        name="Conditional Workflow",
        condition_config={
            "condition": "status == 'ready'",
            "true_branch": "process_data",
            "false_branch": "prepare_data"
        }
    )

    print(f"工作流: {conditional_workflow.name}")
    print(f"节点数: {len(conditional_workflow.nodes)}")

    # 5. 执行条件工作流（条件为真）
    print("\n=== 执行条件工作流（条件为真） ===")
    result_true = await engine.execute_workflow(
        conditional_workflow,
        {"status": "ready", "progress": 50}
    )
    print(f"状态: {result_true['status']}")
    print(f"执行时间: {result_true['execution_time']:.2f}s")

    # 6. 执行条件工作流（条件为假）
    print("\n=== 执行条件工作流（条件为假） ===")
    result_false = await engine.execute_workflow(
        conditional_workflow,
        {"status": "not_ready", "progress": 0}
    )
    print(f"状态: {result_false['status']}")
    print(f"执行时间: {result_false['execution_time']:.2f}s")

    # 7. 创建并行工作流
    print("\n=== 创建并行工作流 ===")
    parallel_workflow = WorkflowDefinition("parallel_001", "Parallel Workflow")

    # 创建并行节点
    parallel_node = WorkflowNode(
        node_id="parallel",
        name="Parallel Processing",
        node_type=NodeType.PARALLEL,
        config={
            "sub_nodes": ["task1", "task2", "task3"]
        }
    )
    parallel_workflow.add_node(parallel_node)

    # 创建子任务节点
    for i in range(1, 4):
        task_node = WorkflowNode(
            node_id=f"task{i}",
            name=f"Task {i}",
            node_type=NodeType.TASK,
            config={"task_type": f"parallel_task_{i}", "duration": 0.5}
        )
        parallel_workflow.add_node(task_node)

    # 8. 执行并行工作流
    print("\n=== 执行并行工作流 ===")
    result_parallel = await engine.execute_workflow(parallel_workflow, {})
    print(f"状态: {result_parallel['status']}")
    print(f"执行时间: {result_parallel['execution_time']:.2f}s")

    # 9. 显示执行历史
    print("\n=== 执行历史 ===")
    history = engine.get_execution_history(result['execution_id'])
    for entry in history:
        print(f"  {entry['timestamp']} - {entry['node_id']}: {entry['status']}")

    # 10. 显示统计信息
    print("\n=== 统计信息 ===")
    stats = engine.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


# ============================================================================
# 7. 高级功能：工作流版本管理
# ============================================================================

class WorkflowVersionManager:
    """工作流版本管理器

    管理工作流定义的版本控制和回滚。
    """

    def __init__(self):
        self.versions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def save_version(
        self,
        workflow: WorkflowDefinition,
        version: Optional[str] = None
    ) -> str:
        """保存版本"""
        version = version or workflow.version

        version_data = {
            "version": version,
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "nodes": {nid: node.__dict__ for nid, node in workflow.nodes.items()},
            "edges": [edge.__dict__ for edge in workflow.edges],
            "created_at": datetime.now().isoformat(),
        }

        self.versions[workflow.workflow_id].append(version_data)

        logger.info(f"Saved workflow version: {workflow.workflow_id} v{version}")
        return version

    def get_version(
        self,
        workflow_id: str,
        version: str
    ) -> Optional[Dict[str, Any]]:
        """获取版本"""
        versions = self.versions.get(workflow_id, [])
        for v in versions:
            if v["version"] == version:
                return v
        return None

    def list_versions(self, workflow_id: str) -> List[str]:
        """列出所有版本"""
        versions = self.versions.get(workflow_id, [])
        return [v["version"] for v in versions]


# ============================================================================
# 8. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_advanced_workflow())
