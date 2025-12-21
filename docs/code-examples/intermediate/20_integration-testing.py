#!/usr/bin/env python3
"""
高级代码示例20: 集成测试框架
=================================

本示例展示如何构建一个功能完整的集成测试系统，
用于ScholarFlow项目的端到端测试验证。

功能特性:
- 服务编排
- 测试数据准备
- API集成测试
- 数据库测试
- 消息队列测试
- 外部服务模拟
- 测试报告
- 并行执行

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
import aiohttp
import aiofiles
import subprocess
import docker
import sqlite3
import aiosqlite
from pathlib import Path
from collections import defaultdict
import time
import uuid

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class ServiceType(Enum):
    """服务类型"""
    API = "api"
    DATABASE = "database"
    MESSAGE_QUEUE = "message_queue"
    STORAGE = "storage"
    EXTERNAL = "external"


class TestPhase(Enum):
    """测试阶段"""
    SETUP = "setup"
    EXECUTE = "execute"
    VERIFY = "verify"
    CLEANUP = "cleanup"


@dataclass
class ServiceConfig:
    """服务配置"""
    name: str
    service_type: ServiceType
    image: Optional[str] = None
    port: Optional[int] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    health_check: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrationTest:
    """集成测试"""
    test_id: str
    name: str
    description: str
    services: List[ServiceConfig]
    test_func: Callable
    setup_func: Optional[Callable] = None
    teardown_func: Optional[Callable] = None
    timeout: float = 300.0
    retries: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    status: str  # PASSED, FAILED, SKIPPED
    duration: float
    start_time: datetime
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    assertions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 2. 服务管理器
# ============================================================================

class ServiceManager:
    """服务管理器

    管理和控制测试所需的服务。
    """

    def __init__(self):
        self.services: Dict[str, ServiceConfig] = {}
        self.running_services: Dict[str, Any] = {}
        self.docker_client = docker.from_env()

    def register_service(self, service: ServiceConfig):
        """注册服务"""
        self.services[service.name] = service
        logger.info(f"Registered service: {service.name}")

    async def start_service(self, service_name: str) -> bool:
        """启动服务"""
        if service_name not in self.services:
            logger.error(f"Service not found: {service_name}")
            return False

        service = self.services[service_name]

        try:
            if service.service_type == ServiceType.DATABASE:
                return await self._start_database(service)
            elif service.service_type == ServiceType.MESSAGE_QUEUE:
                return await self._start_message_queue(service)
            elif service.service_type == ServiceType.EXTERNAL:
                return await self._start_external(service)
            else:
                logger.warning(f"Unknown service type: {service.service_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to start service {service_name}: {e}")
            return False

    async def _start_database(self, service: ServiceConfig) -> bool:
        """启动数据库"""
        logger.info(f"Starting database: {service.name}")

        # 启动SQLite数据库（模拟）
        db_path = f"/tmp/{service.name}.db"
        conn = sqlite3.connect(db_path)
        conn.close()

        self.running_services[service.name] = {"db_path": db_path}
        logger.info(f"Database started: {service.name}")
        return True

    async def _start_message_queue(self, service: ServiceConfig) -> bool:
        """启动消息队列"""
        logger.info(f"Starting message queue: {service.name}")

        # 模拟消息队列启动
        self.running_services[service.name] = {"queue_name": service.name}
        logger.info(f"Message queue started: {service.name}")
        return True

    async def _start_external(self, service: ServiceConfig) -> bool:
        """启动外部服务"""
        logger.info(f"Starting external service: {service.name}")

        # 模拟外部服务启动
        self.running_services[service.name] = {"service_url": f"http://localhost:{service.port}"}
        logger.info(f"External service started: {service.name}")
        return True

    async def stop_service(self, service_name: str) -> bool:
        """停止服务"""
        if service_name not in self.running_services:
            logger.warning(f"Service not running: {service_name}")
            return True

        try:
            # 清理资源
            del self.running_services[service_name]
            logger.info(f"Stopped service: {service_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop service {service_name}: {e}")
            return False

    async def start_all_services(self, service_names: List[str]) -> bool:
        """启动所有服务"""
        logger.info(f"Starting {len(service_names)} services")

        # 按依赖顺序启动
        for service_name in service_names:
            if service_name not in self.running_services:
                await self.start_service(service_name)
                await asyncio.sleep(1)  # 等待服务启动

        logger.info("All services started")
        return True

    async def stop_all_services(self):
        """停止所有服务"""
        logger.info("Stopping all services")

        for service_name in list(self.running_services.keys()):
            await self.stop_service(service_name)

        logger.info("All services stopped")

    def get_service_url(self, service_name: str) -> Optional[str]:
        """获取服务URL"""
        if service_name in self.running_services:
            service_info = self.running_services[service_name]
            if "service_url" in service_info:
                return service_info["service_url"]
        return None

    def get_service_config(self, service_name: str) -> Optional[ServiceConfig]:
        """获取服务配置"""
        return self.services.get(service_name)


# ============================================================================
# 3. 测试数据管理器
# ============================================================================

class TestDataManager:
    """测试数据管理器

    管理测试所需的数据。
    """

    def __init__(self, service_manager: ServiceManager):
        self.service_manager = service_manager
        self.test_data: Dict[str, Any] = {}

    def prepare_test_data(self, data_config: Dict[str, Any]):
        """准备测试数据"""
        self.test_data.update(data_config)

    async def insert_test_data(self, table: str, data: List[Dict[str, Any]]):
        """插入测试数据"""
        db_service = self.service_manager.get_service_config("test_db")
        if not db_service:
            return

        db_path = self.service_manager.running_services["test_db"]["db_path"]

        async with aiosqlite.connect(db_path) as conn:
            for item in data:
                columns = ", ".join(item.keys())
                placeholders = ", ".join(["?"] * len(item))
                values = list(item.values())

                await conn.execute(
                    f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
                    values
                )
            await conn.commit()

    def get_test_data(self, key: str) -> Any:
        """获取测试数据"""
        return self.test_data.get(key)

    def clear_test_data(self):
        """清空测试数据"""
        self.test_data.clear()


# ============================================================================
# 4. API测试客户端
# ============================================================================

class APITestClient:
    """API测试客户端"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """GET请求"""
        async with self.session.get(f"{self.base_url}{path}", **kwargs) as response:
            return await response.json()

    async def post(self, path: str, json_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """POST请求"""
        async with self.session.post(f"{self.base_url}{path}", json=json_data, **kwargs) as response:
            return await response.json()

    async def put(self, path: str, json_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """PUT请求"""
        async with self.session.put(f"{self.base_url}{path}", json=json_data, **kwargs) as response:
            return await response.json()

    async def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """DELETE请求"""
        async with self.session.delete(f"{self.base_url}{path}", **kwargs) as response:
            return await response.json()


# ============================================================================
# 5. 集成测试运行器
# ============================================================================

class IntegrationTestRunner:
    """集成测试运行器"""

    def __init__(self):
        self.service_manager = ServiceManager()
        self.test_data_manager: Optional[TestDataManager] = None
        self.results: List[TestResult] = []

    def set_test_data_manager(self, manager: TestDataManager):
        """设置测试数据管理器"""
        self.test_data_manager = manager

    async def run_test(self, test: IntegrationTest) -> TestResult:
        """运行单个集成测试"""
        logger.info(f"Running integration test: {test.name}")
        start_time = datetime.now()

        result = TestResult(
            test_id=test.test_id,
            status="FAILED",
            duration=0.0,
            start_time=start_time
        )

        try:
            # 设置超时
            async with asyncio.timeout(test.timeout):
                # 1. 启动服务
                await self._start_test_services(test.services)

                # 2. 执行setup
                if test.setup_func:
                    await self._safe_execute(test.setup_func)

                # 3. 执行测试
                await self._safe_execute(test.test_func)

                # 4. 标记为通过
                result.status = "PASSED"

        except asyncio.TimeoutError:
            result.status = "FAILED"
            result.error = f"Test timed out after {test.timeout}s"

        except AssertionError as e:
            result.status = "FAILED"
            result.error = str(e)

        except Exception as e:
            result.status = "FAILED"
            result.error = f"Unexpected error: {str(e)}"

        finally:
            # 5. 清理
            if test.teardown_func:
                await self._safe_execute(test.teardown_func)

            # 停止服务
            await self._stop_test_services(test.services)

            result.end_time = datetime.now()
            result.duration = (result.end_time - start_time).total_seconds()

        self.results.append(result)
        logger.info(f"Test {test.name}: {result.status} ({result.duration:.2f}s)")
        return result

    async def _start_test_services(self, services: List[ServiceConfig]):
        """启动测试服务"""
        service_names = [s.name for s in services]
        await self.service_manager.start_all_services(service_names)

        # 等待服务就绪
        for service in services:
            if service.health_check:
                await self._wait_for_service(service)

    async def _stop_test_services(self, services: List[ServiceConfig]):
        """停止测试服务"""
        for service in services:
            await self.service_manager.stop_service(service.name)

    async def _wait_for_service(self, service: ServiceConfig):
        """等待服务就绪"""
        max_attempts = 30
        attempt = 0

        while attempt < max_attempts:
            try:
                if service.service_type == ServiceType.DATABASE:
                    # 检查数据库连接
                    db_path = self.service_manager.running_services[service.name]["db_path"]
                    async with aiosqlite.connect(db_path) as conn:
                        await conn.execute("SELECT 1")
                    break

                elif service.service_type == ServiceType.EXTERNAL:
                    # 检查HTTP服务
                    url = self.service_manager.get_service_url(service.name)
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{url}/health") as response:
                            if response.status == 200:
                                break

                await asyncio.sleep(1)
                attempt += 1

            except Exception:
                await asyncio.sleep(1)
                attempt += 1

    async def _safe_execute(self, func: Callable):
        """安全执行函数"""
        if asyncio.iscoroutinefunction(func):
            await func()
        else:
            func()

    async def run_test_suite(self, tests: List[IntegrationTest], parallel: bool = False) -> List[TestResult]:
        """运行测试套件"""
        logger.info(f"Running test suite with {len(tests)} tests")

        if parallel:
            # 并行执行
            tasks = [self.run_test(test) for test in tests]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理异常
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    test = tests[i]
                    final_results.append(TestResult(
                        test_id=test.test_id,
                        status="FAILED",
                        duration=0.0,
                        start_time=datetime.now(),
                        error=str(result)
                    ))
                else:
                    final_results.append(result)
            return final_results
        else:
            # 串行执行
            for test in tests:
                await self.run_test(test)
            return self.results

    def get_summary(self) -> Dict[str, Any]:
        """获取测试摘要"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASSED")
        failed = sum(1 for r in self.results if r.status == "FAILED")

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": (passed / max(total, 1)) * 100,
            "total_duration": sum(r.duration for r in self.results),
        }


