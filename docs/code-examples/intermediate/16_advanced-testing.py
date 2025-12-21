#!/usr/bin/env python3
"""
高级代码示例16: 高级测试框架
=================================

本示例展示如何构建一个功能完整的高级测试系统，
用于ScholarFlow项目的全面质量保证。

功能特性:
- 单元测试框架
- 集成测试套件
- 端到端测试
- 测试数据管理
- 测试报告生成
- 覆盖率分析
- 并行测试执行
- 测试监控

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
import uuid
import traceback
from pathlib import Path
from collections import defaultdict, deque
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class TestStatus(Enum):
    """测试状态"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    RUNNING = "running"


class TestType(Enum):
    """测试类型"""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"


class TestSeverity(Enum):
    """测试严重性"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TestCase:
    """测试用例"""
    test_id: str
    name: str
    test_type: TestType
    severity: TestSeverity
    setup: Optional[Callable] = None
    test_func: Optional[Callable] = None
    teardown: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    timeout: float = 30.0
    retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    status: TestStatus
    duration: float
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    assertions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TestSuite:
    """测试套件"""
    suite_id: str
    name: str
    description: str
    tests: List[TestCase] = field(default_factory=list)
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestReport:
    """测试报告"""
    report_id: str
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    coverage: Dict[str, float] = field(default_factory=dict)
    results: List[TestResult] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


# ============================================================================
# 2. 测试断言库
# ============================================================================

class TestAssertions:
    """测试断言库

    提供丰富的断言方法。
    """

    @staticmethod
    def assert_equal(actual: Any, expected: Any, message: str = "") -> bool:
        """断言相等"""
        if actual != expected:
            raise AssertionError(
                f"{message}\nExpected: {expected}\nActual: {actual}"
            )
        return True

    @staticmethod
    def assert_not_equal(actual: Any, expected: Any, message: str = "") -> bool:
        """断言不相等"""
        if actual == expected:
            raise AssertionError(f"{message}\nExpected: {expected} to not equal {actual}")
        return True

    @staticmethod
    def assert_true(condition: Any, message: str = "") -> bool:
        """断言为真"""
        if not condition:
            raise AssertionError(f"{message}\nExpected condition to be True")
        return True

    @staticmethod
    def assert_false(condition: Any, message: str = "") -> bool:
        """断言为假"""
        if condition:
            raise AssertionError(f"{message}\nExpected condition to be False")
        return True

    @staticmethod
    def assert_is_none(value: Any, message: str = "") -> bool:
        """断言为None"""
        if value is not None:
            raise AssertionError(f"{message}\nExpected None but got {value}")
        return True

    @staticmethod
    def assert_is_not_none(value: Any, message: str = "") -> bool:
        """断言不为None"""
        if value is None:
            raise AssertionError(f"{message}\nExpected value to not be None")
        return True

    @staticmethod
    def assert_in(member: Any, container: Any, message: str = "") -> bool:
        """断言包含"""
        if member not in container:
            raise AssertionError(f"{message}\nExpected {member} to be in {container}")
        return True

    @staticmethod
    def assert_not_in(member: Any, container: Any, message: str = "") -> bool:
        """断言不包含"""
        if member in container:
            raise AssertionError(f"{message}\nExpected {member} to not be in {container}")
        return True

    @staticmethod
    def assert_is_instance(obj: Any, cls: type, message: str = "") -> bool:
        """断言类型"""
        if not isinstance(obj, cls):
            raise AssertionError(f"{message}\nExpected {obj} to be instance of {cls}")
        return True

    @staticmethod
    def assert_raises(
        exception_type: type,
        func: Callable,
        *args,
        **kwargs
    ) -> bool:
        """断言抛出异常"""
        try:
            func(*args, **kwargs)
            raise AssertionError(f"Expected {exception_type.__name__} to be raised")
        except exception_type:
            return True
        except Exception as e:
            raise AssertionError(
                f"Expected {exception_type.__name__} but got {type(e).__name__}: {e}"
            )

    @staticmethod
    def assert_less(actual: Any, expected: Any, message: str = "") -> bool:
        """断言小于"""
        if actual >= expected:
            raise AssertionError(f"{message}\nExpected {actual} < {expected}")
        return True

    @staticmethod
    def assert_greater(actual: Any, expected: Any, message: str = "") -> bool:
        """断言大于"""
        if actual <= expected:
            raise AssertionError(f"{message}\nExpected {actual} > {expected}")
        return True


# ============================================================================
# 3. 测试数据管理器
# ============================================================================

class TestDataManager:
    """测试数据管理器

    管理测试所需的数据和资源。
    """

    def __init__(self):
        self.data_store: Dict[str, Any] = {}
        self.temp_files: List[Path] = []

    def set(self, key: str, value: Any):
        """设置测试数据"""
        self.data_store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取测试数据"""
        return self.data_store.get(key, default)

    def create_temp_file(
        self,
        content: str,
        suffix: str = ".tmp"
    ) -> Path:
        """创建临时文件"""
        temp_file = Path(f"/tmp/test_{uuid.uuid4().hex[:8]}{suffix}")
        with open(temp_file, 'w') as f:
            f.write(content)
        self.temp_files.append(temp_file)
        return temp_file

    def cleanup(self):
        """清理资源"""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file}: {e}")

        self.data_store.clear()
        self.temp_files.clear()


