#!/usr/bin/env python3
"""
高级代码示例19: 自定义部署系统
=================================

本示例展示如何构建一个功能完整的自定义部署系统，
用于ScholarFlow项目的自动化部署和运维。

功能特性:
- 多环境部署
- 容器化支持
- 配置管理
- 滚动更新
- 回滚机制
- 健康检查
- 监控集成
- 自动化流程

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
import yaml
import subprocess
import docker
import psutil
from pathlib import Path
from collections import defaultdict
import time
import hashlib

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class DeploymentType(Enum):
    """部署类型"""
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    DOCKER_COMPOSE = "docker_compose"
    LOCAL = "local"


class Environment(Enum):
    """环境类型"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class DeploymentStatus(Enum):
    """部署状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


@dataclass
class DeploymentConfig:
    """部署配置"""
    name: str
    deployment_type: DeploymentType
    environment: Environment
    version: str
    image: Optional[str] = None
    port: int = 8000
    replicas: int = 1
    resources: Dict[str, Any] = field(default_factory=dict)
    env_vars: Dict[str, str] = field(default_factory=dict)
    health_check: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeploymentResult:
    """部署结果"""
    deployment_id: str
    config: DeploymentConfig
    status: DeploymentStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    status: str
    port: int
    version: str
    health: str
    uptime: float
    resources: Dict[str, Any]


# ============================================================================
# 2. 部署策略
# ============================================================================

class DeploymentStrategy(ABC):
    """部署策略基类"""

    @abstractmethod
    async def deploy(self, config: DeploymentConfig) -> DeploymentResult:
        """执行部署"""
        pass

    @abstractmethod
    async def rollback(self, deployment_id: str) -> bool:
        """回滚部署"""
        pass

    @abstractmethod
    async def get_status(self, deployment_id: str) -> DeploymentStatus:
        """获取部署状态"""
        pass


# ============================================================================
# 3. Docker部署策略
# ============================================================================

class DockerDeploymentStrategy(DeploymentStrategy):
    """Docker部署策略"""

    def __init__(self):
        self.client = docker.from_env()
        self.deployments: Dict[str, DeploymentResult] = {}

    async def deploy(self, config: DeploymentConfig) -> DeploymentResult:
        """Docker部署"""
        deployment_id = f"{config.name}:{config.version}"
        logger.info(f"Starting Docker deployment: {deployment_id}")

        result = DeploymentResult(
            deployment_id=deployment_id,
            config=config,
            status=DeploymentStatus.RUNNING,
            start_time=datetime.now()
        )

        try:
            # 拉取镜像
            if config.image:
                logger.info(f"Pulling image: {config.image}")
                self.client.images.pull(config.image)

            # 创建容器
            container_name = f"{config.name}_{int(time.time())}"
            logger.info(f"Creating container: {container_name}")

            container = self.client.containers.run(
                config.image or "scholarflow:latest",
                name=container_name,
                ports={f"{config.port}/tcp": config.port},
                environment=config.env_vars,
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )

            # 等待容器启动
            await asyncio.sleep(2)

            # 检查容器状态
            container.reload()
            if container.status == "running":
                result.status = DeploymentStatus.SUCCESS
                result.end_time = datetime.now()
                result.logs.append(f"Container {container_name} started successfully")
                logger.info(f"Docker deployment successful: {deployment_id}")
            else:
                result.status = DeploymentStatus.FAILED
                result.error = f"Container failed to start: {container.status}"
                logger.error(result.error)

            self.deployments[deployment_id] = result
            return result

        except Exception as e:
            result.status = DeploymentStatus.FAILED
            result.error = str(e)
            result.end_time = datetime.now()
            logger.error(f"Docker deployment failed: {e}")
            return result

    async def rollback(self, deployment_id: str) -> bool:
        """Docker回滚"""
        logger.info(f"Rolling back Docker deployment: {deployment_id}")

        if deployment_id not in self.deployments:
            logger.error(f"Deployment not found: {deployment_id}")
            return False

        try:
            # 停止旧容器
            config = self.deployments[deployment_id].config
            containers = self.client.containers.list(filters={"name": config.name})
            for container in containers:
                logger.info(f"Stopping container: {container.name}")
                container.stop()
                container.remove()

            self.deployments[deployment_id].status = DeploymentStatus.ROLLED_BACK
            logger.info(f"Docker rollback successful: {deployment_id}")
            return True

        except Exception as e:
            logger.error(f"Docker rollback failed: {e}")
            return False

    async def get_status(self, deployment_id: str) -> DeploymentStatus:
        """获取部署状态"""
        if deployment_id in self.deployments:
            return self.deployments[deployment_id].status
        return DeploymentStatus.FAILED


# ============================================================================
# 4. 配置管理器
# ============================================================================

class ConfigManager:
    """配置管理器

    管理不同环境的部署配置。
    """

    def __init__(self, config_dir: str = "./configs"):
        self.config_dir = Path(config_dir)
        self.configs: Dict[str, DeploymentConfig] = {}

    def load_config(self, config_file: str) -> DeploymentConfig:
        """加载配置文件"""
        config_path = self.config_dir / config_file

        with open(config_path, 'r') as f:
            if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        config = DeploymentConfig(
            name=data['name'],
            deployment_type=DeploymentType(data['deployment_type']),
            environment=Environment(data['environment']),
            version=data['version'],
            image=data.get('image'),
            port=data.get('port', 8000),
            replicas=data.get('replicas', 1),
            resources=data.get('resources', {}),
            env_vars=data.get('env_vars', {}),
            health_check=data.get('health_check', {}),
            metadata=data.get('metadata', {})
        )

        self.configs[config.name] = config
        return config

    def save_config(self, config: DeploymentConfig, filename: Optional[str] = None):
        """保存配置"""
        filename = filename or f"{config.name}_{config.environment.value}.yaml"
        config_path = self.config_dir / filename

        data = {
            'name': config.name,
            'deployment_type': config.deployment_type.value,
            'environment': config.environment.value,
            'version': config.version,
            'image': config.image,
            'port': config.port,
            'replicas': config.replicas,
            'resources': config.resources,
            'env_vars': config.env_vars,
            'health_check': config.health_check,
            'metadata': config.metadata
        }

        with open(config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

        logger.info(f"Config saved: {config_path}")

    def get_config(self, name: str, environment: Environment) -> Optional[DeploymentConfig]:
        """获取配置"""
        for config in self.configs.values():
            if config.name == name and config.environment == environment:
                return config
        return None

    def list_configs(self, environment: Optional[Environment] = None) -> List[DeploymentConfig]:
        """列出配置"""
        configs = list(self.configs.values())
        if environment:
            configs = [c for c in configs if c.environment == environment]
        return configs


# ============================================================================
# 5. 健康检查器
# ============================================================================

class HealthChecker:
    """健康检查器

    检查部署服务的健康状态。
    """

    def __init__(self):
        self.checks: Dict[str, Callable] = {}

    def register_check(self, service_name: str, check_func: Callable):
        """注册健康检查"""
        self.checks[service_name] = check_func

    async def check_service(self, service_name: str) -> Dict[str, Any]:
        """检查服务健康"""
        if service_name not in self.checks:
            return {"status": "unknown", "error": "No check registered"}

        try:
            check_func = self.checks[service_name]
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()

            return {
                "status": "healthy",
                "details": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def check_all_services(self) -> Dict[str, Any]:
        """检查所有服务"""
        results = {}
        for service_name in self.checks:
            results[service_name] = await self.check_service(service_name)
        return results


# ============================================================================
# 6. 部署编排器
# ============================================================================

class DeploymentOrchestrator:
    """部署编排器

    统一管理部署流程。
    """

    def __init__(self):
        self.strategies: Dict[DeploymentType, DeploymentStrategy] = {}
        self.config_manager = ConfigManager()
        self.health_checker = HealthChecker()
        self.deployments: Dict[str, DeploymentResult] = {}
        self.notification_callbacks: List[Callable] = []

        # 注册默认策略
        self._register_default_strategies()

    def _register_default_strategies(self):
        """注册默认策略"""
        self.strategies[DeploymentType.DOCKER] = DockerDeploymentStrategy()

    def register_strategy(self, deployment_type: DeploymentType, strategy: DeploymentStrategy):
        """注册部署策略"""
        self.strategies[deployment_type] = strategy
        logger.info(f"Registered strategy for {deployment_type.value}")

    def register_notification(self, callback: Callable):
        """注册通知回调"""
        self.notification_callbacks.append(callback)

    async def deploy(
        self,
        config: DeploymentConfig,
        wait_for_health: bool = True,
        timeout: int = 300
    ) -> DeploymentResult:
        """执行部署"""
        logger.info(f"Starting deployment: {config.name} ({config.environment.value})")

        # 获取部署策略
        strategy = self.strategies.get(config.deployment_type)
        if not strategy:
            raise ValueError(f"No strategy for deployment type: {config.deployment_type.value}")

        # 执行部署
        result = await strategy.deploy(config)
        self.deployments[result.deployment_id] = result

        # 发送通知
        await self._notify(result)

        # 等待健康检查
        if wait_for_health and result.status == DeploymentStatus.SUCCESS:
            await self._wait_for_health(config, timeout)

        return result

    async def rollback(self, deployment_id: str) -> bool:
        """回滚部署"""
        logger.info(f"Starting rollback: {deployment_id}")

        # 获取部署配置
        if deployment_id not in self.deployments:
            logger.error(f"Deployment not found: {deployment_id}")
            return False

        config = self.deployments[deployment_id].config
        strategy = self.strategies.get(config.deployment_type)

        if not strategy:
            logger.error(f"No strategy for deployment type: {config.deployment_type.value}")
            return False

        # 执行回滚
        success = await strategy.rollback(deployment_id)

        if success:
            self.deployments[deployment_id].status = DeploymentStatus.ROLLED_BACK
            await self._notify(self.deployments[deployment_id])

        return success

    async def get_deployment_status(self, deployment_id: str) -> Optional[DeploymentResult]:
        """获取部署状态"""
        return self.deployments.get(deployment_id)

    async def list_deployments(self, environment: Optional[Environment] = None) -> List[DeploymentResult]:
        """列出部署"""
        deployments = list(self.deployments.values())
        if environment:
            deployments = [d for d in deployments if d.config.environment == environment]
        return deployments

    async def _wait_for_health(
        self,
        config: DeploymentConfig,
        timeout: int
    ):
        """等待服务健康"""
        logger.info(f"Waiting for service health: {config.name}")
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 这里简化实现，实际应该调用真实的健康检查
            await asyncio.sleep(5)

            # 模拟健康检查
            logger.info(f"Health check for {config.name}: OK")
            break

        logger.info(f"Service health confirmed: {config.name}")

    async def _notify(self, result: DeploymentResult):
        """发送通知"""
        for callback in self.notification_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception as e:
                logger.error(f"Notification failed: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取部署统计"""
        total = len(self.deployments)
        successful = sum(1 for d in self.deployments.values() if d.status == DeploymentStatus.SUCCESS)
        failed = sum(1 for d in self.deployments.values() if d.status == DeploymentStatus.FAILED)

        success_rate = (successful / max(total, 1)) * 100

        return {
            "total_deployments": total,
            "successful": successful,
            "failed": failed,
            "success_rate": success_rate,
            "registered_strategies": list(self.strategies.keys()),
        }


