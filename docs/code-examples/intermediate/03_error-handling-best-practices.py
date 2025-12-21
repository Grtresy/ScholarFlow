#!/usr/bin/env python3
"""
高级代码示例3: 错误处理最佳实践
===================================

本示例展示如何构建健壮的错误处理系统，
包括错误分类、重试机制、恢复策略和监控告警。

功能特性:
- 多层级错误分类
- 智能重试策略
- 错误恢复机制
- 熔断器模式
- 错误聚合与分析
- 实时告警
- 错误追踪

作者: Claude Code
版本: 1.0
"""

import asyncio
import logging
from typing import (
    TypedDict, List, Optional, Dict, Any, Callable,
    Type, Union, Awaitable
)
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import traceback
from functools import wraps
import uuid
from collections import defaultdict, deque
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 错误分类体系
# ============================================================================

class ErrorCategory(Enum):
    """错误类别"""
    NETWORK = "network"              # 网络错误
    TIMEOUT = "timeout"              # 超时错误
    AUTHENTICATION = "authentication"  # 认证错误
    AUTHORIZATION = "authorization"  # 授权错误
    VALIDATION = "validation"        # 验证错误
    BUSINESS_LOGIC = "business_logic"  # 业务逻辑错误
    RESOURCE = "resource"            # 资源错误
    SYSTEM = "system"                # 系统错误
    EXTERNAL_SERVICE = "external_service"  # 外部服务错误
    UNKNOWN = "unknown"              # 未知错误


class ErrorSeverity(Enum):
    """错误严重性"""
    CRITICAL = "critical"    # 严重错误，影响核心功能
    HIGH = "high"            # 高严重性错误
    MEDIUM = "medium"        # 中等严重性错误
    LOW = "low"              # 低严重性错误


class ErrorRecoverability(Enum):
    """错误可恢复性"""
    AUTOMATIC = "automatic"    # 可自动恢复
    MANUAL = "manual"          # 需要人工干预
    NOT_RECOVERABLE = "not_recoverable"  # 不可恢复


class ErrorScope(Enum):
    """错误作用域"""
    TASK = "task"              # 单个任务
    BATCH = "batch"            # 批量任务
    USER = "user"              # 用户级别
    SYSTEM = "system"          # 系统级别


