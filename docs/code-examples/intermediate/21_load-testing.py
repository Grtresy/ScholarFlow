#!/usr/bin/env python3
"""
高级代码示例21: 负载测试系统
=================================

本示例展示如何构建一个功能完整的负载测试系统，
用于ScholarFlow项目的性能压力测试。

功能特性:
- 并发请求生成
- 负载模式控制
- 性能指标收集
- 实时监控
- 结果分析
- 瓶颈检测
- 报告生成
- 自动化测试

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
import statistics
from collections import defaultdict, deque
import aiohttp
import random
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class LoadPattern(Enum):
    """负载模式"""
    CONSTANT = "constant"      # 恒定负载
    RAMP_UP = "ramp_up"        # 逐渐增加
    RAMP_DOWN = "ramp_down"    # 逐渐减少
    SPIKE = "spike"           # 突发负载
    SOAK = "soak"             # 长时间稳定
    CUSTOM = "custom"         # 自定义


class MetricType(Enum):
    """指标类型"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CONCURRENT_USERS = "concurrent_users"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"


@dataclass
class LoadTestConfig:
    """负载测试配置"""
    test_name: str
    base_url: str
    endpoints: List[Dict[str, Any]]
    load_pattern: LoadPattern
    duration: int  # 持续时间（秒）
    ramp_up_time: int = 0  # 预热时间
    concurrent_users: int = 10
    max_users: Optional[int] = None
    think_time: float = 1.0  # 用户思考时间
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestResult:
    """请求结果"""
    request_id: str
    endpoint: str
    method: str
    start_time: datetime
    end_time: datetime
    duration: float
    status_code: int
    success: bool
    error: Optional[str] = None
    response_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadTestMetrics:
    """负载测试指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    avg_response_time: float = 0.0
    p50_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    requests_per_second: float = 0.0
    error_rate: float = 0.0
    concurrent_users: int = 0


@dataclass
class LoadTestReport:
    """负载测试报告"""
    test_name: str
    config: LoadTestConfig
    start_time: datetime
    end_time: datetime
    duration: float
    metrics: LoadTestMetrics
    results: List[RequestResult]
    analysis: Dict[str, Any]
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.now)


# ============================================================================
# 2. 负载生成器
# ============================================================================

class LoadGenerator:
    """负载生成器

    根据负载模式生成用户请求。
    """

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.running = False
        self.current_users = 0
        self.target_users = config.concurrent_users

    def calculate_user_count(self, elapsed_time: float) -> int:
        """根据负载模式计算用户数"""
        if self.config.load_pattern == LoadPattern.CONSTANT:
            return self.config.concurrent_users

        elif self.config.load_pattern == LoadPattern.RAMP_UP:
            if elapsed_time < self.config.ramp_up_time:
                progress = elapsed_time / self.config.ramp_up_time
                return int(self.config.concurrent_users * progress)
            return self.config.concurrent_users

        elif self.config.load_pattern == LoadPattern.RAMP_DOWN:
            if elapsed_time < self.config.ramp_up_time:
                progress = elapsed_time / self.config.ramp_up_time
                return self.config.concurrent_users
            else:
                remaining_time = self.config.duration - elapsed_time
                if remaining_time > 0:
                    progress = remaining_time / (self.config.duration - self.config.ramp_up_time)
                    return int(self.config.concurrent_users * progress)
            return 0

        elif self.config.load_pattern == LoadPattern.SPIKE:
            # 前半段低负载，后半段高负载
            if elapsed_time < self.config.duration * 0.7:
                return self.config.concurrent_users // 4
            else:
                return self.config.concurrent_users * 2

        elif self.config.load_pattern == LoadPattern.SOAK:
            return self.config.concurrent_users

        else:  # CUSTOM
            return self.config.concurrent_users

    def should_continue(self, elapsed_time: float) -> bool:
        """判断是否继续生成负载"""
        return elapsed_time < self.config.duration


# ============================================================================
# 3. HTTP客户端
# ============================================================================

class HTTPClient:
    """HTTP客户端"""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> tuple[int, Dict[str, Any]]:
        """发起HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            async with self.session.request(method, url, **kwargs) as response:
                end_time = time.time()
                duration = end_time - start_time

                try:
                    data = await response.json()
                except:
                    data = await response.text()

                return response.status, data, duration

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            raise