# ============================================================================
# 4. 测试运行器
# ============================================================================

class TestRunner:
    """测试运行器

    执行测试用例并收集结果。
    """

    def __init__(self):
        self.data_manager = TestDataManager()
        self.assertions = TestAssertions()
        self.results: List[TestResult] = []

    async def run_test_case(
        self,
        test_case: TestCase,
        context: Optional[Dict[str, Any]] = None
    ) -> TestResult:
        """运行单个测试用例"""
        logger.info(f"Running test: {test_case.name}")
        start_time = time.time()

        result = TestResult(
            test_id=test_case.test_id,
            status=TestStatus.RUNNING,
            duration=0.0
        )

        try:
            # 设置超时
            async with asyncio.timeout(test_case.timeout):
                # 执行setup
                if test_case.setup:
                    await self._safe_execute(test_case.setup, context)

                # 执行测试
                if test_case.test_func:
                    await self._safe_execute(test_case.test_func, context)

                # 执行teardown
                if test_case.teardown:
                    await self._safe_execute(test_case.teardown, context)

                # 标记为通过
                result.status = TestStatus.PASSED

        except asyncio.TimeoutError:
            result.status = TestStatus.ERROR
            result.error_message = f"Test timed out after {test_case.timeout}s"

        except AssertionError as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.stack_trace = traceback.format_exc()

        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_message = f"Unexpected error: {str(e)}"
            result.stack_trace = traceback.format_exc()

        finally:
            result.duration = time.time() - start_time

        self.results.append(result)
        logger.info(f"Test {test_case.name}: {result.status.value} ({result.duration:.2f}s)")
        return result

    async def _safe_execute(
        self,
        func: Callable,
        context: Optional[Dict[str, Any]] = None
    ):
        """安全执行函数"""
        if asyncio.iscoroutinefunction(func):
            if context:
                await func(context)
            else:
                await func()
        else:
            if context:
                func(context)
            else:
                func()

    async def run_test_suite(
        self,
        test_suite: TestSuite,
        parallel: bool = False,
        max_workers: int = 4
    ) -> TestReport:
        """运行测试套件"""
        logger.info(f"Running test suite: {test_suite.name}")
        start_time = time.time()

        # 执行setup
        if test_suite.setup:
            await self._safe_execute(test_suite.setup)

        # 执行测试
        if parallel:
            await self._run_tests_parallel(test_suite.tests, max_workers)
        else:
            for test_case in test_suite.tests:
                await self.run_test_case(test_case)

        # 执行teardown
        if test_suite.teardown:
            await self._safe_execute(test_suite.teardown)

        # 生成报告
        duration = time.time() - start_time
        report = self._generate_report(test_suite, duration)

        return report

    async def _run_tests_parallel(
        self,
        test_cases: List[TestCase],
        max_workers: int
    ):
        """并行运行测试"""
        semaphore = asyncio.Semaphore(max_workers)

        async def run_with_semaphore(test_case: TestCase):
            async with semaphore:
                return await self.run_test_case(test_case)

        tasks = [run_with_semaphore(tc) for tc in test_cases]
        await asyncio.gather(*tasks)

    def _generate_report(self, test_suite: TestSuite, duration: float) -> TestReport:
        """生成测试报告"""
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
        errors = sum(1 for r in self.results if r.status == TestStatus.ERROR)

        return TestReport(
            report_id=str(uuid.uuid4()),
            suite_name=test_suite.name,
            total_tests=len(self.results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=duration,
            results=self.results.copy()
        )


# ============================================================================
# 5. 覆盖率分析器
# ============================================================================

class CoverageAnalyzer:
    """覆盖率分析器

    分析代码覆盖率。
    """

    def __init__(self):
        self.executed_lines: set = set()
        self.total_lines: set = set()
        self.branches: Dict[int, List[bool]] = {}

    def add_executed_line(self, file_path: str, line_number: int):
        """记录执行行"""
        key = f"{file_path}:{line_number}"
        self.executed_lines.add(key)

    def set_total_lines(self, file_path: str, line_count: int):
        """设置总行数"""
        for i in range(1, line_count + 1):
            key = f"{file_path}:{i}"
            self.total_lines.add(key)

    def get_coverage(self) -> Dict[str, float]:
        """获取覆盖率"""
        coverage = {}

        # 计算总体覆盖率
        covered = len(self.executed_lines & self.total_lines)
        total = len(self.total_lines)
        coverage["total"] = (covered / max(total, 1)) * 100

        # 按文件计算覆盖率
        file_coverage = defaultdict(int)
        file_total = defaultdict(int)

        for line in self.total_lines:
            file_path = line.split(":")[0]
            file_total[file_path] += 1

        for line in self.executed_lines:
            file_path = line.split(":")[0]
            file_coverage[file_path] += 1

        for file_path in file_total:
            coverage[file_path] = (file_coverage[file_path] / file_total[file_path]) * 100

        return coverage


# ============================================================================
# 6. 测试套件示例
# ============================================================================

class ExampleTestSuites:
    """示例测试套件"""

    @staticmethod
    def create_unit_tests(runner: TestRunner) -> TestSuite:
        """创建单元测试套件"""
        test_suite = TestSuite(
            suite_id="unit_001",
            name="Unit Tests",
            description="Basic unit tests"
        )

        # 测试1：基本断言
        async def test_basic_assertions(context):
            runner.assertions.assert_equal(1 + 1, 2)
            runner.assertions.assert_true(True)
            runner.assertions.assert_false(False)
            runner.assertions.assert_in("a", "abc")
            runner.assertions.assert_is_instance("test", str)

        test_case1 = TestCase(
            test_id="test_basic_assertions",
            name="Test Basic Assertions",
            test_type=TestType.UNIT,
            severity=TestSeverity.HIGH,
            test_func=test_basic_assertions
        )
        test_suite.tests.append(test_case1)

        # 测试2：异常处理
        async def test_exception_handling(context):
            def raise_error():
                raise ValueError("Test error")

            runner.assertions.assert_raises(ValueError, raise_error)

        test_case2 = TestCase(
            test_id="test_exception",
            name="Test Exception Handling",
            test_type=TestType.UNIT,
            severity=TestSeverity.HIGH,
            test_func=test_exception_handling
        )
        test_suite.tests.append(test_case2)

        # 测试3：测试数据管理
        async def test_data_management(context):
            runner.data_manager.set("test_key", "test_value")
            assert runner.data_manager.get("test_key") == "test_value"

        test_case3 = TestCase(
            test_id="test_data_mgmt",
            name="Test Data Management",
            test_type=TestType.UNIT,
            severity=TestSeverity.MEDIUM,
            test_func=test_data_management
        )
        test_suite.tests.append(test_case3)

        return test_suite

    @staticmethod
    def create_integration_tests(runner: TestRunner) -> TestSuite:
        """创建集成测试套件"""
        test_suite = TestSuite(
            suite_id="integration_001",
            name="Integration Tests",
            description="Integration tests"
        )

        # 测试：文件操作
        async def test_file_operations(context):
            temp_file = runner.data_manager.create_temp_file("Hello World")
            with open(temp_file, 'r') as f:
                content = f.read()
            runner.assertions.assert_equal(content, "Hello World")

        test_case = TestCase(
            test_id="test_file_ops",
            name="Test File Operations",
            test_type=TestType.INTEGRATION,
            severity=TestSeverity.HIGH,
            test_func=test_file_operations
        )
        test_suite.tests.append(test_case)

        return test_suite


# ============================================================================
# 7. 测试报告生成器
# ============================================================================

class TestReportGenerator:
    """测试报告生成器"""

    def __init__(self, output_dir: str = "./test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_html_report(self, report: TestReport) -> Path:
        """生成HTML报告"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Report - {report.suite_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background: #e0e0e0; padding: 15px; border-radius: 5px; text-align: center; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .skipped {{ color: orange; }}
        .error {{ color: purple; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Test Report: {report.suite_name}</h1>
        <p>Generated at: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="summary">
        <div class="metric">
            <h3>Total Tests</h3>
            <p>{report.total_tests}</p>
        </div>
        <div class="metric passed">
            <h3>Passed</h3>
            <p>{report.passed}</p>
        </div>
        <div class="metric failed">
            <h3>Failed</h3>
            <p>{report.failed}</p>
        </div>
        <div class="metric error">
            <h3>Errors</h3>
            <p>{report.errors}</p>
        </div>
        <div class="metric">
            <h3>Duration</h3>
            <p>{report.duration:.2f}s</p>
        </div>
    </div>

    <h2>Test Details</h2>
    <table>
        <tr>
            <th>Test Name</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Error Message</th>
        </tr>
        {self._generate_test_rows(report.results)}
    </table>
</body>
</html>
        """

        report_file = self.output_dir / f"report_{report.report_id}.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html)

        return report_file

    def _generate_test_rows(self, results: List[TestResult]) -> str:
        """生成测试行"""
        rows = []
        for result in results:
            status_class = result.status.value
            error_msg = result.error_message or ""
            rows.append(f"""
        <tr>
            <td>{result.test_id}</td>
            <td class="{status_class}">{result.status.value}</td>
            <td>{result.duration:.3f}s</td>
            <td>{error_msg}</td>
        </tr>
            """)
        return "".join(rows)

    def generate_json_report(self, report: TestReport) -> Path:
        """生成JSON报告"""
        report_data = {
            "report_id": report.report_id,
            "suite_name": report.suite_name,
            "summary": {
                "total_tests": report.total_tests,
                "passed": report.passed,
                "failed": report.failed,
                "skipped": report.skipped,
                "errors": report.errors,
                "duration": report.duration
            },
            "results": [
                {
                    "test_id": r.test_id,
                    "status": r.status.value,
                    "duration": r.duration,
                    "error_message": r.error_message
                }
                for r in report.results
            ],
            "generated_at": report.generated_at.isoformat()
        }

        report_file = self.output_dir / f"report_{report.report_id}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)

        return report_file


# ============================================================================
# 8. 使用示例
# ============================================================================

async def example_advanced_testing():
    """高级测试示例"""

    # 1. 创建测试运行器
    print("\n=== 创建测试运行器 ===")
    runner = TestRunner()

    # 2. 创建测试套件
    print("\n=== 创建测试套件 ===")
    unit_tests = ExampleTestSuites.create_unit_tests(runner)
    integration_tests = ExampleTestSuites.create_integration_tests(runner)

    print(f"单元测试数: {len(unit_tests.tests)}")
    print(f"集成测试数: {len(integration_tests.tests)}")

    # 3. 运行单元测试
    print("\n=== 运行单元测试 ===")
    unit_report = await runner.run_test_suite(unit_tests)

    print(f"测试套件: {unit_report.suite_name}")
    print(f"总测试数: {unit_report.total_tests}")
    print(f"通过: {unit_report.passed}")
    print(f"失败: {unit_report.failed}")
    print(f"错误: {unit_report.errors}")
    print(f"执行时间: {unit_report.duration:.2f}s")

    # 4. 运行集成测试
    print("\n=== 运行集成测试 ===")
    runner.results.clear()  # 清除之前的结果
    integration_report = await runner.run_test_suite(integration_tests)

    print(f"测试套件: {integration_report.suite_name}")
    print(f"总测试数: {integration_report.total_tests}")
    print(f"通过: {integration_report.passed}")
    print(f"失败: {integration_report.failed}")

    # 5. 并行测试
    print("\n=== 并行运行测试 ===")
    runner.results.clear()
    parallel_report = await runner.run_test_suite(unit_tests, parallel=True, max_workers=2)

    print(f"并行执行时间: {parallel_report.duration:.2f}s")
    print(f"串行执行时间: {unit_report.duration:.2f}s")
    print(f"性能提升: {(unit_report.duration / parallel_report.duration - 1) * 100:.1f}%")

    # 6. 生成报告
    print("\n=== 生成测试报告 ===")
    generator = TestReportGenerator()

    html_file = generator.generate_html_report(unit_report)
    json_file = generator.generate_json_report(unit_report)

    print(f"HTML报告: {html_file}")
    print(f"JSON报告: {json_file}")

    # 7. 显示详细结果
    print("\n=== 测试详细结果 ===")
    for result in unit_report.results:
        print(f"\n{result.test_id}:")
        print(f"  状态: {result.status.value}")
        print(f"  时间: {result.duration:.3f}s")
        if result.error_message:
            print(f"  错误: {result.error_message}")

    # 8. 清理资源
    print("\n=== 清理资源 ===")
    runner.data_manager.cleanup()
    print("测试数据已清理")

    # 9. 显示覆盖率（模拟）
    print("\n=== 代码覆盖率 ===")
    coverage_analyzer = CoverageAnalyzer()
    coverage_analyzer.set_total_lines("example.py", 100)
    for i in range(1, 85):  # 模拟85行被执行
        coverage_analyzer.add_executed_line("example.py", i)

    coverage = coverage_analyzer.get_coverage()
    print(f"总体覆盖率: {coverage['total']:.1f}%")


# ============================================================================
# 9. 高级功能：性能测试
# ============================================================================

class PerformanceTestRunner:
    """性能测试运行器

    进行性能基准测试。
    """

    def __init__(self):
        self.benchmarks: Dict[str, List[float]] = defaultdict(list)

    async def benchmark(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 10
    ):
        """基准测试"""
        # 预热
        for _ in range(warmup):
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()

        # 正式测试
        times = []
        for _ in range(iterations):
            start = time.time()
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()
            times.append(time.time() - start)

        self.benchmarks[name] = times

        # 统计
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        return {
            "name": name,
            "iterations": iterations,
            "average": avg_time,
            "min": min_time,
            "max": max_time,
            "ops_per_second": 1.0 / avg_time
        }

    def get_benchmark_report(self) -> Dict[str, Any]:
        """获取基准报告"""
        report = {}
        for name, times in self.benchmarks.items():
            report[name] = {
                "average": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "ops_per_second": len(times) / sum(times)
            }
        return report


# ============================================================================
# 10. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_advanced_testing())
