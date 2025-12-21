#!/usr/bin/env python3
"""
高级代码示例15: 自定义API端点
=================================

本示例展示如何构建功能完整的自定义API端点系统，
用于ScholarFlow中的HTTP API开发。

功能特性:
- FastAPI端点定义
- 请求验证
- 响应模型
- 错误处理
- 认证授权
- 限流控制
- API文档
- 异步处理

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
from pathlib import Path
import hashlib
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class HttpMethod(Enum):
    """HTTP方法"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class ResponseFormat(Enum):
    """响应格式"""
    JSON = "json"
    HTML = "html"
    FILE = "file"
    STREAM = "stream"


class AuthType(Enum):
    """认证类型"""
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    OAUTH2 = "oauth2"


@dataclass
class APIEndpoint:
    """API端点定义"""
    path: str
    method: HttpMethod
    handler: Callable
    description: str = ""
    auth_type: AuthType = AuthType.NONE
    rate_limit: Optional[int] = None  # 每分钟请求数
    timeout: float = 30.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestModel:
    """请求模型"""
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    validation_rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    example: Optional[Dict[str, Any]] = None


@dataclass
class ResponseModel:
    """响应模型"""
    status_code: int
    format: ResponseFormat = ResponseFormat.JSON
    schema: Optional[Dict[str, Any]] = None
    example: Optional[Dict[str, Any]] = None


@dataclass
class APIRequest:
    """API请求"""
    request_id: str
    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, Any]
    body: Optional[Dict[str, Any]]
    client_ip: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class APIResponse:
    """API响应"""
    request_id: str
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    format: ResponseFormat = ResponseFormat.JSON
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 2. 请求验证器
# ============================================================================

class RequestValidator:
    """请求验证器

    验证HTTP请求的参数和内容。
    """

    def __init__(self):
        self.rules = {
            "email": lambda x: "@" in str(x),
            "url": lambda x: str(x).startswith(("http://", "https://")),
            "uuid": lambda x: len(str(x)) == 36,
            "positive": lambda x: float(x) > 0,
            "non_empty": lambda x: len(str(x).strip()) > 0,
        }

    def validate(
        self,
        request: APIRequest,
        model: RequestModel
    ) -> Dict[str, List[str]]:
        """验证请求"""
        errors = defaultdict(list)

        # 验证必需字段
        for field_name in model.required_fields:
            if field_name not in request.query_params and field_name not in request.body:
                errors[field_name].append(f"Required field missing: {field_name}")

        # 获取字段值
        field_value = self._get_field_value(request, field_name)

        # 应用验证规则
        if field_name in model.validation_rules:
            rules = model.validation_rules[field_name]
            for rule_name, rule_config in rules.items():
                if not self._apply_rule(field_value, rule_name, rule_config):
                    errors[field_name].append(f"Validation failed: {rule_name}")

        return dict(errors)

    def _get_field_value(self, request: APIRequest, field_name: str) -> Any:
        """获取字段值"""
        # 优先从查询参数获取
        if field_name in request.query_params:
            return request.query_params[field_name]

        # 从请求体获取
        if request.body and field_name in request.body:
            return request.body[field_name]

        return None

    def _apply_rule(self, value: Any, rule_name: str, rule_config: Any) -> bool:
        """应用验证规则"""
        if rule_name in self.rules:
            return self.rules[rule_name](value)

        # 内置规则
        if rule_name == "min_length" and isinstance(value, str):
            return len(value) >= rule_config

        if rule_name == "max_length" and isinstance(value, str):
            return len(value) <= rule_config

        if rule_name == "min_value" and isinstance(value, (int, float)):
            return float(value) >= rule_config

        if rule_name == "max_value" and isinstance(value, (int, float)):
            return float(value) <= rule_config

        if rule_name == "regex":
            import re
            return bool(re.match(rule_config, str(value)))

        return True


# ============================================================================
# 3. 认证管理器
# ============================================================================