# ============================================================================
# 4. 虚拟用户
# ============================================================================

class VirtualUser:
    """虚拟用户

    模拟真实用户的请求行为。
    """

    def __init__(
        self,
        user_id: str,
        config: LoadTestConfig,
        client: HTTPClient,
        results_queue: asyncio.Queue
    ):
        self.user_id = user_id
        self.config = config
        self.client = client
        self.results_queue = results_queue
        self.running = False

    async def start(self):
        """启动虚拟用户"""
        self.running = True
        start_time = time.time()

        while self.running:
            # 选择端点
            endpoint = random.choice(self.config.endpoints)

            # 发起请求
            await self._make_request(endpoint)

            # 思考时间
            if self.config.think_time > 0:
                await asyncio.sleep(self.config.think_time)

            # 检查是否超时
            elapsed = time.time() - start_time
            if elapsed >= self.config.duration:
                break

        self.running = False

    async def _make_request(self, endpoint: Dict[str, Any]):
        """发起请求"""
        method = endpoint.get("method", "GET")
        path = endpoint.get("path", "/")
        data = endpoint.get("data", {})
        headers = endpoint.get("headers", {})

        request_id = f"{self.user_id}_{int(time.time() * 1000)}"
        start_time = datetime.now()

        try:
            status_code, response_data, duration = await self.client.request(
                method,
                path,
                json=data if data else None,
                headers=headers
            )

            end_time = datetime.now()

            result = RequestResult(
                request_id=request_id,
                endpoint=path,
                method=method,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                status_code=status_code,
                success=200 <= status_code < 400,
                response_size=len(json.dumps(response_data)) if isinstance(response_data, dict) else 0
            )

        except Exception as e:
            end_time = datetime.now()

            result = RequestResult(
                request_id=request_id,
                endpoint=path,
                method=method,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                status_code=0,
                success=False,
                error=str(e)
            )

        await self.results_queue.put(result)

    def stop(self):
        """停止虚拟用户"""
        self.running = False


# ============================================================================
# 5. 负载测试引擎
# ============================================================================