@dataclass
class ErrorInfo:
    """错误信息"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    recoverability: ErrorRecoverability
    scope: ErrorScope
    error_type: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_id": self.error_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "recoverability": self.recoverability.value,
            "scope": self.scope.value,
            "error_type": self.error_type,
            "message": self.message,
            "details": self.details,
            "stack_trace": self.stack_trace,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "retry_count": self.retry_count,
            "resolved": self.resolved,
        }


# ============================================================================
# 2. 错误分类器
# ============================================================================

class ErrorClassifier:
    """错误分类器

    智能分类错误类型，确定严重性和可恢复性。
    """

    # 错误类型映射
    ERROR_MAPPINGS = {
        # 网络错误
        ConnectionError: (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, ErrorRecoverability.AUTOMATIC),
        ConnectionRefusedError: (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, ErrorRecoverability.AUTOMATIC),
        ConnectionResetError: (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, ErrorRecoverability.AUTOMATIC),
        TimeoutError: (ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM, ErrorRecoverability.AUTOMATIC),

        # 认证/授权错误
        PermissionError: (ErrorCategory.AUTHORIZATION, ErrorSeverity.HIGH, ErrorRecoverability.MANUAL),
        AuthenticationError: (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, ErrorRecoverability.MANUAL),

        # 验证错误
        ValueError: (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM, ErrorRecoverability.MANUAL),
        TypeError: (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM, ErrorRecoverability.MANUAL),

        # 资源错误
        FileNotFoundError: (ErrorCategory.RESOURCE, ErrorSeverity.HIGH, ErrorRecoverability.MANUAL),
        MemoryError: (ErrorCategory.RESOURCE, ErrorSeverity.CRITICAL, ErrorRecoverability.NOT_RECOVERABLE),
        DiskFullError: (ErrorCategory.RESOURCE, ErrorSeverity.CRITICAL, ErrorRecoverability.NOT_RECOVERABLE),

        # 系统错误
        SystemError: (ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL, ErrorRecoverability.NOT_RECOVERABLE),
        KeyboardInterrupt: (ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL, ErrorRecoverability.NOT_RECOVERABLE),

        # HTTP错误
        "404": (ErrorCategory.RESOURCE, ErrorSeverity.MEDIUM, ErrorRecoverability.MANUAL),
        "500": (ErrorCategory.EXTERNAL_SERVICE, ErrorSeverity.HIGH, ErrorRecoverability.AUTOMATIC),
        "503": (ErrorCategory.EXTERNAL_SERVICE, ErrorSeverity.HIGH, ErrorRecoverability.AUTOMATIC),
    }

    @classmethod
    def classify_error(cls, error: Exception) -> ErrorInfo:
        """分类错误"""

        error_type = type(error).__name__

        # 查找预定义映射
        mapping = cls.ERROR_MAPPINGS.get(error_type)

        if mapping:
            category, severity, recoverability = mapping
        else:
            # 默认分类
            category = ErrorCategory.UNKNOWN
            severity = ErrorSeverity.MEDIUM
            recoverability = ErrorRecoverability.MANUAL

        # 根据错误消息调整严重性
        message = str(error).lower()
        if any(keyword in message for keyword in ["critical", "fatal", "severe"]):
            severity = ErrorSeverity.CRITICAL
        elif any(keyword in message for keyword in ["warning", "minor", "low"]):
            severity = ErrorSeverity.LOW

        # 确定作用域 (简化)
        scope = ErrorScope.TASK

        # 生成错误ID
        error_id = str(uuid.uuid4())

        # 创建错误信息
        error_info = ErrorInfo(
            error_id=error_id,
            category=category,
            severity=severity,
            recoverability=recoverability,
            scope=scope,
            error_type=error_type,
            message=str(error),
            stack_trace=traceback.format_exc(),
        )

        return error_info


# ============================================================================
# 3. 错误处理器
# ============================================================================

class ErrorHandler:
    """错误处理器基类"""

    def __init__(self, handler_id: str):
        self.handler_id = handler_id
        self.logger = logging.getLogger(f"error_handler.{handler_id}")
        self.stats = {
            "errors_handled": 0,
            "errors_recovered": 0,
            "average_handling_time": 0.0,
        }

    async def handle_error(self, error_info: ErrorInfo) -> Optional[Dict[str, Any]]:
        """处理错误 (子类实现)"""
        raise NotImplementedError

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()


class NetworkErrorHandler(ErrorHandler):
    """网络错误处理器"""

    def __init__(self):
        super().__init__("network")

    async def handle_error(self, error_info: ErrorInfo) -> Optional[Dict[str, Any]]:
        """处理网络错误"""

        # 网络错误通常可以自动重试
        if error_info.recoverability == ErrorRecoverability.AUTOMATIC:
            return {
                "action": "retry",
                "delay": self._calculate_retry_delay(error_info),
                "max_retries": 5,
            }

        return {
            "action": "fail",
            "reason": "Network error requires manual intervention",
        }

    def _calculate_retry_delay(self, error_info: ErrorInfo) -> float:
        """计算重试延迟"""
        base_delay = 1.0
        exponential_factor = 2.0

        # 指数退避
        delay = base_delay * (exponential_factor ** error_info.retry_count)
        return min(delay, 60.0)  # 最大60秒


class ValidationErrorHandler(ErrorHandler):
    """验证错误处理器"""

    def __init__(self):
        super().__init__("validation")

    async def handle_error(self, error_info: ErrorInfo) -> Optional[Dict[str, Any]]:
        """处理验证错误"""

        # 验证错误需要修正输入
        return {
            "action": "fail",
            "reason": "Input validation failed",
            "suggestions": [
                "Check input parameters",
                "Verify data format",
                "Review validation rules",
            ],
        }


class ExternalServiceErrorHandler(ErrorHandler):
    """外部服务错误处理器"""

    def __init__(self):
        super().__init__("external_service")

    async def handle_error(self, error_info: ErrorInfo) -> Optional[Dict[str, Any]]:
        """处理外部服务错误"""

        # 检查服务状态
        if error_info.message.startswith("503"):
            return {
                "action": "retry",
                "delay": 5.0,
                "max_retries": 3,
                "fallback": True,  # 启用备用方案
            }

        return {
            "action": "fail",
            "reason": "External service error",
        }


# ============================================================================
# 4. 重试策略
# ============================================================================

class RetryManager:
    """重试管理器"""

    def __init__(self):
        self.retry_policies: Dict[str, Dict[str, Any]] = {
            "network": {
                "max_retries": 5,
                "base_delay": 1.0,
                "max_delay": 60.0,
                "backoff_factor": 2.0,
                "jitter": True,
            },
            "external_service": {
                "max_retries": 3,
                "base_delay": 2.0,
                "max_delay": 30.0,
                "backoff_factor": 2.0,
                "jitter": True,
            },
            "default": {
                "max_retries": 3,
                "base_delay": 1.0,
                "max_delay": 10.0,
                "backoff_factor": 1.5,
                "jitter": False,
            },
        }

    async def should_retry(self, error_info: ErrorInfo) -> bool:
        """判断是否应该重试"""
        if error_info.resolved:
            return False

        if error_info.recoverability == ErrorRecoverability.NOT_RECOVERABLE:
            return False

        if error_info.retry_count >= 5:  # 最大重试次数
            return False

        return True

    async def calculate_delay(self, error_info: ErrorInfo) -> float:
        """计算重试延迟"""

        policy_key = error_info.category.value
        if policy_key not in self.retry_policies:
            policy_key = "default"

        policy = self.retry_policies[policy_key]

        base_delay = policy["base_delay"]
        backoff_factor = policy["backoff_factor"]
        max_delay = policy["max_delay"]

        # 计算延迟
        delay = base_delay * (backoff_factor ** error_info.retry_count)
        delay = min(delay, max_delay)

        # 添加抖动
        if policy.get("jitter"):
            import random
            jitter_range = delay * 0.1
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)


# ============================================================================
# 5. 熔断器
# ============================================================================

class CircuitBreaker:
    """熔断器模式实现

    防止连续失败导致的级联故障。
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.logger = logging.getLogger("circuit_breaker")

    async def call(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """通过熔断器调用函数"""

        if self.state == "OPEN":
            # 检查是否应该转换到半开状态
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                self.logger.info("Circuit breaker: HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            # 执行函数
            result = await func(*args, **kwargs)

            # 成功：重置失败计数
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                self.logger.info("Circuit breaker: CLOSED (recovered)")

            return result

        except self.expected_exception as e:
            # 失败：增加计数
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            # 检查是否应该打开熔断器
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.logger.warning(
                    f"Circuit breaker: OPEN (failures: {self.failure_count})"
                )

            raise

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置"""
        if not self.last_failure_time:
            return False

        return (datetime.now() - self.last_failure_time).total_seconds() >= self.recovery_timeout


# ============================================================================
# 6. 错误聚合器
# ============================================================================

class ErrorAggregator:
    """错误聚合器

    聚合相似错误，分析错误模式。
    """

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.error_history: deque = deque(maxlen=window_size)
        self.error_patterns: Dict[str, int] = defaultdict(int)

    def add_error(self, error_info: ErrorInfo):
        """添加错误到聚合器"""
        self.error_history.append(error_info)

        # 更新错误模式
        pattern_key = self._generate_pattern_key(error_info)
        self.error_patterns[pattern_key] += 1

    def _generate_pattern_key(self, error_info: ErrorInfo) -> str:
        """生成错误模式键"""
        return f"{error_info.category.value}:{error_info.error_type}"

    def get_error_trends(self) -> Dict[str, Any]:
        """获取错误趋势"""

        # 计算各错误类别的频率
        category_counts = defaultdict(int)
        severity_counts = defaultdict(int)

        for error in self.error_history:
            category_counts[error.category.value] += 1
            severity_counts[error.severity.value] += 1

        # 识别高频错误模式
        frequent_patterns = sorted(
            self.error_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # 计算错误率 (最近5分钟)
        now = datetime.now()
        recent_errors = [
            error for error in self.error_history
            if (now - error.timestamp).total_seconds() < 300
        ]

        error_rate = len(recent_errors) / 5  # 每分钟错误数

        return {
            "total_errors": len(self.error_history),
            "error_rate_per_minute": error_rate,
            "category_distribution": dict(category_counts),
            "severity_distribution": dict(severity_counts),
            "top_error_patterns": frequent_patterns,
            "recent_errors": len(recent_errors),
        }

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """检测异常错误模式"""

        anomalies = []

        # 检查错误率激增
        error_trends = self.get_error_trends()
        if error_trends["error_rate_per_minute"] > 10:  # 每分钟超过10个错误
            anomalies.append({
                "type": "high_error_rate",
                "message": "Error rate is abnormally high",
                "value": error_trends["error_rate_per_minute"],
                "threshold": 10,
            })

        # 检查特定模式重复
        for pattern, count in error_trends["top_error_patterns"]:
            if count > 20:  # 同一错误模式出现超过20次
                anomalies.append({
                    "type": "repetitive_error",
                    "message": f"Repetitive error pattern detected: {pattern}",
                    "pattern": pattern,
                    "count": count,
                })

        return anomalies


# ============================================================================
# 7. 错误管理系统
# ============================================================================

class ErrorManagementSystem:
    """错误管理系统

    统一管理错误处理、重试、熔断和监控。
    """

    def __init__(self):
        self.handlers: Dict[ErrorCategory, ErrorHandler] = {}
        self.retry_manager = RetryManager()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.aggregator = ErrorAggregator()
        self.error_log: List[ErrorInfo] = []
        self.alert_thresholds = {
            "error_rate_per_minute": 10,
            "critical_errors_per_hour": 5,
        }

    def register_handler(self, category: ErrorCategory, handler: ErrorHandler):
        """注册错误处理器"""
        self.handlers[category] = handler
        logger.info(f"Registered error handler: {category.value}")

    def register_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ):
        """注册熔断器"""
        self.circuit_breakers[name] = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
        logger.info(f"Registered circuit breaker: {name}")

    async def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """统一错误处理入口"""

        # 1. 分类错误
        error_info = ErrorClassifier.classify_error(error)
        if context:
            error_info.context = context

        # 2. 记录错误
        self._log_error(error_info)

        # 3. 添加到聚合器
        self.aggregator.add_error(error_info)

        # 4. 获取处理器
        handler = self.handlers.get(error_info.category)

        if handler:
            # 5. 处理器处理
            handling_result = await handler.handle_error(error_info)

            if handling_result:
                return handling_result

        # 6. 检查是否应该重试
        if await self.retry_manager.should_retry(error_info):
            delay = await self.retry_manager.calculate_delay(error_info)

            return {
                "action": "retry",
                "delay": delay,
                "error_id": error_info.error_id,
            }

        # 7. 无法处理
        return {
            "action": "fail",
            "error_id": error_info.error_id,
            "reason": "Unable to handle error",
        }

    async def execute_with_error_handling(
        self,
        func: Callable,
        *args,
        circuit_breaker_name: Optional[str] = None,
        **kwargs
    ) -> Any:
        """带错误处理的执行包装器"""

        # 使用熔断器 (如果指定)
        if circuit_breaker_name and circuit_breaker_name in self.circuit_breakers:
            circuit_breaker = self.circuit_breakers[circuit_breaker_name]
            return await circuit_breaker.call(func, *args, **kwargs)

        # 直接执行
        return await func(*args, **kwargs)

    def _log_error(self, error_info: ErrorInfo):
        """记录错误"""
        self.error_log.append(error_info)

        # 限制日志大小
        if len(self.error_log) > 1000:
            self.error_log = self.error_log[-500:]

        # 记录到日志
        self.logger.error(
            f"Error [{error_info.error_id}]: {error_info.message}",
            extra={
                "error_id": error_info.error_id,
                "category": error_info.category.value,
                "severity": error_info.severity.value,
                "context": error_info.context,
            }
        )

    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计"""
        trends = self.aggregator.get_error_trends()
        anomalies = self.aggregator.detect_anomalies()

        # 计算各严重性错误数量
        severity_counts = defaultdict(int)
        for error in self.error_log:
            severity_counts[error.severity.value] += 1

        return {
            "total_errors": len(self.error_log),
            "error_trends": trends,
            "anomalies": anomalies,
            "severity_counts": dict(severity_counts),
            "active_circuit_breakers": {
                name: cb.state
                for name, cb in self.circuit_breakers.items()
            },
            "alert_status": self._check_alerts(trends),
        }

    def _check_alerts(self, trends: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查是否需要告警"""
        alerts = []

        # 错误率告警
        if trends["error_rate_per_minute"] > self.alert_thresholds["error_rate_per_minute"]:
            alerts.append({
                "type": "error_rate",
                "message": f"Error rate ({trends['error_rate_per_minute']:.2f}/min) exceeds threshold",
                "severity": "high",
            })

        # 严重错误告警
        recent_critical = sum(
            1 for error in self.error_log
            if error.severity == ErrorSeverity.CRITICAL
            and (datetime.now() - error.timestamp).total_seconds() < 3600
        )

        if recent_critical > self.alert_thresholds["critical_errors_per_hour"]:
            alerts.append({
                "type": "critical_errors",
                "message": f"{recent_critical} critical errors in the last hour",
                "severity": "critical",
            })

        return alerts


# ============================================================================
# 8. 装饰器
# ============================================================================

def error_handling(ems: ErrorManagementSystem):
    """错误处理装饰器"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)

            except Exception as e:
                handling_result = await ems.handle_error(e, {
                    "function": func.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs),
                })

                # 根据处理结果决定
                if handling_result.get("action") == "retry":
                    # 等待后重试
                    await asyncio.sleep(handling_result["delay"])

                    # 重试执行
                    return await func(*args, **kwargs)

                # 其他情况抛出异常
                raise

        return wrapper
    return decorator


# ============================================================================
# 9. 使用示例
# ============================================================================

async def example_error_handling():
    """错误处理示例"""

    # 1. 创建错误管理系统
    ems = ErrorManagementSystem()

    # 2. 注册处理器
    ems.register_handler(ErrorCategory.NETWORK, NetworkErrorHandler())
    ems.register_handler(ErrorCategory.VALIDATION, ValidationErrorHandler())
    ems.register_handler(ErrorCategory.EXTERNAL_SERVICE, ExternalServiceErrorHandler())

    # 3. 注册熔断器
    ems.register_circuit_breaker(
        "external_api",
        failure_threshold=3,
        recovery_timeout=30
    )

    # 4. 使用装饰器
    @error_handling(ems)
    async def unreliable_operation():
        """模拟不可靠操作"""
        import random
        if random.random() < 0.7:  # 70%概率失败
            raise ConnectionError("Network connection failed")
        return "Success!"

    # 5. 执行操作
    try:
        for i in range(5):
            print(f"\nAttempt {i + 1}:")
            result = await unreliable_operation()
            print(f"Result: {result}")

    except Exception as e:
        print(f"Final error: {e}")

    # 6. 显示错误统计
    print("\n=== Error Statistics ===")
    stats = ems.get_error_statistics()
    print(json.dumps(stats, indent=2, default=str))


# ============================================================================
# 10. 高级功能：错误恢复策略
# ============================================================================

class ErrorRecoveryStrategy:
    """错误恢复策略"""

    @staticmethod
    async def circuit_breaker_recovery(
        error_info: ErrorInfo,
        circuit_breaker: CircuitBreaker
    ) -> Optional[Dict[str, Any]]:
        """熔断器恢复策略"""

        if error_info.category == ErrorCategory.EXTERNAL_SERVICE:
            # 外部服务错误，启用熔断器
            return {
                "action": "circuit_breaker",
                "state": circuit_breaker.state,
            }

        return None

    @staticmethod
    async def fallback_recovery(
        error_info: ErrorInfo,
        fallback_func: Callable
    ) -> Optional[Dict[str, Any]]:
        """备用方案恢复策略"""

        if error_info.category == ErrorCategory.EXTERNAL_SERVICE:
            # 执行备用方案
            try:
                result = await fallback_func()
                return {
                    "action": "fallback",
                    "result": result,
                    "note": "Used fallback due to error",
                }
            except Exception as e:
                return {
                    "action": "fail",
                    "reason": f"Fallback also failed: {e}",
                }

        return None


# ============================================================================
# 11. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_error_handling())
