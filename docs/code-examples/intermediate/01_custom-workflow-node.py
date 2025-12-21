#!/usr/bin/env python3
"""
高级代码示例1: 自定义工作流节点开发
=====================================

本示例展示如何为ScholarFlow系统开发自定义工作流节点，
包括节点注册、状态管理、错误处理和条件路由。

功能特性:
- 创建自定义处理节点
- 实现条件分支逻辑
- 状态数据验证
- 错误处理与恢复
- 动态路由决策

作者: Claude Code
版本: 1.0
"""

from typing import TypedDict, Optional, Literal, Any, Dict, List
from enum import Enum
import asyncio
import logging
from datetime import datetime
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 定义节点输入输出类型
# ============================================================================

class CustomNodeState(TypedDict, total=False):
    """自定义节点状态"""
    task_id: str
    current_step: str
    # 输入数据
    input_data: Dict[str, Any]
    processing_options: Dict[str, Any]

    # 处理结果
    processed_result: Optional[Dict[str, Any]]
    validation_errors: List[str]

    # 控制流
    should_continue: bool
    next_node: Literal["validation", "transformation", "end"]

    # 元数据
    node_metadata: Dict[str, Any]
    execution_log: List[Dict[str, Any]]


class ProcessingMode(Enum):
    """处理模式"""
    STRICT = "strict"      # 严格模式，错误时终止
    RELAXED = "relaxed"    # 宽松模式，记录错误但继续
    ADAPTIVE = "adaptive"   # 自适应模式，根据数据自动调整


class ValidationLevel(Enum):
    """验证级别"""
    BASIC = "basic"        # 基础验证
    STANDARD = "standard"  # 标准验证
    STRICT = "strict"      # 严格验证


# ============================================================================
# 2. 实现自定义节点类
# ============================================================================