class LoadTestEngine:
    """负载测试引擎

    执行负载测试并收集指标。
    """

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.results_queue = asyncio.Queue()
        self.results: List[RequestResult] = []
        self.metrics = LoadTestMetrics()
        self.running = False
        self.load_generator = LoadGenerator(config)

    async def run(self) -> LoadTestReport:
        """运行负载测试"""
        logger.info(f"Starting load test: {self.config.test_name}")
        start_time = time.time()
        self.running = True

        # 创建HTTP客户端
        async with HTTPClient(self.config.base_url, self.config.timeout) as client:
            # 启动虚拟用户
            users = []
            user_tasks = []

            test_start = time.time()

            while self.load_generator.should_continue(time.time() - test_start):
                # 计算当前应该有多少用户
                elapsed = time.time() - test_start
                target_users = self.load_generator.calculate_user_count(elapsed)

                # 调整用户数
                if target_users > len(users):
                    # 添加用户
                    for _ in range(target_users - len(users)):
                        user_id = f"user_{len(users)}"
                        user = VirtualUser(user_id, self.config, client, self.results_queue)
                        users.append(user)
                        task = asyncio.create_task(user.start())
                        user_tasks.append(task)
                        logger.debug(f"Added user: {user_id} (total: {len(users)})")

                elif target_users < len(users):
                    # 移除用户
                    for _ in range(len(users) - target_users):
                        user = users.pop()
                        user.stop()
                        logger.debug(f"Removed user: {user.user_id} (total: {len(users)})")

                # 更新指标
                self.metrics.concurrent_users = len(users)
                self.metrics.total_requests = len(self.results)

                # 处理结果
                await self._process_results()

                # 等待一秒
                await asyncio.sleep(1)

            # 停止所有用户
            for user in users:
                user.stop()

            # 等待所有任务完成
            if user_tasks:
                await asyncio.gather(*user_tasks, return_exceptions=True)

            # 处理剩余结果
            await self._process_results()

        test_end_time = time.time()
        self.running = False

        # 计算最终指标
        self._calculate_final_metrics(test_end_time - test_start)

        # 生成报告
        report = self._generate_report(start_time, test_end_time)

        logger.info(f"Load test completed: {self.config.test_name}")
        return report

    async def _process_results(self):
        """处理请求结果"""
        processed = 0
        max_process = 100  # 限制每次处理的数量

        while not self.results_queue.empty() and processed < max_process:
            try:
                result = await asyncio.wait_for(self.results_queue.get(), timeout=0.1)
                self.results.append(result)
                processed += 1

                # 更新实时指标
                if result.success:
                    self.metrics.successful_requests += 1
                else:
                    self.metrics.failed_requests += 1

            except asyncio.TimeoutError:
                break

    def _calculate_final_metrics(self, total_duration: float):
        """计算最终指标"""
        if not self.results:
            return

        # 响应时间统计
        response_times = [r.duration for r in self.results if r.success]
        if response_times:
            self.metrics.min_response_time = min(response_times)
            self.metrics.max_response_time = max(response_times)
            self.metrics.avg_response_time = statistics.mean(response_times)
            self.metrics.p50_response_time = statistics.median(response_times)
            self.metrics.p95_response_time = statistics.quantiles(response_times, n=100)[94]
            self.metrics.p99_response_time = statistics.quantiles(response_times, n=100)[98]

        # 吞吐量
        self.metrics.total_requests = len(self.results)
        self.metrics.successful_requests = sum(1 for r in self.results if r.success)
        self.metrics.failed_requests = sum(1 for r in self.results if not r.success)
        self.metrics.requests_per_second = self.metrics.total_requests / total_duration
        self.metrics.error_rate = (self.metrics.failed_requests / max(self.metrics.total_requests, 1)) * 100

    def _generate_report(self, start_time: datetime, end_time: datetime) -> LoadTestReport:
        """生成报告"""
        # 分析结果
        analysis = self._analyze_results()

        # 生成建议
        recommendations = self._generate_recommendations()

        report = LoadTestReport(
            test_name=self.config.test_name,
            config=self.config,
            start_time=start_time,
            end_time=end_time,
            duration=(end_time - start_time),
            metrics=self.metrics,
            results=self.results,
            analysis=analysis,
            recommendations=recommendations
        )

        return report

    def _analyze_results(self) -> Dict[str, Any]:
        """分析结果"""
        analysis = {
            "summary": {},
            "performance": {},
            "errors": {}
        }

        # 性能分析
        if self.metrics.avg_response_time > 2.0:
            analysis["performance"]["response_time"] = "poor"
        elif self.metrics.avg_response_time > 1.0:
            analysis["performance"]["response_time"] = "acceptable"
        else:
            analysis["performance"]["response_time"] = "good"

        if self.metrics.requests_per_second < 10:
            analysis["performance"]["throughput"] = "low"
        elif self.metrics.requests_per_second < 50:
            analysis["performance"]["throughput"] = "medium"
        else:
            analysis["performance"]["throughput"] = "high"

        # 错误分析
        if self.metrics.error_rate > 5:
            analysis["errors"]["error_rate"] = "high"
        elif self.metrics.error_rate > 1:
            analysis["errors"]["error_rate"] = "medium"
        else:
            analysis["errors"]["error_rate"] = "low"

        # 状态码分布
        status_codes = defaultdict(int)
        for result in self.results:
            status_codes[result.status_code] += 1

        analysis["status_codes"] = dict(status_codes)

        return analysis

    def _generate_recommendations(self) -> List[str]:
        """生成建议"""
        recommendations = []

        # 响应时间建议
        if self.metrics.avg_response_time > 2.0:
            recommendations.append(
                f"Average response time is {self.metrics.avg_response_time:.2f}s, "
                "consider optimizing backend performance or adding caching"
            )

        # 吞吐量建议
        if self.metrics.requests_per_second < 10:
            recommendations.append(
                f"Throughput is {self.metrics.requests_per_second:.2f} req/s, "
                "consider scaling horizontally or optimizing database queries"
            )

        # 错误率建议
        if self.metrics.error_rate > 5:
            recommendations.append(
                f"Error rate is {self.metrics.error_rate:.1f}%, "
                "investigate and fix error sources"
            )

        # 并发建议
        if self.config.concurrent_users < 50:
            recommendations.append(
                "Consider testing with higher concurrency to find breaking points"
            )

        return recommendations