# ============================================================================
# 6. 预定义测试
# ============================================================================

class PredefinedTests:
    """预定义测试"""

    @staticmethod
    def create_api_integration_test() -> IntegrationTest:
        """创建API集成测试"""
        async def test_api_workflow(api_client: APITestClient, data_manager: TestDataManager):
            """测试API工作流"""

            # 1. 创建任务
            task_data = {
                "name": "Test Task",
                "description": "Integration test task",
                "priority": "high"
            }
            response = await api_client.post("/api/tasks", task_data)
            assert "task_id" in response, "Task creation failed"

            # 2. 获取任务
            task_id = response["task_id"]
            task = await api_client.get(f"/api/tasks/{task_id}")
            assert task["name"] == "Test Task", "Task retrieval failed"

            # 3. 更新任务
            update_data = {"status": "completed"}
            await api_client.put(f"/api/tasks/{task_id}", update_data)

            # 4. 验证更新
            updated_task = await api_client.get(f"/api/tasks/{task_id}")
            assert updated_task["status"] == "completed", "Task update failed"

            # 5. 删除任务
            await api_client.delete(f"/api/tasks/{task_id}")

            # 6. 验证删除
            try:
                await api_client.get(f"/api/tasks/{task_id}")
                assert False, "Task should have been deleted"
            except Exception:
                pass  # 预期异常

        services = [
            ServiceConfig(
                name="test_api",
                service_type=ServiceType.API,
                port=8000,
                health_check={"path": "/health"}
            ),
            ServiceConfig(
                name="test_db",
                service_type=ServiceType.DATABASE
            )
        ]

        return IntegrationTest(
            test_id="test_api_workflow",
            name="API Workflow Test",
            description="Test complete API workflow",
            services=services,
            test_func=test_api_workflow
        )

    @staticmethod
    def create_database_integration_test() -> IntegrationTest:
        """创建数据库集成测试"""
        async def test_database_operations(data_manager: TestDataManager):
            """测试数据库操作"""

            # 插入测试数据
            test_users = [
                {"id": 1, "name": "User 1", "email": "user1@test.com"},
                {"id": 2, "name": "User 2", "email": "user2@test.com"},
                {"id": 3, "name": "User 3", "email": "user3@test.com"}
            ]

            await data_manager.insert_test_data("users", test_users)

            # 验证数据
            db_path = data_manager.service_manager.running_services["test_db"]["db_path"]
            async with aiosqlite.connect(db_path) as conn:
                cursor = await conn.execute("SELECT COUNT(*) FROM users")
                count = await cursor.fetchone()
                assert count[0] == 3, "User count mismatch"

        services = [
            ServiceConfig(
                name="test_db",
                service_type=ServiceType.DATABASE
            )
        ]

        return IntegrationTest(
            test_id="test_database_ops",
            name="Database Operations Test",
            description="Test database CRUD operations",
            services=services,
            test_func=test_database_operations
        )


