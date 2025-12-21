#!/usr/bin/env python3
"""
高级代码示例6: 高级LLM配置与管理
===================================

本示例展示如何构建一个功能完整的LLM管理系统，
包括多提供商支持、智能负载均衡、批量处理、缓存优化和错误恢复。

功能特性:
- 多LLM提供商支持
- 智能负载均衡
- 批量调用优化
- 响应缓存管理
- 错误分类与恢复
- 流式响应处理
- Token使用监控

作者: Claude Code
版本: 1.0
"""

import asyncio
import logging
from typing import (
    TypedDict, List, Optional, Dict, Any, Callable,
    Awaitable, Union, AsyncGenerator
)
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import hashlib
import time
from collections import defaultdict, deque
import random

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class LLMProvider(Enum):
    """LLM提供商"""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    KIMI = "kimi"
    CLAUDE = "claude"
    CUSTOM = "custom"


class RequestPriority(Enum):
    """请求优先级"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class CacheStrategy(Enum):
    """缓存策略"""
    MEMORY = "memory"
    DISK = "disk"
    DISTRIBUTED = "distributed"
    HYBRID = "hybrid"


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: LLMProvider
    model: str
    api_key: str
    base_url: str
    max_tokens: int = 4000
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: float = 60.0
    retry_count: int = 3
    rate_limit: Optional[int] = None  # 每分钟请求数
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMRequest:
    """LLM请求"""
    request_id: str
    prompt: str
    max_tokens: int = 4000
    temperature: float = 0.7
    priority: RequestPriority = RequestPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class LLMResponse:
    """LLM响应"""
    request_id: str
    content: str
    tokens_used: int
    prompt_tokens: int
    completion_tokens: int
    cost: float = 0.0
    latency: float = 0.0
    provider: str = ""
    model: str = ""
    cached: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 2. 响应缓存管理器
# ============================================================================

class ResponseCache:
    """响应缓存管理器"""

    def __init__(self, strategy: CacheStrategy = CacheStrategy.MEMORY):
        self.strategy = strategy
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.access_times = deque(maxlen=1000)
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "size": 0,
        }

    def _generate_cache_key(self, request: LLMRequest) -> str:
        """生成缓存键"""
        content = f"{request.prompt}:{request.temperature}:{request.max_tokens}"
        return hashlib.md5(content.encode()).hexdigest()

    async def get(self, request: LLMRequest) -> Optional[LLMResponse]:
        """获取缓存响应"""
        cache_key = self._generate_cache_key(request)

        if self.strategy == CacheStrategy.MEMORY:
            cached = self.memory_cache.get(cache_key)
            if cached:
                self.stats["hits"] += 1
                return LLMResponse(**cached)
            self.stats["misses"] += 1
            return None

        # TODO: 实现磁盘和分布式缓存
        return None

    async def set(self, request: LLMRequest, response: LLMResponse):
        """设置缓存响应"""
        cache_key = self._generate_cache_key(request)

        if self.strategy == CacheStrategy.MEMORY:
            # LRU淘汰策略
            if len(self.memory_cache) >= 1000:
                oldest_key = min(
                    self.memory_cache.keys(),
                    key=lambda k: self.memory_cache[k]["access_time"]
                )
                del self.memory_cache[oldest_key]
                self.stats["evictions"] += 1

            self.memory_cache[cache_key] = {
                **response.__dict__,
                "access_time": time.time()
            }
            self.stats["size"] = len(self.memory_cache)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        hit_rate = (
            self.stats["hits"] / max(self.stats["hits"] + self.stats["misses"], 1)
        ) * 100

        return {
            **self.stats,
            "hit_rate": hit_rate,
        }


# ============================================================================
# 3. 速率限制器
# ============================================================================

class RateLimiter:
    """速率限制器"""

    def __init__(self, max_requests: int, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """获取令牌"""
        async with self.lock:
            now = time.time()

            # 清理过期请求
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()

            # 检查是否超过限制
            if len(self.requests) >= self.max_requests:
                sleep_time = self.requests[0] + self.time_window - now
                if sleep_time > 0:
                    logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()

            # 添加新请求
            self.requests.append(now)


# ============================================================================
# 4. 高级LLM客户端
# ============================================================================

class AdvancedLLMClient:
    """高级LLM客户端

    功能特性:
    - 多提供商支持
    - 智能负载均衡
    - 批量请求处理
    - 响应缓存
    - 错误重试
    - 速率限制
    """

    def __init__(
        self,
        default_config: LLMConfig,
        configs: Optional[List[LLMConfig]] = None,
        cache_strategy: CacheStrategy = CacheStrategy.MEMORY,
        enable_load_balancing: bool = True
    ):
        self.default_config = default_config
        self.configs = configs or [default_config]
        self.enable_load_balancing = enable_load_balancing

        # 缓存
        self.cache = ResponseCache(cache_strategy)

        # 速率限制器
        self.rate_limiters = {
            config.provider: RateLimiter(
                config.rate_limit or 60,
                time_window=60
            )
            for config in self.configs
        }

        # 负载均衡
        self.provider_load = defaultdict(int)
        self.current_provider_index = 0

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "average_latency": 0.0,
        }

    def _select_provider(self, request: LLMRequest) -> LLMConfig:
        """选择提供商"""
        if not self.enable_load_balancing:
            return self.default_config

        # 策略1: 轮询
        if request.priority == RequestPriority.LOW:
            provider = self.configs[self.current_provider_index]
            self.current_provider_index = (self.current_provider_index + 1) % len(self.configs)
            return provider

        # 策略2: 选择负载最低的
        best_provider = min(
            self.configs,
            key=lambda c: self.provider_load[c.provider]
        )

        return best_provider

    async def call(
        self,
        request: LLMRequest,
        config: Optional[LLMConfig] = None,
        use_cache: bool = True
    ) -> LLMResponse:
        """调用LLM"""

        # 选择配置
        selected_config = config or self._select_provider(request)

        # 检查缓存
        if use_cache:
            cached_response = await self.cache.get(request)
            if cached_response:
                cached_response.cached = True
                return cached_response

        # 应用速率限制
        await self.rate_limiters[selected_config.provider].acquire()

        start_time = time.time()
        self.stats["total_requests"] += 1
        self.provider_load[selected_config.provider] += 1

        try:
            # 调用LLM
            response = await self._make_request(request, selected_config)

            # 更新统计
            latency = time.time() - start_time
            self.stats["successful_requests"] += 1
            self.stats["total_tokens"] += response.tokens_used
            self.stats["total_cost"] += response.cost
            self.stats["average_latency"] = (
                (self.stats["average_latency"] * (self.stats["successful_requests"] - 1) + latency)
                / self.stats["successful_requests"]
            )

            # 缓存响应
            if use_cache:
                await self.cache.set(request, response)

            return response

        except Exception as e:
            self.stats["failed_requests"] += 1
            logger.error(f"LLM request failed: {e}")
            raise

        finally:
            self.provider_load[selected_config.provider] -= 1

    async def _make_request(
        self,
        request: LLMRequest,
        config: LLMConfig
    ) -> LLMResponse:
        """实际发起请求

        这里模拟实际的API调用。
        """
        # 模拟网络延迟
        await asyncio.sleep(random.uniform(0.1, 0.5))

        # 模拟成功率 (95%)
        if random.random() < 0.95:
            return LLMResponse(
                request_id=request.request_id,
                content=f"Response from {config.provider.value}: {request.prompt[:50]}...",
                tokens_used=random.randint(100, 500),
                prompt_tokens=random.randint(50, 200),
                completion_tokens=random.randint(50, 300),
                cost=random.uniform(0.01, 0.05),
                provider=config.provider.value,
                model=config.model,
            )
        else:
            raise Exception(f"Simulated {config.provider.value} error")

    async def batch_call(
        self,
        requests: List[LLMRequest],
        max_concurrent: int = 5,
        use_cache: bool = True
    ) -> List[LLMResponse]:
        """批量调用"""

        # 按优先级排序
        sorted_requests = sorted(
            requests,
            key=lambda r: r.priority.value
        )

        # 分批处理
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def process_request(request: LLMRequest) -> LLMResponse:
            async with semaphore:
                return await self.call(request, use_cache=use_cache)

        # 并发执行
        tasks = [process_request(req) for req in sorted_requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Request {i} failed: {result}")
                responses.append(
                    LLMResponse(
                        request_id=sorted_requests[i].request_id,
                        content="",
                        tokens_used=0,
                        prompt_tokens=0,
                        completion_tokens=0,
                        error=str(result)
                    )
                )
            else:
                responses.append(result)

        return responses

    async def stream_call(
        self,
        request: LLMRequest
    ) -> AsyncGenerator[str, None]:
        """流式调用"""

        config = self._select_provider(request)

        # 模拟流式响应
        for i in range(5):
            chunk = f"Chunk {i+1} from {config.provider.value}: {request.prompt[:30]}..."
            await asyncio.sleep(0.1)
            yield chunk

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        success_rate = (
            self.stats["successful_requests"] / max(self.stats["total_requests"], 1)
        ) * 100

        return {
            **self.stats,
            "success_rate": success_rate,
            "provider_load": dict(self.provider_load),
            "cache_stats": self.cache.get_stats(),
        }


# ============================================================================
# 5. 智能负载均衡器
# ============================================================================

class IntelligentLoadBalancer:
    """智能负载均衡器

    根据延迟、错误率和成本动态分配请求。
    """

    def __init__(self, clients: List[AdvancedLLMClient]):
        self.clients = clients
        self.provider_metrics = defaultdict(lambda: {
            "requests": 0,
            "latencies": deque(maxlen=100),
            "errors": 0,
            "costs": [],
        })

    async def select_best_client(
        self,
        request: LLMRequest,
        budget_limit: Optional[float] = None
    ) -> AdvancedLLMClient:
        """选择最佳客户端"""

        # 过滤符合预算的客户端
        eligible_clients = self.clients
        if budget_limit is not None:
            # 假设平均成本
            eligible_clients = [
                c for c in self.clients
                if c.stats["total_cost"] / max(c.stats["total_requests"], 1) <= budget_limit
            ]

        if not eligible_clients:
            return self.clients[0]

        # 计算综合得分
        best_client = None
        best_score = float("-inf")

        for client in eligible_clients:
            # 计算得分 (延迟越低、错误率越低、吞吐量越高越好)
            metrics = self.provider_metrics[client.default_config.provider]

            latency_score = 1.0 / max(sum(metrics["latencies"]) / max(len(metrics["latencies"]), 1), 0.001)
            error_rate = metrics["errors"] / max(metrics["requests"], 1)
            error_score = 1.0 - error_rate

            throughput = client.stats["total_requests"]
            throughput_score = min(throughput / 100, 1.0)

            # 加权计算
            score = (
                latency_score * 0.4 +
                error_score * 0.4 +
                throughput_score * 0.2
            )

            if score > best_score:
                best_score = score
                best_client = client

        return best_client or self.clients[0]

    async def track_request(
        self,
        client: AdvancedLLMClient,
        latency: float,
        success: bool,
        cost: float
    ):
        """跟踪请求指标"""
        metrics = self.provider_metrics[client.default_config.provider]
        metrics["requests"] += 1
        metrics["latencies"].append(latency)
        if not success:
            metrics["errors"] += 1
        metrics["costs"].append(cost)


# ============================================================================
# 6. 使用示例
# ============================================================================

async def example_advanced_llm():
    """高级LLM配置示例"""

    # 1. 创建多个LLM配置
    configs = [
        LLMConfig(
            provider=LLMProvider.DEEPSEEK,
            model="deepseek-chat",
            api_key="sk-deepseek-xxx",
            base_url="https://api.deepseek.com/v1",
            max_tokens=4000,
            temperature=0.7,
            rate_limit=100,
        ),
        LLMConfig(
            provider=LLMProvider.KIMI,
            model="Kimi-K2",
            api_key="sk-kimi-xxx",
            base_url="https://llmapi.paratera.com/v1",
            max_tokens=4000,
            temperature=0.7,
            rate_limit=80,
        ),
        LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o",
            api_key="sk-openai-xxx",
            base_url="https://api.openai.com/v1",
            max_tokens=4000,
            temperature=0.7,
            rate_limit=60,
        ),
    ]

    # 2. 创建高级客户端
    client = AdvancedLLMClient(
        default_config=configs[0],
        configs=configs,
        cache_strategy=CacheStrategy.MEMORY,
        enable_load_balancing=True
    )

    # 3. 单个请求示例
    print("\n=== 单个请求示例 ===")
    request = LLMRequest(
        request_id="req-001",
        prompt="Explain the concept of artificial intelligence",
        max_tokens=1000,
        temperature=0.7,
        priority=RequestPriority.HIGH
    )

    response = await client.call(request)
    print(f"Response: {response.content[:100]}...")
    print(f"Provider: {response.provider}")
    print(f"Tokens: {response.tokens_used}")
    print(f"Cached: {response.cached}")

    # 4. 批量请求示例
    print("\n=== 批量请求示例 ===")
    batch_requests = [
        LLMRequest(
            request_id=f"req-{i:03d}",
            prompt=f"What is machine learning concept {i}?",
            max_tokens=500,
            priority=RequestPriority.NORMAL
        )
        for i in range(10)
    ]

    batch_responses = await client.batch_call(
        batch_requests,
        max_concurrent=3
    )

    print(f"Processed {len(batch_responses)} requests")
    successful = sum(1 for r in batch_responses if r.content)
    print(f"Successful: {successful}/{len(batch_responses)}")

    # 5. 流式响应示例
    print("\n=== 流式响应示例 ===")
    stream_request = LLMRequest(
        request_id="stream-001",
        prompt="Tell me a story",
        max_tokens=800
    )

    print("Streaming response:")
    async for chunk in client.stream_call(stream_request):
        print(f"  {chunk}")

    # 6. 显示统计信息
    print("\n=== 客户端统计 ===")
    stats = client.get_stats()
    for key, value in stats.items():
        if key != "provider_load":
            print(f"{key}: {value}")

    print("\nProvider load:")
    for provider, load in stats["provider_load"].items():
        print(f"  {provider}: {load}")


# ============================================================================
# 7. 高级功能：错误恢复和重试
# ============================================================================

class RetryManager:
    """重试管理器

    智能重试策略，包括指数退避和错误分类。
    """

    def __init__(self):
        self.retry_policies = {
            "rate_limit": {"max_retries": 5, "backoff": "exponential"},
            "timeout": {"max_retries": 3, "backoff": "fixed"},
            "server_error": {"max_retries": 4, "backoff": "exponential"},
            "auth_error": {"max_retries": 0, "backoff": "none"},
            "unknown": {"max_retries": 2, "backoff": "linear"},
        }

    def classify_error(self, error: Exception) -> str:
        """分类错误类型"""
        error_str = str(error).lower()

        if "rate limit" in error_str:
            return "rate_limit"
        elif "timeout" in error_str:
            return "timeout"
        elif "500" in error_str or "server error" in error_str:
            return "server_error"
        elif "auth" in error_str or "unauthorized" in error_str:
            return "auth_error"
        else:
            return "unknown"

    async def retry_with_backoff(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """带退避的重试"""

        max_attempts = 3
        base_delay = 1.0

        for attempt in range(max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_type = self.classify_error(e)
                policy = self.retry_policies.get(error_type, self.retry_policies["unknown"])

                if attempt >= policy["max_retries"]:
                    raise

                # 计算延迟
                if policy["backoff"] == "exponential":
                    delay = base_delay * (2 ** attempt)
                elif policy["backoff"] == "linear":
                    delay = base_delay * (attempt + 1)
                else:  # fixed
                    delay = base_delay

                logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)

        raise Exception("All retry attempts exhausted")


# ============================================================================
# 8. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_advanced_llm())