class CustomProcessingNode:
    """自定义处理节点

    这是一个高级示例，展示如何创建一个功能完整的自定义节点。
    节点能够:
    - 验证输入数据
    - 根据配置执行不同的处理逻辑
    - 动态决定下一步路由
    - 处理错误并记录日志
    - 支持多种处理模式
    """

    def __init__(
        self,
        node_id: str,
        processing_mode: ProcessingMode = ProcessingMode.ADAPTIVE,
        validation_level: ValidationLevel = ValidationLevel.STANDARD
    ):
        self.node_id = node_id
        self.processing_mode = processing_mode
        self.validation_level = validation_level
        self.logger = logging.getLogger(f"node.{node_id}")

        # 节点统计
        self.stats = {
            "executions": 0,
            "successes": 0,
            "failures": 0,
            "average_duration": 0.0,
        }

    async def execute(
        self,
        state: CustomNodeState,
        context: Optional[Dict[str, Any]] = None
    ) -> CustomNodeState:
        """执行节点处理

        Args:
            state: 当前工作流状态
            context: 节点执行上下文

        Returns:
            更新后的状态
        """
        start_time = datetime.now()
        self.stats["executions"] += 1

        try:
            self.logger.info(f"Starting execution of node {self.node_id}")

            # 1. 记录执行开始
            state = self._log_execution_start(state, context)

            # 2. 验证输入数据
            validation_result = await self._validate_input(state)
            if not validation_result["valid"]:
                return await self._handle_validation_failure(state, validation_result)

            # 3. 根据模式选择处理策略
            if self.processing_mode == ProcessingMode.STRICT:
                result = await self._process_strict_mode(state)
            elif self.processing_mode == ProcessingMode.RELAXED:
                result = await self._process_relaxed_mode(state)
            else:  # ADAPTIVE
                result = await self._process_adaptive_mode(state)

            # 4. 更新状态
            state = await self._update_state(state, result)

            # 5. 决定下一步路由
            state = await self._determine_next_step(state)

            # 6. 记录成功
            self.stats["successes"] += 1
            state = self._log_execution_success(state, start_time)

            self.logger.info(f"Node {self.node_id} executed successfully")
            return state

        except Exception as e:
            # 错误处理
            self.stats["failures"] += 1
            state = await self._handle_execution_error(state, e, start_time)
            raise

    async def _validate_input(self, state: CustomNodeState) -> Dict[str, Any]:
        """验证输入数据

        根据验证级别执行不同级别的验证。
        """
        errors = []
        warnings = []

        input_data = state.get("input_data", {})

        # 基础验证 (所有级别)
        if not input_data:
            errors.append("Input data is required")

        # 标准验证
        if self.validation_level in [ValidationLevel.STANDARD, ValidationLevel.STRICT]:
            if "content" not in input_data:
                errors.append("Missing required field: content")

            if "metadata" in input_data:
                if not isinstance(input_data["metadata"], dict):
                    errors.append("Metadata must be a dictionary")

        # 严格验证
        if self.validation_level == ValidationLevel.STRICT:
            if "encoding" not in input_data.get("metadata", {}):
                warnings.append("Encoding not specified, using default")

            if "format" not in input_data.get("metadata", {}):
                errors.append("Format must be specified in metadata")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    async def _process_strict_mode(self, state: CustomNodeState) -> Dict[str, Any]:
        """严格模式处理

        遇到任何错误都抛出异常，停止处理。
        """
        input_data = state["input_data"]

        # 严格验证所有必需字段
        required_fields = ["content", "format", "encoding"]
        for field in required_fields:
            if field not in input_data.get("metadata", {}):
                raise ValueError(f"Missing required field: {field}")

        # 执行处理
        result = {
            "processed": True,
            "records_processed": len(input_data.get("content", "")),
            "quality_score": await self._calculate_quality_score(input_data),
            "recommendations": [],
        }

        # 添加建议
        if result["quality_score"] < 0.7:
            result["recommendations"].append("Consider improving data quality")

        return result

    async def _process_relaxed_mode(self, state: CustomNodeState) -> Dict[str, Any]:
        """宽松模式处理

        记录错误但继续处理，使用默认值。
        """
        input_data = state["input_data"]
        validation_errors = state.get("validation_errors", [])

        # 使用默认值填充缺失字段
        metadata = input_data.get("metadata", {})
        metadata.setdefault("encoding", "utf-8")
        metadata.setdefault("format", "json")

        # 记录处理过程
        result = {
            "processed": True,
            "records_processed": len(input_data.get("content", "")),
            "quality_score": await self._calculate_quality_score(input_data),
            "default_values_used": ["encoding", "format"],
            "validation_errors": validation_errors,
            "recommendations": [
                "Some fields were missing and filled with defaults",
                "Review input data for completeness",
            ],
        }

        return result

    async def _process_adaptive_mode(self, state: CustomNodeState) -> Dict[str, Any]:
        """自适应模式处理

        根据数据质量自动选择处理策略。
        """
        input_data = state["input_data"]

        # 评估数据质量
        quality_score = await self._calculate_quality_score(input_data)

        # 根据质量分数决定处理策略
        if quality_score >= 0.9:
            # 高质量数据，使用快速处理
            result = await self._process_fast_path(input_data)
        elif quality_score >= 0.7:
            # 中等质量数据，使用标准处理
            result = await self._process_standard_path(input_data)
        else:
            # 低质量数据，使用详细处理和验证
            result = await self._process_detailed_path(input_data)

        result["quality_score"] = quality_score
        result["adaptive_strategy"] = "fast" if quality_score >= 0.9 else "standard" if quality_score >= 0.7 else "detailed"

        return result

    async def _calculate_quality_score(self, input_data: Dict[str, Any]) -> float:
        """计算数据质量分数 (0-1)"""
        score = 1.0
        metadata = input_data.get("metadata", {})

        # 检查必需字段
        required_fields = ["format", "encoding"]
        for field in required_fields:
            if field not in metadata:
                score -= 0.2

        # 检查内容长度
        content = input_data.get("content", "")
        if len(content) < 100:
            score -= 0.3
        elif len(content) > 100000:
            score -= 0.1

        # 检查格式一致性
        if "format" in metadata:
            if metadata["format"] not in ["json", "xml", "csv"]:
                score -= 0.2

        return max(0.0, min(1.0, score))

    async def _process_fast_path(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """快速处理路径"""
        # 最小化处理，最大化性能
        return {
            "processed": True,
            "strategy": "fast",
            "processing_time_ms": 100,
            "records_processed": 1,
        }

    async def _process_standard_path(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准处理路径"""
        await asyncio.sleep(0.1)  # 模拟处理时间
        return {
            "processed": True,
            "strategy": "standard",
            "processing_time_ms": 200,
            "records_processed": 1,
        }

    async def _process_detailed_path(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """详细处理路径"""
        await asyncio.sleep(0.5)  # 模拟详细处理

        return {
            "processed": True,
            "strategy": "detailed",
            "processing_time_ms": 500,
            "records_processed": 1,
            "recommendations": [
                "Input data quality is low",
                "Consider data cleaning before processing",
            ],
        }

    async def _update_state(
        self,
        state: CustomNodeState,
        result: Dict[str, Any]
    ) -> CustomNodeState:
        """更新状态"""
        updated_state = state.copy()

        updated_state["processed_result"] = result
        updated_state["current_step"] = f"Completed: {self.node_id}"
        updated_state["should_continue"] = True

        # 添加节点元数据
        node_metadata = updated_state.get("node_metadata", {})
        node_metadata[self.node_id] = {
            "executed_at": datetime.now().isoformat(),
            "processing_mode": self.processing_mode.value,
            "result": result,
        }
        updated_state["node_metadata"] = node_metadata

        return updated_state

    async def _determine_next_step(self, state: CustomNodeState) -> CustomNodeState:
        """决定下一步路由"""
        result = state.get("processed_result", {})

        # 基于结果质量决定下一步
        quality_score = result.get("quality_score", 0.5)

        if quality_score >= 0.8:
            next_node = "transformation"
        elif quality_score >= 0.5:
            next_node = "validation"
        else:
            next_node = "end"

        state["next_node"] = next_node
        state["current_step"] = f"Routing to: {next_node}"

        return state

    def _log_execution_start(
        self,
        state: CustomNodeState,
        context: Optional[Dict[str, Any]]
    ) -> CustomNodeState:
        """记录执行开始"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "execution_started",
            "node_id": self.node_id,
            "mode": self.processing_mode.value,
        }

        if context:
            log_entry["context"] = context

        execution_log = state.get("execution_log", [])
        execution_log.append(log_entry)
        state["execution_log"] = execution_log

        return state

    def _log_execution_success(
        self,
        state: CustomNodeState,
        start_time: datetime
    ) -> CustomNodeState:
        """记录执行成功"""
        duration = (datetime.now() - start_time).total_seconds()

        # 更新统计
        self.stats["average_duration"] = (
            (self.stats["average_duration"] * (self.stats["executions"] - 1) + duration)
            / self.stats["executions"]
        )

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "execution_completed",
            "node_id": self.node_id,
            "duration_seconds": duration,
            "status": "success",
        }

        execution_log = state.get("execution_log", [])
        execution_log.append(log_entry)
        state["execution_log"] = execution_log

        return state

    async def _handle_validation_failure(
        self,
        state: CustomNodeState,
        validation_result: Dict[str, Any]
    ) -> CustomNodeState:
        """处理验证失败"""
        state["validation_errors"] = validation_result["errors"]
        state["should_continue"] = False
        state["next_node"] = "end"

        # 根据处理模式决定是否继续
        if self.processing_mode == ProcessingMode.STRICT:
            raise ValueError(f"Validation failed: {validation_result['errors']}")

        self.logger.warning(
            f"Validation failed in {self.node_id}: {validation_result['errors']}"
        )

        return state

    async def _handle_execution_error(
        self,
        state: CustomNodeState,
        error: Exception,
        start_time: datetime
    ) -> CustomNodeState:
        """处理执行错误"""
        duration = (datetime.now() - start_time).total_seconds()

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "execution_failed",
            "node_id": self.node_id,
            "error": str(error),
            "error_type": type(error).__name__,
            "duration_seconds": duration,
        }

        execution_log = state.get("execution_log", [])
        execution_log.append(log_entry)
        state["execution_log"] = execution_log

        state["current_step"] = f"Error in {self.node_id}: {str(error)}"

        self.logger.error(
            f"Node {self.node_id} execution failed: {error}",
            exc_info=True
        )

        return state

    def get_stats(self) -> Dict[str, Any]:
        """获取节点统计信息"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successes"] / max(self.stats["executions"], 1)
            ) * 100,
        }


# ============================================================================
# 3. 节点工厂和注册机制
# ============================================================================

class NodeFactory:
    """节点工厂

    管理自定义节点的创建和注册。
    """

    _nodes: Dict[str, type] = {}
    _instances: Dict[str, CustomProcessingNode] = {}

    @classmethod
    def register_node(cls, node_id: str, node_class: type):
        """注册节点类"""
        cls._nodes[node_id] = node_class
        logger.info(f"Registered node: {node_id}")

    @classmethod
    def create_node(
        cls,
        node_id: str,
        processing_mode: ProcessingMode = ProcessingMode.ADAPTIVE,
        validation_level: ValidationLevel = ValidationLevel.STANDARD,
        **kwargs
    ) -> CustomProcessingNode:
        """创建节点实例"""
        if node_id not in cls._nodes:
            raise ValueError(f"Node not registered: {node_id}")

        node_class = cls._nodes[node_id]
        node_instance = node_class(
            node_id=node_id,
            processing_mode=processing_mode,
            validation_level=validation_level,
            **kwargs
        )

        cls._instances[node_id] = node_instance
        return node_instance

    @classmethod
    def get_node(cls, node_id: str) -> Optional[CustomProcessingNode]:
        """获取节点实例"""
        return cls._instances.get(node_id)

    @classmethod
    def list_nodes(cls) -> List[str]:
        """列出所有注册的节点"""
        return list(cls._nodes.keys())


# ============================================================================
# 4. 使用示例
# ============================================================================

async def example_custom_node():
    """自定义节点使用示例"""

    # 1. 创建初始状态
    initial_state: CustomNodeState = {
        "task_id": "task_001",
        "current_step": "Starting custom processing",
        "input_data": {
            "content": "Sample content for processing",
            "metadata": {
                "format": "json",
                "encoding": "utf-8",
                "source": "example",
            }
        },
        "processing_options": {
            "mode": "adaptive",
            "validation": "standard",
        },
        "validation_errors": [],
        "processed_result": None,
        "should_continue": True,
        "next_node": "custom",
        "node_metadata": {},
        "execution_log": [],
    }

    # 2. 注册自定义节点
    NodeFactory.register_node("custom_processor", CustomProcessingNode)

    # 3. 创建节点实例
    node = NodeFactory.create_node(
        node_id="custom_processor",
        processing_mode=ProcessingMode.ADAPTIVE,
        validation_level=ValidationLevel.STANDARD
    )

    # 4. 执行节点
    try:
        result_state = await node.execute(initial_state)

        # 5. 输出结果
        print("\n=== 执行结果 ===")
        print(f"任务ID: {result_state['task_id']}")
        print(f"当前步骤: {result_state['current_step']}")
        print(f"下一步路由: {result_state['next_node']}")
        print(f"处理结果: {json.dumps(result_state['processed_result'], indent=2)}")

        # 6. 显示统计信息
        print("\n=== 节点统计 ===")
        stats = node.get_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")

        # 7. 显示执行日志
        print("\n=== 执行日志 ===")
        for log_entry in result_state["execution_log"]:
            print(json.dumps(log_entry, indent=2))

        return result_state

    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)
        raise


# ============================================================================
# 5. 高级用法：条件路由节点
# ============================================================================

class ConditionalRoutingNode(CustomProcessingNode):
    """条件路由节点

    展示如何基于处理结果动态决定路由。
    """

    async def _determine_next_step(self, state: CustomNodeState) -> CustomNodeState:
        """基于条件决定下一步"""
        result = state.get("processed_result", {})

        # 多条件决策
        conditions = {
            "high_quality": result.get("quality_score", 0) >= 0.8,
            "needs_validation": result.get("validation_errors"),
            "has_recommendations": result.get("recommendations"),
            "fast_processing": result.get("processing_time_ms", 1000) < 200,
        }

        # 决策树逻辑
        if conditions["high_quality"] and conditions["fast_processing"]:
            next_node = "transformation"
        elif conditions["needs_validation"]:
            next_node = "validation"
        elif conditions["has_recommendations"]:
            next_node = "review"
        else:
            next_node = "end"

        state["next_node"] = next_node
        state["current_step"] = f"Conditional routing to: {next_node} (conditions: {conditions})"

        return state


# ============================================================================
# 6. 主函数
# ============================================================================

if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_custom_node())
