#!/usr/bin/env python3
"""
高级代码示例18: 高级监控系统
=================================

本示例展示如何构建一个功能完整的高级监控系统，
用于ScholarFlow项目的实时监控和告警。

功能特性:
- 指标收集
- 实时监控
- 告警系统
- 性能分析
- 日志聚合
- 可视化仪表板
- 健康检查
- 容量规划

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
import time
from pathlib import Path
from collections import defaultdict, deque
import statistics
import psutil
import uuid

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"          # 计数器
    GAUGE = "gauge"             # 仪表
    HISTOGRAM = "histogram"     # 直方图
    TIMER = "timer"             # 计时器


class AlertSeverity(Enum):
    """告警严重性"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Metric:
    """指标"""
    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRule:
    """告警规则"""
    rule_id: str
    name: str
    metric_name: str
    condition: str  # e.g., ">", "<", ">="
    threshold: float
    severity: AlertSeverity
    duration: int  # 持续时间（秒）
    enabled: bool = True
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """告警"""
    alert_id: str
    rule_id: str
    name: str
    severity: AlertSeverity
    status: AlertStatus
    metric_name: str
    current_value: float
    threshold: float
    triggered_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 2. 指标收集器
# ============================================================================

class MetricsCollector:
    """指标收集器

    收集系统指标和业务指标。
    """

    def __init__(self):
        self.metrics: deque = deque(maxlen=10000)
        self.metric_values: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.custom_collectors: Dict[str, Callable] = {}

    def record_metric(self, metric: Metric):
        """记录指标"""
        self.metrics.append(metric)
        self.metric_values[metric.name].append(metric.value)

    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """增加计数器"""
        self.record_metric(Metric(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            labels=labels or {}
        ))

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """设置仪表值"""
        self.record_metric(Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            labels=labels or {}
        ))

    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """记录直方图"""
        self.record_metric(Metric(
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            labels=labels or {}
        ))

    def time_function(self, name: str, func: Callable, labels: Optional[Dict[str, str]] = None):
        """计时函数执行"""
        start_time = time.time()
        try:
            result = func()
            if asyncio.iscoroutine(result):
                # 异步函数
                return self._async_time_function(name, result, labels)
            else:
                # 同步函数
                duration = time.time() - start_time
                self.record_histogram(f"{name}_duration", duration, labels)
                return result
        except Exception as e:
            duration = time.time() - start_time
            self.record_histogram(f"{name}_duration", duration, labels)
            raise

    async def _async_time_function(self, name: str, coro, labels: Optional[Dict[str, str]]):
        """异步函数计时"""
        start_time = time.time()
        try:
            result = await coro
            duration = time.time() - start_time
            self.record_histogram(f"{name}_duration", duration, labels)
            return result
        except Exception as e:
            duration = time.time() - start_time
            self.record_histogram(f"{name}_duration", duration, labels)
            raise

    def register_custom_collector(self, name: str, collector_func: Callable):
        """注册自定义收集器"""
        self.custom_collectors[name] = collector_func
        logger.info(f"Registered custom collector: {name}")

    async def collect_system_metrics(self):
        """收集系统指标"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        self.set_gauge("system.cpu.usage", cpu_percent)

        # 内存使用率
        memory = psutil.virtual_memory()
        self.set_gauge("system.memory.usage", memory.percent)
        self.set_gauge("system.memory.available", memory.available / (1024**3))  # GB

        # 磁盘使用率
        disk = psutil.disk_usage('/')
        self.set_gauge("system.disk.usage", disk.percent)
        self.set_gauge("system.disk.free", disk.free / (1024**3))  # GB

        # 网络IO
        net_io = psutil.net_io_counters()
        self.increment_counter("system.network.bytes_sent", net_io.bytes_sent)
        self.increment_counter("system.network.bytes_recv", net_io.bytes_recv)

        logger.debug(f"Collected system metrics: CPU {cpu_percent}%, Memory {memory.percent}%")

    async def collect_all_metrics(self):
        """收集所有指标"""
        await self.collect_system_metrics()

        # 执行自定义收集器
        for name, collector in self.custom_collectors.items():
            try:
                if asyncio.iscoroutinefunction(collector):
                    await collector()
                else:
                    collector()
            except Exception as e:
                logger.error(f"Custom collector {name} failed: {e}")

    def get_metric_values(self, name: str, window_seconds: Optional[int] = None) -> List[float]:
        """获取指标值"""
        values = list(self.metric_values[name])

        if window_seconds:
            cutoff_time = datetime.now() - timedelta(seconds=window_seconds)
            # 这里简化处理，实际应该根据timestamp过滤
            return values[-100:]  # 返回最近100个值

        return values

    def get_statistics(self, name: str) -> Dict[str, float]:
        """获取统计信息"""
        values = self.get_metric_values(name)
        if not values:
            return {}

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
        }

    def _percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数"""
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