# ============================================================================
# 6. 性能监控器
# ============================================================================

class PerformanceMonitor:
    """性能监控器

    监控系统资源使用情况。
    """

    def __init__(self):
        self.running = False
        self.metrics_queue = asyncio.Queue()
        self.metrics_history: deque = deque(maxlen=3600)  # 保留1小时数据

    async def start(self):
        """开始监控"""
        self.running = True
        asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """停止监控"""
        self.running = False

    async def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                # 收集系统指标
                cpu_percent = await self._get_cpu_usage()
                memory_percent = await self._get_memory_usage()

                metrics = {
                    "timestamp": time.time(),
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent
                }

                self.metrics_history.append(metrics)
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(5)

    async def _get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        return 50.0  # 模拟值

    async def _get_memory_usage(self) -> float:
        """获取内存使用率"""
        return 60.0  # 模拟值

    def get_current_metrics(self) -> Dict[str, float]:
        """获取当前指标"""
        if self.metrics_history:
            return dict(self.metrics_history[-1])
        return {}


# ============================================================================
# 7. 报告生成器
# ============================================================================

class LoadTestReportGenerator:
    """负载测试报告生成器"""

    def __init__(self, output_dir: str = "./load_test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_html_report(self, report: LoadTestReport) -> Path:
        """生成HTML报告"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Load Test Report - {report.test_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #e0e0e0; border-radius: 5px; }}
        .good {{ color: green; }}
        .warning {{ color: orange; }}
        .error {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Load Test Report: {report.test_name}</h1>
        <p>Generated at: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Duration: {report.duration:.2f} seconds</p>
    </div>

    <h2>Summary</h2>
    <div class="metric">
        <h3>Total Requests</h3>
        <p>{report.metrics.total_requests}</p>
    </div>
    <div class="metric">
        <h3>Success Rate</h3>
        <p>{(1 - report.metrics.error_rate / 100) * 100:.1f}%</p>
    </div>
    <div class="metric">
        <h3>Avg Response Time</h3>
        <p>{report.metrics.avg_response_time:.3f}s</p>
    </div>
    <div class="metric">
        <h3>Throughput</h3>
        <p>{report.metrics.requests_per_second:.2f} req/s</p>
    </div>
    <div class="metric">
        <h3>Max Concurrent Users</h3>
        <p>{report.metrics.concurrent_users}</p>
    </div>

    <h2>Performance Metrics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
        <tr>
            <td>Min Response Time</td>
            <td>{report.metrics.min_response_time:.3f}s</td>
        </tr>
        <tr>
            <td>Max Response Time</td>
            <td>{report.metrics.max_response_time:.3f}s</td>
        </tr>
        <tr>
            <td>Median (P50)</td>
            <td>{report.metrics.p50_response_time:.3f}s</td>
        </tr>
        <tr>
            <td>P95</td>
            <td>{report.metrics.p95_response_time:.3f}s</td>
        </tr>
        <tr>
            <td>P99</td>
            <td>{report.metrics.p99_response_time:.3f}s</td>
        </tr>
        <tr>
            <td>Error Rate</td>
            <td>{report.metrics.error_rate:.2f}%</td>
        </tr>
    </table>

    <h2>Recommendations</h2>
    <ul>
        {''.join(f'<li>{rec}</li>' for rec in report.recommendations)}
    </ul>
</body>
</html>
        """

        report_file = self.output_dir / f"load_test_report_{report.test_name}_{int(time.time())}.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"HTML report generated: {report_file}")
        return report_file

    def generate_json_report(self, report: LoadTestReport) -> Path:
        """生成JSON报告"""
        report_data = {
            "test_name": report.test_name,
            "config": {
                "base_url": report.config.base_url,
                "load_pattern": report.config.load_pattern.value,
                "duration": report.config.duration,
                "concurrent_users": report.config.concurrent_users
            },
            "metrics": {
                "total_requests": report.metrics.total_requests,
                "successful_requests": report.metrics.successful_requests,
                "failed_requests": report.metrics.failed_requests,
                "avg_response_time": report.metrics.avg_response_time,
                "p50_response_time": report.metrics.p50_response_time,
                "p95_response_time": report.metrics.p95_response_time,
                "p99_response_time": report.metrics.p99_response_time,
                "requests_per_second": report.metrics.requests_per_second,
                "error_rate": report.metrics.error_rate,
                "concurrent_users": report.metrics.concurrent_users
            },
            "analysis": report.analysis,
            "recommendations": report.recommendations,
            "generated_at": report.generated_at.isoformat()
        }

        report_file = self.output_dir / f"load_test_report_{report.test_name}_{int(time.time())}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"JSON report generated: {report_file}")
        return report_file


# ============================================================================
# 8. 使用示例
# ============================================================================

async def example_load_testing():
    """负载测试示例"""

    # 1. 创建负载测试配置
    print("\n=== 创建负载测试配置 ===")
    config = LoadTestConfig(
        test_name="API Load Test",
        base_url="http://localhost:8000",
        endpoints=[
            {"method": "GET", "path": "/api/health"},
            {"method": "GET", "path": "/api/tasks"},
            {"method": "POST", "path": "/api/tasks", "data": {"name": "Test Task"}},
        ],
        load_pattern=LoadPattern.RAMP_UP,
        duration=30,
        ramp_up_time=10,
        concurrent_users=5,
        think_time=0.5
    )

    print(f"测试名称: {config.test_name}")
    print(f"基础URL: {config.base_url}")
    print(f"负载模式: {config.load_pattern.value}")
    print(f"持续时间: {config.duration}s")
    print(f"并发用户: {config.concurrent_users}")
    print(f"端点数: {len(config.endpoints)}")

    # 2. 创建负载测试引擎
    print("\n=== 创建负载测试引擎 ===")
    engine = LoadTestEngine(config)

    # 3. 运行负载测试
    print("\n=== 运行负载测试 ===")
    print("测试进行中...")
    start_time = time.time()

    report = await engine.run()

    elapsed = time.time() - start_time
    print(f"\n测试完成! 总用时: {elapsed:.2f}s")

    # 4. 显示结果摘要
    print("\n=== 测试结果摘要 ===")
    metrics = report.metrics
    print(f"总请求数: {metrics.total_requests}")
    print(f"成功请求: {metrics.successful_requests}")
    print(f"失败请求: {metrics.failed_requests}")
    print(f"成功率: {(1 - metrics.error_rate / 100) * 100:.1f}%")
    print(f"平均响应时间: {metrics.avg_response_time:.3f}s")
    print(f"吞吐量: {metrics.requests_per_second:.2f} req/s")
    print(f"最大并发用户: {metrics.concurrent_users}")

    # 5. 显示性能指标
    print("\n=== 性能指标 ===")
    print(f"最小响应时间: {metrics.min_response_time:.3f}s")
    print(f"最大响应时间: {metrics.max_response_time:.3f}s")
    print(f"中位数 (P50): {metrics.p50_response_time:.3f}s")
    print(f"P95: {metrics.p95_response_time:.3f}s")
    print(f"P99: {metrics.p99_response_time:.3f}s")

    # 6. 显示分析结果
    print("\n=== 分析结果 ===")
    analysis = report.analysis
    print(f"响应时间评级: {analysis['performance']['response_time']}")
    print(f"吞吐量评级: {analysis['performance']['throughput']}")
    print(f"错误率评级: {analysis['errors']['error_rate']}")

    if analysis.get("status_codes"):
        print("\n状态码分布:")
        for code, count in analysis["status_codes"].items():
            print(f"  {code}: {count}")

    # 7. 显示建议
    print("\n=== 优化建议 ===")
    if report.recommendations:
        for rec in report.recommendations:
            print(f"  • {rec}")
    else:
        print("  无特殊建议")

    # 8. 生成报告
    print("\n=== 生成报告 ===")
    generator = LoadTestReportGenerator()

    html_file = generator.generate_html_report(report)
    json_file = generator.generate_json_report(report)

    print(f"HTML报告: {html_file}")
    print(f"JSON报告: {json_file}")

    # 9. 批量测试
    print("\n=== 批量测试示例 ===")
    test_configs = [
        (LoadPattern.CONSTANT, "Constant Load Test", 10),
        (LoadPattern.SPIKE, "Spike Load Test", 20),
        (LoadPattern.SOAK, "Soak Load Test", 5),
    ]

    for pattern, name, users in test_configs:
        test_config = LoadTestConfig(
            test_name=name,
            base_url="http://localhost:8000",
            endpoints=[{"method": "GET", "path": "/api/health"}],
            load_pattern=pattern,
            duration=15,
            concurrent_users=users
        )

        print(f"\n运行测试: {name}")
        test_engine = LoadTestEngine(test_config)
        test_report = await test_engine.run()

        print(f"  请求数: {test_report.metrics.total_requests}")
        print(f"  响应时间: {test_report.metrics.avg_response_time:.3f}s")
        print(f"  吞吐量: {test_report.metrics.requests_per_second:.2f} req/s")


# ============================================================================
# 9. 高级功能：自动化测试套件
# ============================================================================

class AutomatedLoadTestSuite:
    """自动化负载测试套件

    自动运行多个负载测试场景。
    """

    def __init__(self):
        self.test_scenarios: List[LoadTestConfig] = []
        self.reports: List[LoadTestReport] = []

    def add_scenario(self, config: LoadTestConfig):
        """添加测试场景"""
        self.test_scenarios.append(config)

    async def run_all(self) -> List[LoadTestReport]:
        """运行所有场景"""
        logger.info(f"Running {len(self.test_scenarios)} test scenarios")

        for config in self.test_scenarios:
            logger.info(f"Running scenario: {config.test_name}")
            engine = LoadTestEngine(config)
            report = await engine.run()
            self.reports.append(report)

        return self.reports

    def generate_comparison_report(self) -> Dict[str, Any]:
        """生成对比报告"""
        comparison = {
            "scenarios": [],
            "best_performance": {},
            "summary": {}
        }

        for report in self.reports:
            comparison["scenarios"].append({
                "name": report.test_name,
                "avg_response_time": report.metrics.avg_response_time,
                "throughput": report.metrics.requests_per_second,
                "error_rate": report.metrics.error_rate,
                "total_requests": report.metrics.total_requests
            })

        # 找出最佳性能
        if comparison["scenarios"]:
            best_response = min(comparison["scenarios"], key=lambda s: s["avg_response_time"])
            best_throughput = max(comparison["scenarios"], key=lambda s: s["throughput"])
            best_error = min(comparison["scenarios"], key=lambda s: s["error_rate"])

            comparison["best_performance"] = {
                "best_response_time": best_response["name"],
                "best_throughput": best_throughput["name"],
                "lowest_error_rate": best_error["name"]
            }

        return comparison


# ============================================================================
# 10. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_load_testing())