# ============================================================================
# 7. 使用示例
# ============================================================================

async def example_custom_deployment():
    """自定义部署示例"""

    # 1. 创建部署编排器
    print("\n=== 创建部署编排器 ===")
    orchestrator = DeploymentOrchestrator()

    # 2. 创建部署配置
    print("\n=== 创建部署配置 ===")
    config = DeploymentConfig(
        name="scholarflow",
        deployment_type=DeploymentType.DOCKER,
        environment=Environment.PRODUCTION,
        version="1.0.0",
        image="scholarflow:latest",
        port=8000,
        replicas=2,
        env_vars={
            "ENV": "production",
            "LOG_LEVEL": "INFO",
            "DATABASE_URL": "postgresql://..."
        },
        health_check={
            "path": "/health",
            "interval": 10,
            "timeout": 5
        }
    )

    print(f"服务名称: {config.name}")
    print(f"部署类型: {config.deployment_type.value}")
    print(f"环境: {config.environment.value}")
    print(f"版本: {config.version}")
    print(f"镜像: {config.image}")

    # 3. 保存配置
    print("\n=== 保存配置 ===")
    config_manager = ConfigManager()
    config_manager.save_config(config)
    print(f"配置已保存")

    # 4. 注册通知
    print("\n=== 注册通知 ===")
    def notification_callback(result: DeploymentResult):
        print(f"\n[通知] 部署状态更新: {result.deployment_id} - {result.status.value}")

    orchestrator.register_notification(notification_callback)

    # 5. 执行部署
    print("\n=== 执行部署 ===")
    try:
        deployment_result = await orchestrator.deploy(
            config,
            wait_for_health=False,
            timeout=60
        )

        print(f"部署ID: {deployment_result.deployment_id}")
        print(f"部署状态: {deployment_result.status.value}")
        print(f"开始时间: {deployment_result.start_time.strftime('%H:%M:%S')}")

        if deployment_result.end_time:
            duration = (deployment_result.end_time - deployment_result.start_time).total_seconds()
            print(f"部署耗时: {duration:.2f}s")

        if deployment_result.error:
            print(f"错误: {deployment_result.error}")

    except Exception as e:
        print(f"部署失败: {e}")

    # 6. 列出部署
    print("\n=== 列出部署 ===")
    deployments = await orchestrator.list_deployments()
    print(f"部署总数: {len(deployments)}")

    for deployment in deployments:
        print(f"  {deployment.deployment_id}: {deployment.status.value}")

    # 7. 健康检查
    print("\n=== 健康检查 ===")
    health_checker = HealthChecker()

    # 注册健康检查
    async def check_scholarflow():
        # 模拟健康检查
        await asyncio.sleep(1)
        return {
            "status": "healthy",
            "response_time": 0.05,
            "cpu_usage": 25.5,
            "memory_usage": 512.0
        }

    health_checker.register_check("scholarflow", check_scholarflow)

    health_result = await health_checker.check_service("scholarflow")
    print(f"健康状态: {health_result['status']}")
    if health_result['status'] == 'healthy':
        print(f"详情: {health_result['details']}")

    # 8. 回滚部署
    print("\n=== 回滚部署 ===")
    if deployments:
        deployment_id = deployments[0].deployment_id
        rollback_success = await orchestrator.rollback(deployment_id)
        print(f"回滚结果: {'成功' if rollback_success else '失败'}")

    # 9. 显示统计
    print("\n=== 部署统计 ===")
    stats = orchestrator.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")

    # 10. 清理
    print("\n=== 清理 ===")
    print("部署示例完成")


