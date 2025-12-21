#!/usr/bin/env python3
"""
高级代码示例8: 自定义路由逻辑
=================================

本示例展示如何构建一个灵活的自定义路由系统，
用于ScholarFlow工作流中的动态路径决策。

功能特性:
- 条件路由引擎
- 规则优先级管理
- 动态路由策略
- 上下文感知路由
- 路由性能监控
- 路由回退机制
- 自定义路由函数

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
from datetime import datetime
import json
import re
from abc import ABC, abstractmethod

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class RouteCondition(Enum):
    """路由条件类型"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX = "regex"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    CUSTOM = "custom"


class RouteAction(Enum):
    """路由动作"""
    NEXT = "next"
    SKIP = "skip"
    REPEAT = "repeat"
    FALLBACK = "fallback"
    END = "end"
    CUSTOM = "custom"


@dataclass
class RouteContext:
    """路由上下文"""
    task_id: str
    current_node: str
    state: Dict[str, Any]
    history: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteRule:
    """路由规则"""
    rule_id: str
    name: str
    priority: int  # 数字越小优先级越高
    conditions: List[Dict[str, Any]]
    action: RouteAction
    target: Optional[str] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingResult:
    """路由结果"""
    rule_id: str
    action: RouteAction
    target: Optional[str]
    context: RouteContext
    executed_at: datetime = field(default_factory=datetime.now)


# ============================================================================
# 2. 条件评估器
# ============================================================================

class ConditionEvaluator:
    """条件评估器"""

    @staticmethod
    def evaluate_condition(
        condition: Dict[str, Any],
        context: RouteContext
    ) -> bool:
        """评估单个条件"""
        condition_type = condition["type"]
        field_path = condition["field"]
        value = condition.get("value")

        # 获取字段值
        field_value = ConditionEvaluator._get_nested_value(context.state, field_path)

        # 根据条件类型评估
        if condition_type == RouteCondition.EQUALS:
            return field_value == value
        elif condition_type == RouteCondition.NOT_EQUALS:
            return field_value != value
        elif condition_type == RouteCondition.CONTAINS:
            return value in field_value if field_value else False
        elif condition_type == RouteCondition.NOT_CONTAINS:
            return value not in field_value if field_value else True
        elif condition_type == RouteCondition.REGEX:
            pattern = re.compile(value)
            return bool(pattern.match(str(field_value)))
        elif condition_type == RouteCondition.GREATER_THAN:
            return field_value > value
        elif condition_type == RouteCondition.LESS_THAN:
            return field_value < value
        elif condition_type == RouteCondition.IN:
            return field_value in value
        elif condition_type == RouteCondition.NOT_IN:
            return field_value not in value
        elif condition_type == RouteCondition.EXISTS:
            return field_value is not None
        elif condition_type == RouteCondition.CUSTOM:
            # 自定义评估函数
            custom_func = condition.get("func")
            if custom_func:
                return custom_func(field_value, context)
            return False
        else:
            return False

    @staticmethod
    def evaluate_conditions(
        conditions: List[Dict[str, Any]],
        context: RouteContext,
        logic: str = "and"  # and / or
    ) -> bool:
        """评估多个条件"""
        if not conditions:
            return True

        results = [
            ConditionEvaluator.evaluate_condition(cond, context)
            for cond in conditions
        ]

        if logic == "and":
            return all(results)
        elif logic == "or":
            return any(results)
        else:
            return False

    @staticmethod
    def _get_nested_value(data: Dict[str, Any], path: str) -> Any:
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
# 3. 自定义路由函数接口
# ============================================================================

class CustomRouterFunction(ABC):
    """自定义路由函数基类"""

    @abstractmethod
    async def evaluate(self, context: RouteContext) -> str:
        """评估并返回目标节点"""
        pass


class ContentComplexityRouter(CustomRouterFunction):
    """基于内容复杂度的路由

    根据内容复杂度决定是否需要额外处理。
    """

    async def evaluate(self, context: RouteContext) -> str:
        """评估内容复杂度"""
        content = context.state.get("content", "")
        word_count = len(content.split())

        if word_count > 5000:
            return "detailed_processing"
        elif word_count > 2000:
            return "standard_processing"
        else:
            return "quick_processing"


class QualityScoreRouter(CustomRouterFunction):
    """基于质量分数的路由

    根据处理结果质量决定下一步操作。
    """

    async def evaluate(self, context: RouteContext) -> str:
        """评估质量分数"""
        quality_score = context.state.get("quality_score", 0.5)

        if quality_score >= 0.9:
            return "high_quality_path"
        elif quality_score >= 0.7:
            return "standard_path"
        elif quality_score >= 0.5:
            return "review_required"
        else:
            return "reprocess_required"


# ============================================================================
# 4. 高级路由引擎
# ============================================================================