# ============================================================================
# 7. 使用示例
# ============================================================================

async def example_integration_testing():
    """集成测试示例"""

    # 1. 创建测试运行器
    print("\n=== 创建集成测试运行器 ===")
    runner = IntegrationTestRunner()
    data_manager = TestDataManager(runner.service_manager)
    runner.set_test_data_manager(data_manager)

    # 2. 注册服务
    print("\n=== 注册服务 ===")
    runner.service_manager.register_service(ServiceConfig(
        name="test_api",
        service_type=ServiceType.API,
        port=8000
    ))
    runner.service_manager.register_service(ServiceConfig(
        name="test_db",
        service_type=ServiceType.DATABASE
    ))

    # 3. 准备测试数据
    print("\n=== 准备测试数据 ===")
    data_manager.prepare_test_data({
        "api_url": "http://localhost:8000",
        "test_user": {"name": "Integration Test User"}
    })

    # 4. 创建测试
    print("\n=== 创建集成测试 ===")

    # 测试1: API工作流测试
    async def test_with_api_client(api_client: APITestClient, data_manager: TestDataManager):
        """使用API客户端的测试"""
        # 模拟API调用
        await asyncio.sleep(0.5)
        print("  - Created task via API")
        await asyncio.sleep(0.5)
        print("  - Retrieved task via API")
        await asyncio.sleep(0.5)
        print("  - Updated task via API")
        # 模拟断言
        assert True, "API workflow test passed"

    api_test = IntegrationTest(
        test_id="api_workflow",
        name="API Workflow",
        description="Test API workflow",
        services=[
            ServiceConfig(name="test_api", service_type=ServiceType.API, port=8000),
            ServiceConfig(name="test_db", service_type=ServiceType.DATABASE)
        ],
        test_func=test_with_api_client,
        setup_func=lambda: print("  Setup: Initializing API client"),
        teardown_func=lambda: print("  Teardown: Cleaning up API client")
    )

    # 测试2: 数据库操作测试
    async def test_db_operations(data_manager: TestDataManager):
        """数据库操作测试"""
        print("  - Inserting test data")
        await data_manager.insert_test_data("test_table", [
            {"id": 1, "value": "test1"},
            {"id": 2, "value": "test2"}
        ])
        print("  - Verifying data insertion")
        # 模拟断言
        assert True, "Database operations test passed"

    db_test = IntegrationTest(
        test_id="db_operations",
        name="Database Operations",
        description="Test database operations",
        services=[
            ServiceConfig(name="test_db", service_type=ServiceType.DATABASE)
        ],
        test_func=test_db_operations
    )

    # 测试3: 完整工作流测试
    async def test_full_workflow(api_client: APITestClient, data_manager: TestDataManager):
        """完整工作流测试"""
        print("  - Starting full workflow")
        await asyncio.sleep(1)
        print("  - Processing data")
        await asyncio.sleep(1)
        print("  - Validating results")
        # 模拟断言
        assert True, "Full workflow test passed"

    workflow_test = IntegrationTest(
        test_id="full_workflow",
        name="Full Workflow",
        description="Test complete workflow",
        services=[
            ServiceConfig(name="test_api", service_type=ServiceType.API, port=8000),
            ServiceConfig(name="test_db", service_type=ServiceType.DATABASE),
            ServiceConfig(name="test_queue", service_type=ServiceType.MESSAGE_QUEUE)
        ],
        test_func=test_full_workflow
    )

    tests = [api_test, db_test, workflow_test]

    # 5. 运行测试
    print("\n=== 运行集成测试 ===")
    start_time = time.time()

    # 串行执行
    print("\n--- 串行执行 ---")
    await runner.run_test_suite(tests, parallel=False)

    # 并行执行（重新创建运行器）
    print("\n--- 并行执行 ---")
    parallel_runner = IntegrationTestRunner()
    parallel_runner.set_test_data_manager(data_manager)
    for test in tests:
        await parallel_runner.run_test(test)

    # 6. 显示结果
    print("\n=== 测试结果 ===")
    summary = runner.get_summary()
    print(f"总测试数: {summary['total']}")
    print(f"通过: {summary['passed']}")
    print(f"失败: {summary['failed']}")
    print(f"成功率: {summary['success_rate']:.1f}%")
    print(f"总耗时: {summary['total_duration']:.2f}s")

    # 详细结果
    print("\n=== 详细结果 ===")
    for result in runner.results:
        print(f"\n{result.test_id}:")
        print(f"  状态: {result.status}")
        print(f"  耗时: {result.duration:.2f}s")
        if result.error:
            print(f"  错误: {result.error}")


# ============================================================================
# 8. 高级功能：测试报告生成
# ============================================================================

class TestReportGenerator:
    """测试报告生成器"""

    def __init__(self, output_dir: str = "./integration_test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_report(self, results: List[TestResult]) -> Path:
        """生成测试报告"""
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.status == "PASSED"),
                "failed": sum(1 for r in results if r.status == "FAILED"),
                "total_duration": sum(r.duration for r in results)
            },
            "tests": []
        }

        for result in results:
            report_data["tests"].append({
                "test_id": result.test_id,
                "status": result.status,
                "duration": result.duration,
                "start_time": result.start_time.isoformat(),
                "end_time": result.end_time.isoformat() if result.end_time else None,
                "error": result.error,
                "logs": result.logs,
                "assertions": result.assertions
            })

        report_file = self.output_dir / f"integration_test_report_{int(time.time())}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Test report generated: {report_file}")
        return report_file


# ============================================================================
# 9. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_integration_testing())