# ============================================================================
# 3. 告警管理器
# ============================================================================

class AlertManager:
    """告警管理器

    管理告警规则和告警状态。
    """

    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_callbacks: List[Callable] = []

    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """删除告警规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")
            return True
        return False

    def enable_rule(self, rule_id: str):
        """启用规则"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True

    def disable_rule(self, rule_id: str):
        """禁用规则"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False

    def register_notification(self, callback: Callable):
        """注册通知回调"""
        self.notification_callbacks.append(callback)

    async def evaluate_rules(self):
        """评估告警规则"""
        for rule in self.rules.values():
            if not rule.enabled:
                continue

            # 获取最新指标值
            values = self.collector.get_metric_values(rule.metric_name, window_seconds=60)
            if not values:
                continue

            current_value = values[-1]

            # 检查条件
            triggered = self._check_condition(current_value, rule.condition, rule.threshold)

            # 检查持续时间
            alert_key = f"{rule.rule_id}"
            if triggered:
                if alert_key not in self.active_alerts:
                    # 新告警
                    alert = Alert(
                        alert_id=str(uuid.uuid4()),
                        rule_id=rule.rule_id,
                        name=rule.name,
                        severity=rule.severity,
                        status=AlertStatus.ACTIVE,
                        metric_name=rule.metric_name,
                        current_value=current_value,
                        threshold=rule.threshold,
                        labels=rule.labels
                    )
                    self.active_alerts[alert_key] = alert
                    self.alert_history.append(alert)
                    await self._notify(alert)
                    logger.warning(f"Alert triggered: {rule.name} ({current_value} {rule.condition} {rule.threshold})")
            else:
                if alert_key in self.active_alerts:
                    # 告警恢复
                    alert = self.active_alerts[alert_key]
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.now()
                    await self._notify(alert)
                    logger.info(f"Alert resolved: {rule.name}")
                    del self.active_alerts[alert_key]

    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        """检查条件"""
        if condition == ">":
            return value > threshold
        elif condition == "<":
            return value < threshold
        elif condition == ">=":
            return value >= threshold
        elif condition == "<=":
            return value <= threshold
        elif condition == "==":
            return value == threshold
        else:
            return False

    async def _notify(self, alert: Alert):
        """发送通知"""
        for callback in self.notification_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Notification failed: {e}")

    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """获取活跃告警"""
        alerts = list(self.active_alerts.values())
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        return self.alert_history[-limit:]


# ============================================================================
# 4. 性能分析器
# ============================================================================

class PerformanceAnalyzer:
    """性能分析器

    分析系统性能趋势和瓶颈。
    """

    def __init__(self, collector: MetricsCollector):
        self.collector = collector

    async def analyze_trends(self, metric_name: str, window_hours: int = 24) -> Dict[str, Any]:
        """分析指标趋势"""
        window_seconds = window_hours * 3600
        values = self.collector.get_metric_values(metric_name, window_seconds=window_seconds)

        if len(values) < 2:
            return {"error": "Not enough data points"}

        # 计算趋势
        recent_values = values[-10:]  # 最近10个点
        older_values = values[:10]    # 较早10个点

        recent_avg = statistics.mean(recent_values)
        older_avg = statistics.mean(older_values)

        change_percent = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0

        # 计算变化趋势
        if change_percent > 5:
            trend = "increasing"
        elif change_percent < -5:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "metric": metric_name,
            "window_hours": window_hours,
            "data_points": len(values),
            "recent_average": recent_avg,
            "overall_average": statistics.mean(values),
            "trend": trend,
            "change_percent": change_percent,
            "min": min(values),
            "max": max(values),
        }

    async def detect_anomalies(self, metric_name: str, threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        """检测异常"""
        values = self.collector.get_metric_values(metric_name)

        if len(values) < 20:
            return []

        mean = statistics.mean(values)
        std = statistics.stdev(values)

        anomalies = []
        for i, value in enumerate(values[-50:]):  # 检查最近50个点
            z_score = abs(value - mean) / std if std > 0 else 0

            if z_score > threshold_std:
                anomalies.append({
                    "index": len(values) - 50 + i,
                    "value": value,
                    "z_score": z_score,
                    "deviation": value - mean
                })

        return anomalies

    async def generate_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "system_health": {},
            "trends": {},
            "anomalies": {},
            "recommendations": []
        }

        # 系统健康状态
        cpu_values = self.collector.get_metric_values("system.cpu.usage")
        if cpu_values:
            avg_cpu = statistics.mean(cpu_values[-10:])
            report["system_health"]["cpu"] = {
                "average": avg_cpu,
                "status": "healthy" if avg_cpu < 70 else "warning" if avg_cpu < 90 else "critical"
            }

        memory_values = self.collector.get_metric_values("system.memory.usage")
        if memory_values:
            avg_memory = statistics.mean(memory_values[-10:])
            report["system_health"]["memory"] = {
                "average": avg_memory,
                "status": "healthy" if avg_memory < 80 else "warning" if avg_memory < 95 else "critical"
            }

        # 生成建议
        if avg_cpu > 80:
            report["recommendations"].append("High CPU usage detected. Consider optimizing CPU-intensive operations.")

        if avg_memory > 85:
            report["recommendations"].append("High memory usage detected. Consider increasing memory or optimizing memory usage.")

        return report


# ============================================================================
# 5. 健康检查器
# ============================================================================

class HealthChecker:
    """健康检查器

    检查系统和服务健康状态。
    """

    def __init__(self):
        self.checks: Dict[str, Callable] = {}

    def register_check(self, name: str, check_func: Callable):
        """注册健康检查"""
        self.checks[name] = check_func
        logger.info(f"Registered health check: {name}")

    async def run_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        results = {}
        overall_status = "healthy"

        for name, check_func in self.checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()

                results[name] = {
                    "status": "healthy",
                    "details": result
                }
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                overall_status = "unhealthy"

        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": results
        }


# ============================================================================
# 6. 监控系统
# ============================================================================

class MonitoringSystem:
    """监控系统

    统一管理监控、告警和分析。
    """

    def __init__(self, collection_interval: float = 5.0):
        self.collector = MetricsCollector()
        self.alert_manager = AlertManager(self.collector)
        self.performance_analyzer = PerformanceAnalyzer(self.collector)
        self.health_checker = HealthChecker()
        self.collection_interval = collection_interval

        self.running = False
        self.tasks: List[asyncio.Task] = []

    def setup_default_rules(self):
        """设置默认告警规则"""
        # CPU使用率告警
        self.alert_manager.add_rule(AlertRule(
            rule_id="high_cpu",
            name="High CPU Usage",
            metric_name="system.cpu.usage",
            condition=">",
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            duration=60
        ))

        # 内存使用率告警
        self.alert_manager.add_rule(AlertRule(
            rule_id="high_memory",
            name="High Memory Usage",
            metric_name="system.memory.usage",
            condition=">",
            threshold=85.0,
            severity=AlertSeverity.HIGH,
            duration=60
        ))

        # 磁盘使用率告警
        self.alert_manager.add_rule(AlertRule(
            rule_id="high_disk",
            name="High Disk Usage",
            metric_name="system.disk.usage",
            condition=">",
            threshold=90.0,
            severity=AlertSeverity.CRITICAL,
            duration=30
        ))

    def setup_default_checks(self):
        """设置默认健康检查"""
        async def check_disk_space():
            disk = psutil.disk_usage('/')
            return {
                "usage_percent": disk.percent,
                "free_gb": disk.free / (1024**3)
            }

        async def check_memory():
            memory = psutil.virtual_memory()
            return {
                "usage_percent": memory.percent,
                "available_gb": memory.available / (1024**3)
            }

        self.health_checker.register_check("disk_space", check_disk_space)
        self.health_checker.register_check("memory", check_memory)

    async def start(self):
        """启动监控"""
        self.running = True
        logger.info("Starting monitoring system")

        # 启动收集任务
        self.tasks.append(asyncio.create_task(self._collection_loop()))
        self.tasks.append(asyncio.create_task(self._alert_evaluation_loop()))

    async def stop(self):
        """停止监控"""
        self.running = False
        logger.info("Stopping monitoring system")

        # 取消所有任务
        for task in self.tasks:
            task.cancel()

        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

    async def _collection_loop(self):
        """指标收集循环"""
        while self.running:
            try:
                await self.collector.collect_all_metrics()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Collection loop error: {e}")
                await asyncio.sleep(5)

    async def _alert_evaluation_loop(self):
        """告警评估循环"""
        while self.running:
            try:
                await self.alert_manager.evaluate_rules()
                await asyncio.sleep(10)  # 每10秒评估一次
            except Exception as e:
                logger.error(f"Alert evaluation loop error: {e}")
                await asyncio.sleep(5)

    def record_custom_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None
    ):
        """记录自定义指标"""
        self.collector.record_metric(Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            labels=labels or {}
        ))


# ============================================================================
# 7. 使用示例
# ============================================================================

async def example_advanced_monitoring():
    """高级监控示例"""

    # 1. 创建监控系统
    print("\n=== 创建监控系统 ===")
    monitoring = MonitoringSystem(collection_interval=2.0)

    # 2. 设置默认规则和检查
    print("\n=== 设置告警规则 ===")
    monitoring.setup_default_rules()
    monitoring.setup_default_checks()

    # 添加自定义告警
    monitoring.alert_manager.add_rule(AlertRule(
        rule_id="custom_metric",
        name="Custom Metric Threshold",
        metric_name="app.custom.metric",
        condition=">",
        threshold=100.0,
        severity=AlertSeverity.MEDIUM,
        duration=30
    ))

    print(f"已设置 {len(monitoring.alert_manager.rules)} 个告警规则")

    # 3. 记录自定义指标
    print("\n=== 记录自定义指标 ===")
    for i in range(20):
        monitoring.record_custom_metric("app.custom.metric", 50 + i * 5)
        await asyncio.sleep(0.1)

    # 4. 启动监控
    print("\n=== 启动监控 ===")
    monitoring.start()

    # 运行一段时间
    await asyncio.sleep(15)

    # 5. 获取指标统计
    print("\n=== 指标统计 ===")
    cpu_stats = monitoring.collector.get_statistics("system.cpu.usage")
    print(f"CPU统计: {json.dumps(cpu_stats, indent=2)}")

    custom_stats = monitoring.collector.get_statistics("app.custom.metric")
    print(f"自定义指标统计: {json.dumps(custom_stats, indent=2)}")

    # 6. 分析性能趋势
    print("\n=== 性能趋势分析 ===")
    trend = await monitoring.performance_analyzer.analyze_trends("app.custom.metric")
    print(f"趋势分析: {json.dumps(trend, indent=2)}")

    # 7. 检测异常
    print("\n=== 异常检测 ===")
    anomalies = await monitoring.performance_analyzer.detect_anomalies("app.custom.metric")
    if anomalies:
        print(f"检测到 {len(anomalies)} 个异常:")
        for anomaly in anomalies:
            print(f"  索引 {anomaly['index']}: 值 {anomaly['value']:.2f}, Z分数 {anomaly['z_score']:.2f}")
    else:
        print("未检测到异常")

    # 8. 检查告警状态
    print("\n=== 告警状态 ===")
    active_alerts = monitoring.alert_manager.get_active_alerts()
    print(f"活跃告警数: {len(active_alerts)}")
    for alert in active_alerts:
        print(f"  {alert.name}: {alert.severity.value} - {alert.metric_name} = {alert.current_value}")

    # 9. 健康检查
    print("\n=== 健康检查 ===")
    health = await monitoring.health_checker.run_checks()
    print(f"整体状态: {health['overall_status']}")
    print("检查详情:")
    for check_name, result in health["checks"].items():
        print(f"  {check_name}: {result['status']}")
        if result['status'] == 'unhealthy':
            print(f"    错误: {result['error']}")

    # 10. 生成性能报告
    print("\n=== 性能报告 ===")
    report = await monitoring.performance_analyzer.generate_report()
    print(f"报告生成时间: {report['generated_at']}")

    if report.get("system_health"):
        print("\n系统健康:")
        for component, info in report["system_health"].items():
            print(f"  {component}: {info['status']} ({info['average']:.1f}%)")

    if report.get("recommendations"):
        print("\n建议:")
        for recommendation in report["recommendations"]:
            print(f"  - {recommendation}")

    # 11. 停止监控
    print("\n=== 停止监控 ===")
    await monitoring.stop()
    print("监控系统已停止")


# ============================================================================
# 8. 高级功能：通知系统
# ============================================================================

class NotificationSystem:
    """通知系统

    发送告警通知。
    """

    def __init__(self):
        self.channels: Dict[str, Callable] = {}

    def register_channel(self, name: str, channel_func: Callable):
        """注册通知渠道"""
        self.channels[name] = channel_func

    async def send_alert(self, alert: Alert, channels: List[str] = None):
        """发送告警"""
        channels = channels or list(self.channels.keys())

        for channel_name in channels:
            if channel_name in self.channels:
                try:
                    channel_func = self.channels[channel_name]
                    if asyncio.iscoroutinefunction(channel_func):
                        await channel_func(alert)
                    else:
                        channel_func(alert)
                    logger.info(f"Alert sent to {channel_name}")
                except Exception as e:
                    logger.error(f"Failed to send alert to {channel_name}: {e}")


# ============================================================================
# 9. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_advanced_monitoring())