class AuthenticationManager:
    """认证管理器

    处理API请求的认证和授权。
    """

    def __init__(self):
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.tokens: Dict[str, Dict[str, Any]] = {}
        self.users: Dict[str, Dict[str, Any]] = {}

    def register_api_key(
        self,
        key: str,
        user_id: str,
        permissions: List[str],
        expires_at: Optional[datetime] = None
    ):
        """注册API密钥"""
        self.api_keys[key] = {
            "user_id": user_id,
            "permissions": permissions,
            "created_at": datetime.now(),
            "expires_at": expires_at
        }
        logger.info(f"Registered API key for user: {user_id}")

    def authenticate(self, request: APIRequest) -> Optional[Dict[str, Any]]:
        """认证请求"""
        # 检查API密钥
        api_key = request.headers.get("X-API-Key")
        if api_key and api_key in self.api_keys:
            key_info = self.api_keys[api_key]

            # 检查过期时间
            if key_info["expires_at"] and datetime.now() > key_info["expires_at"]:
                logger.warning(f"API key expired: {api_key}")
                return None

            return {
                "auth_type": "api_key",
                "user_id": key_info["user_id"],
                "permissions": key_info["permissions"]
            }

        # 检查Bearer令牌
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if token in self.tokens:
                return {
                    "auth_type": "bearer",
                    "user_id": self.tokens[token]["user_id"],
                    "permissions": self.tokens[token]["permissions"]
                }

        # 公开端点
        return None

    def authorize(
        self,
        auth_info: Optional[Dict[str, Any]],
        required_permissions: List[str]
    ) -> bool:
        """授权检查"""
        if not auth_info:
            return not required_permissions  # 无需权限

        user_permissions = auth_info.get("permissions", [])
        return all(perm in user_permissions for perm in required_permissions)


# ============================================================================
# 4. 限流器
# ============================================================================

class RateLimiter:
    """限流器

    控制API请求的频率。
    """

    def __init__(self):
        self.requests = {}  # {client_ip: [timestamps]}
        self.limits = {}    # {client_ip: limit}

    def is_rate_limited(
        self,
        client_ip: str,
        limit: int,
        window: int = 60
    ) -> bool:
        """检查是否超出限制"""
        now = time.time()
        window_start = now - window

        # 清理过期记录
        if client_ip in self.requests:
            self.requests[client_ip] = [
                ts for ts in self.requests[client_ip]
                if ts > window_start
            ]
        else:
            self.requests[client_ip] = []

        # 检查限制
        if len(self.requests[client_ip]) >= limit:
            return True

        # 记录请求
        self.requests[client_ip].append(now)
        return False


# ============================================================================
# 5. 高级API处理器
# ============================================================================