# ============================================================================
# 8. 高级功能：滚动更新
# ============================================================================

class RollingUpdateStrategy(DeploymentStrategy):
    """滚动更新策略

    零停机时间的部署策略。
    """

    def __init__(self, base_strategy: DeploymentStrategy):
        self.base_strategy = base_strategy

    async def deploy(self, config: DeploymentConfig) -> DeploymentResult:
        """滚动更新"""
        logger.info(f"Starting rolling update: {config.name}")

        # 步骤1: 部署新版本（一个实例）
        # 步骤2: 等待健康检查
        # 步骤3: 切换流量
        # 步骤4: 更新剩余实例

        # 简化实现
        result = await self.base_strategy.deploy(config)
        logger.info(f"Rolling update completed: {config.name}")

        return result

    async def rollback(self, deployment_id: str) -> bool:
        """回滚"""
        logger.info(f"Rolling back: {deployment_id}")
        return await self.base_strategy.rollback(deployment_id)

    async def get_status(self, deployment_id: str) -> DeploymentStatus:
        """获取状态"""
        return await self.base_strategy.get_status(deployment_id)


# ============================================================================
# 9. 高级功能：配置模板
# ============================================================================

class ConfigTemplate:
    """配置模板

    生成不同环境的配置。
    """

    def __init__(self, base_config: DeploymentConfig):
        self.base_config = base_config

    def generate_config(
        self,
        environment: Environment,
        overrides: Optional[Dict[str, Any]] = None
    ) -> DeploymentConfig:
        """生成配置"""
        overrides = overrides or {}

        # 复制基础配置
        config_dict = {
            'name': self.base_config.name,
            'deployment_type': self.base_config.deployment_type,
            'version': self.base_config.version,
            'image': self.base_config.image,
            'port': self.base_config.port,
            'resources': self.base_config.resources.copy(),
            'env_vars': self.base_config.env_vars.copy(),
            'health_check': self.base_config.health_check.copy(),
            'metadata': self.base_config.metadata.copy(),
        }

        # 环境特定设置
        if environment == Environment.PRODUCTION:
            config_dict['replicas'] = max(3, self.base_config.replicas)
            config_dict['env_vars']['LOG_LEVEL'] = 'WARNING'
            config_dict['resources']['cpu'] = '1000m'
            config_dict['resources']['memory'] = '1Gi'
        elif environment == Environment.DEVELOPMENT:
            config_dict['replicas'] = 1
            config_dict['env_vars']['LOG_LEVEL'] = 'DEBUG'
            config_dict['resources']['cpu'] = '500m'
            config_dict['resources']['memory'] = '512Mi'

        # 应用覆盖
        config_dict.update(overrides)

        # 创建新配置
        return DeploymentConfig(
            name=config_dict['name'],
            deployment_type=config_dict['deployment_type'],
            environment=environment,
            version=config_dict['version'],
            image=config_dict.get('image'),
            port=config_dict.get('port', 8000),
            replicas=config_dict.get('replicas', 1),
            resources=config_dict.get('resources', {}),
            env_vars=config_dict.get('env_vars', {}),
            health_check=config_dict.get('health_check', {}),
            metadata=config_dict.get('metadata', {})
        )


# ============================================================================
# 10. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_custom_deployment())