class AdvancedRoutingEngine:
    """高级路由引擎

    功能特性:
    - 规则优先级管理
    - 条件组合评估
    - 自定义路由函数
    - 动态规则加载
    - 路由统计
    - 回退机制
    """

    def __init__(self):
        self.rules: List[RouteRule] = []
        self.custom_functions: Dict[str, CustomRouterFunction] = {}
        self.default_route = "standard_path"
        self.fallback_routes = ["error_handler", "manual_review", "end"]
        self.stats = {
            "total_routes": 0,
            "rule_matches": defaultdict(int),
            "custom_routes": defaultdict(int),
        }

    def register_rule(self, rule: RouteRule):
        """注册路由规则"""
        self.rules.append(rule)
        # 按优先级排序
        self.rules.sort(key=lambda r: r.priority)
        logger.info(f"Registered route rule: {rule.name}")

    def register_custom_function(
        self,
        name: str,
        func: CustomRouterFunction
    ):
        """注册自定义路由函数"""
        self.custom_functions[name] = func
        logger.info(f"Registered custom router function: {name}")

    async def route(
        self,
        context: RouteContext
    ) -> RoutingResult:
        """执行路由"""

        self.stats["total_routes"] += 1

        # 1. 检查所有规则
        for rule in self.rules:
            if not rule.enabled:
                continue

            # 评估条件
            logic = rule.metadata.get("logic", "and")
            if ConditionEvaluator.evaluate_conditions(
                rule.conditions,
                context,
                logic
            ):
                # 规则匹配
                self.stats["rule_matches"][rule.rule_id] += 1

                # 执行动作
                if rule.action == RouteAction.NEXT:
                    return RoutingResult(
                        rule_id=rule.rule_id,
                        action=rule.action,
                        target=rule.target,
                        context=context
                    )
                elif rule.action == RouteAction.CUSTOM:
                    # 自定义动作
                    custom_action = rule.metadata.get("custom_action")
                    if custom_action in self.custom_functions:
                        result = await self.custom_functions[custom_action].evaluate(context)
                        self.stats["custom_routes"][custom_action] += 1
                        return RoutingResult(
                            rule_id=rule.rule_id,
                            action=rule.action,
                            target=result,
                            context=context
                        )

        # 2. 检查自定义路由函数
        for name, func in self.custom_functions.items():
            try:
                result = await func.evaluate(context)
                self.stats["custom_routes"][name] += 1
                return RoutingResult(
                    rule_id=f"custom_{name}",
                    action=RouteAction.CUSTOM,
                    target=result,
                    context=context
                )
            except Exception as e:
                logger.error(f"Custom router {name} failed: {e}")
                continue

        # 3. 回退机制
        for fallback in self.fallback_routes:
            return RoutingResult(
                rule_id="fallback",
                action=RouteAction.FALLBACK,
                target=fallback,
                context=context
            )

        # 4. 默认路由
        return RoutingResult(
            rule_id="default",
            action=RouteAction.NEXT,
            target=self.default_route,
            context=context
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取路由统计"""
        return {
            **dict(self.stats),
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules if r.enabled]),
            "custom_functions": list(self.custom_functions.keys()),
        }


# ============================================================================
# 5. 路由规则管理器
# ============================================================================

class RoutingRuleManager:
    """路由规则管理器

    提供便捷的规则创建和管理接口。
    """

    def __init__(self, engine: AdvancedRoutingEngine):
        self.engine = engine

    def create_condition(
        self,
        field: str,
        condition_type: RouteCondition,
        value: Any = None,
        custom_func: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """创建条件"""
        condition = {
            "field": field,
            "type": condition_type,
        }
        if value is not None:
            condition["value"] = value
        if custom_func:
            condition["func"] = custom_func
        return condition

    def create_rule(
        self,
        rule_id: str,
        name: str,
        priority: int,
        conditions: List[Dict[str, Any]],
        action: RouteAction,
        target: Optional[str] = None,
        logic: str = "and"
    ) -> RouteRule:
        """创建路由规则"""
        return RouteRule(
            rule_id=rule_id,
            name=name,
            priority=priority,
            conditions=conditions,
            action=action,
            target=target,
            metadata={"logic": logic}
        )

    def add_high_priority_rule(
        self,
        rule_id: str,
        name: str,
        field: str,
        condition_type: RouteCondition,
        value: Any,
        target: str
    ):
        """添加高优先级规则"""
        condition = self.create_condition(field, condition_type, value)
        rule = self.create_rule(
            rule_id=rule_id,
            name=name,
            priority=1,
            conditions=[condition],
            action=RouteAction.NEXT,
            target=target
        )
        self.engine.register_rule(rule)

    def add_conditional_rule(
        self,
        rule_id: str,
        name: str,
        conditions: List[Dict[str, Any]],
        target: str,
        priority: int = 5
    ):
        """添加条件组合规则"""
        rule = self.create_rule(
            rule_id=rule_id,
            name=name,
            priority=priority,
            conditions=conditions,
            action=RouteAction.NEXT,
            target=target
        )
        self.engine.register_rule(rule)


# ============================================================================
# 6. 使用示例
# ============================================================================

async def example_custom_routing():
    """自定义路由逻辑示例"""

    # 1. 创建路由引擎
    engine = AdvancedRoutingEngine()

    # 2. 注册自定义路由函数
    engine.register_custom_function("complexity", ContentComplexityRouter())
    engine.register_custom_function("quality", QualityScoreRouter())

    # 3. 创建规则管理器
    rule_manager = RoutingRuleManager(engine)

    # 4. 定义路由规则

    # 规则1: 错误状态直接进入错误处理
    rule_manager.add_high_priority_rule(
        rule_id="error_handler",
        name="Handle Errors",
        field="status",
        condition_type=RouteCondition.EQUALS,
        value="error",
        target="error_handler"
    )

    # 规则2: 需要人工审核的情况
    review_conditions = [
        rule_manager.create_condition(
            "quality_score", RouteCondition.LESS_THAN, 0.7
        ),
        rule_manager.create_condition(
            "requires_review", RouteCondition.EQUALS, True
        )
    ]
    rule_manager.add_conditional_rule(
        rule_id="requires_review",
        name="Requires Review",
        conditions=review_conditions,
        target="human_review",
        priority=2
    )

    # 规则3: 高复杂度内容进入详细处理
    rule_manager.add_conditional_rule(
        rule_id="high_complexity",
        name="High Complexity Content",
        conditions=[
            rule_manager.create_condition(
                "word_count", RouteCondition.GREATER_THAN, 5000
            )
        ],
        target="detailed_processing",
        priority=3
    )

    # 规则4: 跳过已处理的内容
    rule_manager.add_conditional_rule(
        rule_id="skip_processed",
        name="Skip Processed Content",
        conditions=[
            rule_manager.create_condition(
                "processed", RouteCondition.EQUALS, True
            )
        ],
        target="skip",
        priority=4
    )

    # 规则5: 默认路径
    rule_manager.add_conditional_rule(
        rule_id="default",
        name="Default Route",
        conditions=[],  # 无条件
        target="standard_processing",
        priority=10
    )

    # 5. 测试路由场景

    scenarios = [
        {
            "name": "Error Scenario",
            "state": {
                "status": "error",
                "message": "Processing failed"
            }
        },
        {
            "name": "Requires Review",
            "state": {
                "status": "processing",
                "quality_score": 0.6,
                "requires_review": True,
                "word_count": 1000
            }
        },
        {
            "name": "High Complexity",
            "state": {
                "status": "processing",
                "quality_score": 0.8,
                "requires_review": False,
                "word_count": 6000
            }
        },
        {
            "name": "Already Processed",
            "state": {
                "status": "completed",
                "processed": True,
                "word_count": 500
            }
        },
        {
            "name": "Standard Path",
            "state": {
                "status": "processing",
                "quality_score": 0.85,
                "requires_review": False,
                "word_count": 1500
            }
        }
    ]

    # 6. 执行路由测试
    print("\n=== 路由测试结果 ===")
    for scenario in scenarios:
        context = RouteContext(
            task_id="test_task",
            current_node="current",
            state=scenario["state"],
            history=[]
        )

        result = await engine.route(context)

        print(f"\n场景: {scenario['name']}")
        print(f"  规则ID: {result.rule_id}")
        print(f"  动作: {result.action.value}")
        print(f"  目标: {result.target}")
        print(f"  执行时间: {result.executed_at.strftime('%H:%M:%S')}")

    # 7. 显示路由统计
    print("\n=== 路由统计 ===")
    stats = engine.get_stats()
    for key, value in stats.items():
        if key != "rule_matches" and key != "custom_routes":
            print(f"{key}: {value}")

    print("\n规则匹配次数:")
    for rule_id, count in stats["rule_matches"].items():
        print(f"  {rule_id}: {count}")

    print("\n自定义路由次数:")
    for func_name, count in stats["custom_routes"].items():
        print(f"  {func_name}: {count}")


# ============================================================================
# 7. 高级功能：动态规则更新
# ============================================================================

class DynamicRuleUpdater:
    """动态规则更新器

    支持运行时更新路由规则。
    """

    def __init__(self, engine: AdvancedRoutingEngine):
        self.engine = engine
        self.rule_versions: Dict[str, int] = {}

    async def update_rule(
        self,
        rule_id: str,
        new_conditions: List[Dict[str, Any]]
    ):
        """更新规则条件"""
        # 查找规则
        for rule in self.engine.rules:
            if rule.rule_id == rule_id:
                rule.conditions = new_conditions
                self.rule_versions[rule_id] = self.rule_versions.get(rule_id, 0) + 1
                logger.info(f"Updated rule {rule_id} to version {self.rule_versions[rule_id]}")
                break

    async def enable_rule(self, rule_id: str):
        """启用规则"""
        for rule in self.engine.rules:
            if rule.rule_id == rule_id:
                rule.enabled = True
                logger.info(f"Enabled rule {rule_id}")
                break

    async def disable_rule(self, rule_id: str):
        """禁用规则"""
        for rule in self.engine.rules:
            if rule.rule_id == rule_id:
                rule.enabled = False
                logger.info(f"Disabled rule {rule_id}")
                break


# ============================================================================
# 8. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_custom_routing())