class AdvancedAPIHandler:
    """高级API处理器

    功能特性:
    - 请求验证
    - 认证授权
    - 限流控制
    - 错误处理
    - 响应格式化
    - 日志记录
    """

    def __init__(self):
        self.validator = RequestValidator()
        self.auth_manager = AuthenticationManager()
        self.rate_limiter = RateLimiter()
        self.endpoints: Dict[str, APIEndpoint] = {}

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_latency": 0.0,
            "rate_limited_requests": 0,
        }

    def register_endpoint(self, endpoint: APIEndpoint):
        """注册端点"""
        key = f"{endpoint.method.value}:{endpoint.path}"
        self.endpoints[key] = endpoint
        logger.info(f"Registered endpoint: {key}")

    async def handle_request(
        self,
        request: APIRequest
    ) -> APIResponse:
        """处理API请求"""
        start_time = time.time()
        self.stats["total_requests"] += 1

        try:
            # 获取端点
            endpoint_key = f"{request.method}:{request.path}"
            endpoint = self.endpoints.get(endpoint_key)

            if not endpoint:
                return self._create_error_response(
                    request.request_id,
                    404,
                    "Endpoint not found"
                )

            # 限流检查
            if endpoint.rate_limit:
                if self.rate_limiter.is_rate_limited(
                    request.client_ip,
                    endpoint.rate_limit
                ):
                    self.stats["rate_limited_requests"] += 1
                    return self._create_error_response(
                        request.request_id,
                        429,
                        "Rate limit exceeded"
                    )

            # 认证
            auth_info = self.auth_manager.authenticate(request)
            if endpoint.auth_type != AuthType.NONE and not auth_info:
                return self._create_error_response(
                    request.request_id,
                    401,
                    "Authentication required"
                )

            # 验证请求
            # 这里简化实现，实际应该使用RequestModel

            # 执行处理器
            result = await self._execute_handler(endpoint, request, auth_info)

            # 格式化响应
            response = APIResponse(
                request_id=request.request_id,
                status_code=200,
                body=result,
                execution_time=time.time() - start_time
            )

            self.stats["successful_requests"] += 1
            return response

        except Exception as e:
            self.stats["failed_requests"] += 1
            logger.error(f"Request handling failed: {e}")
            return self._create_error_response(
                request.request_id,
                500,
                str(e),
                execution_time=time.time() - start_time
            )

    async def _execute_handler(
        self,
        endpoint: APIEndpoint,
        request: APIRequest,
        auth_info: Optional[Dict[str, Any]]
    ) -> Any:
        """执行处理器"""
        # 调用处理器函数
        if asyncio.iscoroutinefunction(endpoint.handler):
            return await endpoint.handler(request, auth_info)
        else:
            return endpoint.handler(request, auth_info)

    def _create_error_response(
        self,
        request_id: str,
        status_code: int,
        message: str,
        execution_time: float = 0.0
    ) -> APIResponse:
        """创建错误响应"""
        return APIResponse(
            request_id=request_id,
            status_code=status_code,
            body={"error": message},
            execution_time=execution_time
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        success_rate = (
            self.stats["successful_requests"] / max(self.stats["total_requests"], 1) * 100
        )

        return {
            **self.stats,
            "success_rate": success_rate,
            "registered_endpoints": len(self.endpoints),
        }


# ============================================================================
# 6. 预定义端点处理器
# ============================================================================

class TaskEndpoints:
    """任务相关端点"""

    def __init__(self, handler: AdvancedAPIHandler):
        self.handler = handler
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def register(self):
        """注册端点"""
        # 创建任务
        self.handler.register_endpoint(
            APIEndpoint(
                path="/api/tasks",
                method=HttpMethod.POST,
                handler=self.create_task,
                description="Create a new task",
                auth_type=AuthType.API_KEY,
                rate_limit=100
            )
        )

        # 获取任务
        self.handler.register_endpoint(
            APIEndpoint(
                path="/api/tasks/{task_id}",
                method=HttpMethod.GET,
                handler=self.get_task,
                description="Get task by ID",
                auth_type=AuthType.API_KEY,
                rate_limit=200
            )
        )

        # 列出任务
        self.handler.register_endpoint(
            APIEndpoint(
                path="/api/tasks",
                method=HttpMethod.GET,
                handler=self.list_tasks,
                description="List all tasks",
                auth_type=AuthType.API_KEY,
                rate_limit=100
            )
        )

        # 删除任务
        self.handler.register_endpoint(
            APIEndpoint(
                path="/api/tasks/{task_id}",
                method=HttpMethod.DELETE,
                handler=self.delete_task,
                description="Delete task",
                auth_type=AuthType.API_KEY,
                rate_limit=50
            )
        )

    async def create_task(
        self,
        request: APIRequest,
        auth_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建任务"""
        # 模拟任务创建
        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "user_id": auth_info["user_id"] if auth_info else "anonymous"
        }

        self.tasks[task_id] = task

        logger.info(f"Created task: {task_id}")
        return {
            "task": task,
            "message": "Task created successfully"
        }

    async def get_task(
        self,
        request: APIRequest,
        auth_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取任务"""
        # 从路径参数获取task_id（简化实现）
        task_id = request.path.split("/")[-1]

        if task_id not in self.tasks:
            raise ValueError(f"Task not found: {task_id}")

        return {"task": self.tasks[task_id]}

    async def list_tasks(
        self,
        request: APIRequest,
        auth_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """列出任务"""
        # 模拟分页
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))

        tasks = list(self.tasks.values())
        start = (page - 1) * limit
        end = start + limit

        return {
            "tasks": tasks[start:end],
            "total": len(tasks),
            "page": page,
            "limit": limit
        }

    async def delete_task(
        self,
        request: APIRequest,
        auth_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """删除任务"""
        task_id = request.path.split("/")[-1]

        if task_id not in self.tasks:
            raise ValueError(f"Task not found: {task_id}")

        del self.tasks[task_id]

        logger.info(f"Deleted task: {task_id}")
        return {"message": "Task deleted successfully"}


class WorkflowEndpoints:
    """工作流相关端点"""

    def __init__(self, handler: AdvancedAPIHandler):
        self.handler = handler
        self.workflows: Dict[str, Dict[str, Any]] = {}

    def register(self):
        """注册端点"""
        # 启动工作流
        self.handler.register_endpoint(
            APIEndpoint(
                path="/api/workflows/start",
                method=HttpMethod.POST,
                handler=self.start_workflow,
                description="Start a workflow",
                auth_type=AuthType.API_KEY,
                rate_limit=50
            )
        )

        # 获取工作流状态
        self.handler.register_endpoint(
            APIEndpoint(
                path="/api/workflows/{workflow_id}/status",
                method=HttpMethod.GET,
                handler=self.get_workflow_status,
                description="Get workflow status",
                auth_type=AuthType.API_KEY,
                rate_limit=200
            )
        )

    async def start_workflow(
        self,
        request: APIRequest,
        auth_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """启动工作流"""
        workflow_id = str(uuid.uuid4())
        workflow = {
            "workflow_id": workflow_id,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "progress": 0
        }

        self.workflows[workflow_id] = workflow

        # 模拟异步执行
        asyncio.create_task(self._execute_workflow(workflow_id))

        return {
            "workflow": workflow,
            "message": "Workflow started"
        }

    async def _execute_workflow(self, workflow_id: str):
        """模拟工作流执行"""
        await asyncio.sleep(2)  # 模拟处理时间

        if workflow_id in self.workflows:
            self.workflows[workflow_id]["status"] = "completed"
            self.workflows[workflow_id]["progress"] = 100
            self.workflows[workflow_id]["completed_at"] = datetime.now().isoformat()

    async def get_workflow_status(
        self,
        request: APIRequest,
        auth_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取工作流状态"""
        workflow_id = request.path.split("/")[-2]

        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")

        return {"workflow": self.workflows[workflow_id]}


# ============================================================================
# 7. 使用示例
# ============================================================================

async def example_custom_api():
    """自定义API端点示例"""

    # 1. 创建API处理器
    print("\n=== 创建API处理器 ===")
    api_handler = AdvancedAPIHandler()

    # 2. 注册API密钥
    print("\n=== 注册API密钥 ===")
    api_handler.auth_manager.register_api_key(
        key="test_api_key_123",
        user_id="user_001",
        permissions=["create_task", "list_task", "delete_task"],
        expires_at=datetime.now() + timedelta(days=7)
    )

    # 3. 注册端点
    print("\n=== 注册端点 ===")
    task_endpoints = TaskEndpoints(api_handler)
    task_endpoints.register()

    workflow_endpoints = WorkflowEndpoints(api_handler)
    workflow_endpoints.register()

    print(f"注册了 {len(api_handler.endpoints)} 个端点")

    # 4. 模拟API请求
    print("\n=== 模拟API请求 ===")

    # 4.1 创建任务（需要认证）
    print("\n--- 创建任务 ---")
    create_request = APIRequest(
        request_id=str(uuid.uuid4()),
        method="POST",
        path="/api/tasks",
        headers={"X-API-Key": "test_api_key_123"},
        query_params={},
        body={
            "task_name": "Test Task",
            "description": "This is a test task",
            "priority": "high"
        },
        client_ip="127.0.0.1"
    )

    response = await api_handler.handle_request(create_request)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.body, indent=2)}")
    print(f"执行时间: {response.execution_time:.3f}s")

    # 4.2 列出任务
    print("\n--- 列出任务 ---")
    list_request = APIRequest(
        request_id=str(uuid.uuid4()),
        method="GET",
        path="/api/tasks",
        headers={"X-API-Key": "test_api_key_123"},
        query_params={"page": 1, "limit": 10},
        body=None,
        client_ip="127.0.0.1"
    )

    response = await api_handler.handle_request(list_request)
    print(f"状态码: {response.status_code}")
    print(f"任务数: {response.body.get('total', 0)}")

    # 4.3 启动工作流
    print("\n--- 启动工作流 ---")
    workflow_request = APIRequest(
        request_id=str(uuid.uuid4()),
        method="POST",
        path="/api/workflows/start",
        headers={"X-API-Key": "test_api_key_123"},
        query_params={},
        body={
            "workflow_type": "pdf_processing",
            "input_file": "/path/to/file.pdf"
        },
        client_ip="127.0.0.1"
    )

    response = await api_handler.handle_request(workflow_request)
    print(f"状态码: {response.status_code}")
    print(f"工作流ID: {response.body.get('workflow', {}).get('workflow_id')}")

    # 4.4 未认证请求
    print("\n--- 未认证请求 ---")
    unauthorized_request = APIRequest(
        request_id=str(uuid.uuid4()),
        method="GET",
        path="/api/tasks",
        headers={},
        query_params={},
        body=None,
        client_ip="127.0.0.1"
    )

    response = await api_handler.handle_request(unauthorized_request)
    print(f"状态码: {response.status_code}")
    print(f"错误: {response.body}")

    # 4.5 限流测试
    print("\n--- 限流测试 ---")
    for i in range(5):
        rate_request = APIRequest(
            request_id=str(uuid.uuid4()),
            method="GET",
            path="/api/tasks",
            headers={"X-API-Key": "test_api_key_123"},
            query_params={},
            body=None,
            client_ip="127.0.0.1"
        )

        response = await api_handler.handle_request(rate_request)
        print(f"请求 {i+1}: 状态码 {response.status_code}")

    # 5. 显示统计信息
    print("\n=== API统计 ===")
    stats = api_handler.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")

    # 6. 显示已注册端点
    print("\n=== 已注册端点 ===")
    for key, endpoint in api_handler.endpoints.items():
        print(f"{key}: {endpoint.description}")
        print(f"  认证: {endpoint.auth_type.value}")
        print(f"  限流: {endpoint.rate_limit}/min")


# ============================================================================
# 8. 高级功能：API文档生成
# ============================================================================

class APIDocGenerator:
    """API文档生成器

    自动生成API文档。
    """

    def __init__(self, handler: AdvancedAPIHandler):
        self.handler = handler

    def generate_docs(self) -> Dict[str, Any]:
        """生成API文档"""
        docs = {
            "title": "ScholarFlow API",
            "version": "1.0.0",
            "description": "API for ScholarFlow system",
            "endpoints": [],
            "authentication": {
                "type": "API Key",
                "header": "X-API-Key"
            }
        }

        for key, endpoint in self.handler.endpoints.items():
            endpoint_doc = {
                "method": endpoint.method.value,
                "path": endpoint.path,
                "description": endpoint.description,
                "tags": endpoint.tags,
                "auth_required": endpoint.auth_type != AuthType.NONE,
                "rate_limit": endpoint.rate_limit
            }

            docs["endpoints"].append(endpoint_doc)

        return docs

    def save_docs(self, output_file: str):
        """保存文档到文件"""
        docs = self.generate_docs()
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(docs, f, indent=2, ensure_ascii=False)
        logger.info(f"API documentation saved to {output_file}")


# ============================================================================
# 9. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_custom_api())
