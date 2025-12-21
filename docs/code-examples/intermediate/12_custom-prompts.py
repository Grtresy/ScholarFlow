#!/usr/bin/env python3
"""
高级代码示例12: 自定义提示词模板
==================================

本示例展示如何构建一个功能完整的自定义提示词管理系统，
用于ScholarFlow工作流中的LLM调用。

功能特性:
- 动态提示词模板
- 变量插值
- 条件渲染
- 多语言支持
- 提示词优化
- 版本管理
- A/B测试
- 性能监控

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
from string import Template
from collections import defaultdict
import hashlib

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class PromptType(Enum):
    """提示词类型"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TASK_SPECIFIC = "task_specific"
    ERROR_HANDLING = "error_handling"


class RenderMode(Enum):
    """渲染模式"""
    STRICT = "strict"      # 严格模式
    FLEXIBLE = "flexible"  # 灵活模式
    CONDITIONAL = "conditional"  # 条件模式


@dataclass
class PromptVariable:
    """提示词变量"""
    name: str
    required: bool = True
    default: Any = None
    description: str = ""
    validator: Optional[Callable] = None


@dataclass
class PromptTemplate:
    """提示词模板"""
    template_id: str
    name: str
    prompt_type: PromptType
    content: str
    variables: List[PromptVariable] = field(default_factory=list)
    version: str = "1.0"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RenderedPrompt:
    """渲染后的提示词"""
    template_id: str
    content: str
    variables_used: Dict[str, Any]
    render_time: float
    checksum: str
    rendered_at: datetime = field(default_factory=datetime.now)


@dataclass
class PromptMetrics:
    """提示词指标"""
    template_id: str
    usage_count: int = 0
    average_latency: float = 0.0
    success_rate: float = 0.0
    token_count: int = 0
    last_used: Optional[datetime] = None


# ============================================================================
# 2. 变量验证器
# ============================================================================

class VariableValidator:
    """变量验证器"""

    @staticmethod
    def validate_type(value: Any, expected_type: type) -> bool:
        """验证类型"""
        if expected_type == List[str]:
            return isinstance(value, list) and all(isinstance(item, str) for item in value)
        return isinstance(value, expected_type)

    @staticmethod
    def validate_range(value: Any, min_val: Any = None, max_val: Any = None) -> bool:
        """验证范围"""
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True

    @staticmethod
    def validate_choices(value: Any, choices: List[Any]) -> bool:
        """验证选择"""
        return value in choices

    @staticmethod
    def validate_pattern(value: str, pattern: str) -> bool:
        """验证正则表达式"""
        return bool(re.match(pattern, value))

    @staticmethod
    def validate_custom(value: Any, validator_func: Callable) -> bool:
        """验证自定义函数"""
        try:
            return validator_func(value)
        except Exception:
            return False


# ============================================================================
# 3. 高级提示词渲染器
# ============================================================================

class AdvancedPromptRenderer:
    """高级提示词渲染器

    功能特性:
    - 多模式渲染
    - 变量验证
    - 条件逻辑
    - 循环支持
    - 过滤器
    - 转义处理
    """

    def __init__(self, mode: RenderMode = RenderMode.FLEXIBLE):
        self.mode = mode
        self.filters = {
            "upper": lambda x: str(x).upper(),
            "lower": lambda x: str(x).lower(),
            "strip": lambda x: str(x).strip(),
            "length": lambda x: len(str(x)),
            "json": lambda x: json.dumps(x, ensure_ascii=False),
            "truncate": lambda x, n=100: str(x)[:n] + "..." if len(str(x)) > n else str(x),
        }

    async def render(
        self,
        template: PromptTemplate,
        variables: Dict[str, Any],
        validate: bool = True
    ) -> RenderedPrompt:
        """渲染提示词"""
        start_time = datetime.now()

        # 验证变量
        if validate:
            await self._validate_variables(template, variables)

        # 预处理内容
        content = await self._preprocess_content(template.content, variables)

        # 渲染变量
        content = await self._render_variables(content, variables)

        # 后处理内容
        content = await self._postprocess_content(content, variables)

        # 计算校验和
        checksum = hashlib.sha256(content.encode()).hexdigest()

        # 计算渲染时间
        render_time = (datetime.now() - start_time).total_seconds()

        return RenderedPrompt(
            template_id=template.template_id,
            content=content,
            variables_used=variables,
            render_time=render_time,
            checksum=checksum
        )

    async def _validate_variables(
        self,
        template: PromptTemplate,
        variables: Dict[str, Any]
    ):
        """验证变量"""
        for var in template.variables:
            value = variables.get(var.name)

            # 检查必需变量
            if var.required and value is None:
                if var.default is not None:
                    variables[var.name] = var.default
                else:
                    raise ValueError(f"Required variable missing: {var.name}")

            # 验证变量
            if value is not None and var.validator:
                if not var.validator(value):
                    raise ValueError(f"Variable validation failed: {var.name}")

    async def _preprocess_content(
        self,
        content: str,
        variables: Dict[str, Any]
    ) -> str:
        """预处理内容"""
        # 处理条件块
        if self.mode == RenderMode.CONDITIONAL:
            content = await self._process_conditional_blocks(content, variables)

        # 处理循环
        content = await self._process_loops(content, variables)

        return content

    async def _render_variables(self, content: str, variables: Dict[str, Any]) -> str:
        """渲染变量"""
        # 使用Template进行基础替换
        try:
            template = Template(content)
            rendered = template.safe_substitute(variables)
            return rendered
        except Exception as e:
            logger.error(f"Variable rendering failed: {e}")
            raise

    async def _postprocess_content(
        self,
        content: str,
        variables: Dict[str, Any]
    ) -> str:
        """后处理内容"""
        # 应用过滤器
        for filter_name, filter_func in self.filters.items():
            pattern = r"\|" + filter_name + r"(?:\([^)]*\))?"
            matches = re.finditer(pattern, content)

            for match in reversed(list(matches)):  # 从后往前替换
                filter_expr = match.group(0)
                # 提取过滤器参数
                params = re.findall(r"\(([^)]*)\)", filter_expr)
                param_values = [p.strip() for p in params]

                # 应用过滤器
                try:
                    if filter_name == "truncate" and param_values:
                        n = int(param_values[0])
                        content = content[:match.start()] + f"{{{n}}}" + content[match.end():]
                        variables[n] = filter_func(variables.get("__last_value", ""), n)
                    else:
                        content = content[:match.start()] + "${" + filter_name + "}" + content[match.end():]
                except Exception as e:
                    logger.warning(f"Filter application failed: {e}")

        return content

    async def _process_conditional_blocks(
        self,
        content: str,
        variables: Dict[str, Any]
    ) -> str:
        """处理条件块"""
        # 匹配 {% if condition %} ... {% endif %}
        pattern = r"{%\s*if\s+(.+?)\s*%}(.*?){%\s*endif\s*%}"

        def replace_conditional(match):
            condition = match.group(1).strip()
            block_content = match.group(2)

            # 简单条件评估
            if self._evaluate_condition(condition, variables):
                return block_content
            return ""

        return re.sub(pattern, replace_conditional, content, flags=re.DOTALL)

    def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """评估条件"""
        # 简化实现：检查变量是否存在且为真
        condition = condition.strip()
        if condition.startswith("not "):
            var_name = condition[4:].strip()
            return not bool(variables.get(var_name))

        var_name = condition
        return bool(variables.get(var_name))

    async def _process_loops(
        self,
        content: str,
        variables: Dict[str, Any]
    ) -> str:
        """处理循环"""
        # 匹配 {% for item in list %} ... {% endfor %}
        pattern = r"{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%}(.*?){%\s*endfor\s*%}"

        def replace_loop(match):
            item_var = match.group(1)
            list_var = match.group(2)
            block_content = match.group(3)

            items = variables.get(list_var, [])
            if not isinstance(items, list):
                return ""

            result = []
            for item in items:
                # 设置循环变量
                loop_vars = variables.copy()
                loop_vars[item_var] = item
                loop_vars["loop"] = {
                    "index": len(result) + 1,
                    "first": len(result) == 0,
                    "last": len(result) == len(items) - 1,
                }

                # 渲染块内容
                try:
                    template = Template(block_content)
                    rendered = template.safe_substitute(loop_vars)
                    result.append(rendered)
                except Exception as e:
                    logger.warning(f"Loop rendering failed: {e}")

            return "".join(result)

        return re.sub(pattern, replace_loop, content, flags=re.DOTALL)


# ============================================================================
# 4. 提示词模板管理器
# ============================================================================

class PromptTemplateManager:
    """提示词模板管理器

    管理提示词模板的创建、更新、版本控制和优化。
    """

    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self.renderer = AdvancedPromptRenderer()
        self.metrics: Dict[str, PromptMetrics] = defaultdict(PromptMetrics)
        self.version_history: Dict[str, List[str]] = defaultdict(list)

    def create_template(
        self,
        template_id: str,
        name: str,
        prompt_type: PromptType,
        content: str,
        variables: Optional[List[PromptVariable]] = None,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> PromptTemplate:
        """创建模板"""
        template = PromptTemplate(
            template_id=template_id,
            name=name,
            prompt_type=prompt_type,
            content=content,
            variables=variables or [],
            description=description,
            tags=tags or []
        )

        self.templates[template_id] = template
        self.version_history[template_id].append(template.version)

        logger.info(f"Created template: {template_id}")
        return template

    def update_template(
        self,
        template_id: str,
        new_content: str,
        new_version: Optional[str] = None
    ) -> PromptTemplate:
        """更新模板"""
        if template_id not in self.templates:
            raise ValueError(f"Template not found: {template_id}")

        template = self.templates[template_id]
        template.content = new_content

        if new_version:
            template.version = new_version
            self.version_history[template_id].append(new_version)

        logger.info(f"Updated template: {template_id} to version {template.version}")
        return template

    async def render(
        self,
        template_id: str,
        variables: Dict[str, Any],
        validate: bool = True
    ) -> RenderedPrompt:
        """渲染模板"""
        if template_id not in self.templates:
            raise ValueError(f"Template not found: {template_id}")

        template = self.templates[template_id]
        rendered = await self.renderer.render(template, variables, validate)

        # 更新指标
        metrics = self.metrics[template_id]
        metrics.usage_count += 1
        metrics.average_latency = (
            (metrics.average_latency * (metrics.usage_count - 1) + rendered.render_time)
            / metrics.usage_count
        )
        metrics.last_used = datetime.now()
        metrics.token_count = len(rendered.content.split())

        return rendered

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """获取模板"""
        return self.templates.get(template_id)

    def list_templates(
        self,
        prompt_type: Optional[PromptType] = None,
        tag: Optional[str] = None
    ) -> List[PromptTemplate]:
        """列出模板"""
        templates = list(self.templates.values())

        if prompt_type:
            templates = [t for t in templates if t.prompt_type == prompt_type]

        if tag:
            templates = [t for t in templates if tag in t.tags]

        return templates

    def get_metrics(self, template_id: str) -> PromptMetrics:
        """获取指标"""
        return self.metrics[template_id]

    def get_all_metrics(self) -> Dict[str, PromptMetrics]:
        """获取所有指标"""
        return dict(self.metrics)


# ============================================================================
# 5. 预定义模板
# ============================================================================

def create_predefined_templates(manager: PromptTemplateManager):
    """创建预定义模板"""

    # Stage 1 提示词
    manager.create_template(
        template_id="stage1_academic",
        name="Stage 1 Academic Outline",
        prompt_type=PromptType.TASK_SPECIFIC,
        content="""
你是一个专业的学术论文演示专家。请根据以下内容创建一份专业的学术演示大纲。

内容: $content

演示风格: $style

要求:
1. 创建 $target_slides 张幻灯片的大纲
2. 每张幻灯片包含标题和3-5个要点
3. 保持学术严谨性和逻辑性
4. 突出关键研究发现和贡献
5. 使用专业术语但保持清晰

输出格式:
# 幻灯片标题
- 要点1
- 要点2
- ...

请确保内容结构清晰，逻辑连贯。
        """,
        variables=[
            PromptVariable("content", required=True, description="论文内容"),
            PromptVariable("style", required=True, description="演示风格"),
            PromptVariable("target_slides", required=True, description="目标幻灯片数"),
        ],
        description="Stage 1阶段学术风格大纲生成",
        tags=["stage1", "academic", "outline"]
    )

    # Stage 2 提示词
    manager.create_template(
        template_id="stage2_academic",
        name="Stage 2 Academic Rendering",
        prompt_type=PromptType.TASK_SPECIFIC,
        content="""
你是一个专业的演示文稿排版专家。请将以下大纲转换为Marp Markdown格式。

大纲: $outline

主题: $theme

要求:
1. 使用Marp Markdown语法
2. 应用学术主题样式
3. 包含适当的过渡效果
4. 添加演讲者备注
5. 保持专业美观

主题颜色: $theme_color

输出格式:
```marp
---
marp: true
theme: $theme
---

# 幻灯片标题

内容...

---
```

请确保语法正确，样式美观。
        """,
        variables=[
            PromptVariable("outline", required=True, description="幻灯片大纲"),
            PromptVariable("theme", required=True, description="主题名称"),
            PromptVariable("theme_color", required=False, default="#1a73e8", description="主题颜色"),
        ],
        description="Stage 2阶段Marp渲染",
        tags=["stage2", "rendering", "marp"]
    )

    # 错误处理提示词
    manager.create_template(
        template_id="error_handling",
        name="Error Handling",
        prompt_type=PromptType.ERROR_HANDLING,
        content="""
遇到错误: $error_message

当前状态: $current_state

请分析错误原因并提供解决方案:

1. 错误分析: $error_analysis
2. 解决步骤: $solution_steps
3. 预防措施: $prevention

{% if retry_attempts > 0 %}
当前重试次数: $retry_attempts / $max_retries
{% endif %}

请提供详细的错误恢复指南。
        """,
        variables=[
            PromptVariable("error_message", required=True, description="错误信息"),
            PromptVariable("current_state", required=True, description="当前状态"),
            PromptVariable("error_analysis", required=False, description="错误分析"),
            PromptVariable("solution_steps", required=False, description="解决步骤"),
            PromptVariable("prevention", required=False, description="预防措施"),
            PromptVariable("retry_attempts", required=False, default=0, description="重试次数"),
            PromptVariable("max_retries", required=False, default=3, description="最大重试数"),
        ],
        description="错误处理指南",
        tags=["error", "recovery"]
    )


# ============================================================================
# 6. 提示词优化器
# ============================================================================

class PromptOptimizer:
    """提示词优化器

    分析和优化提示词的性能和效果。
    """

    def __init__(self, manager: PromptTemplateManager):
        self.manager = manager

    async def analyze_template(self, template_id: str) -> Dict[str, Any]:
        """分析模板"""
        if template_id not in self.manager.templates:
            raise ValueError(f"Template not found: {template_id}")

        template = self.manager.templates[template_id]
        metrics = self.manager.get_metrics(template_id)

        analysis = {
            "template_id": template_id,
            "version": template.version,
            "usage_count": metrics.usage_count,
            "average_latency": metrics.average_latency,
            "token_count": metrics.token_count,
            "complexity_score": self._calculate_complexity(template.content),
            "suggestions": [],
        }

        # 生成优化建议
        if metrics.average_latency > 1.0:
            analysis["suggestions"].append("Consider reducing prompt length to improve latency")

        if metrics.token_count > 3000:
            analysis["suggestions"].append("Prompt is very long, consider splitting into smaller parts")

        if metrics.success_rate < 0.8:
            analysis["suggestions"].append("Low success rate, review variable validation")

        if analysis["complexity_score"] > 0.7:
            analysis["suggestions"].append("High complexity, simplify conditional logic")

        return analysis

    def _calculate_complexity(self, content: str) -> float:
        """计算复杂度分数"""
        complexity = 0.0

        # 变量数量
        variables = re.findall(r"\$(\w+)", content)
        complexity += len(variables) * 0.1

        # 条件块数量
        conditionals = len(re.findall(r"{%\s*if", content))
        complexity += conditionals * 0.2

        # 循环数量
        loops = len(re.findall(r"{%\s*for", content))
        complexity += loops * 0.3

        # 长度
        length_score = min(len(content) / 1000, 1.0)
        complexity += length_score * 0.3

        # 过滤器数量
        filters = len(re.findall(r"\|", content))
        complexity += filters * 0.1

        return min(complexity, 1.0)

    async def optimize_template(self, template_id: str) -> str:
        """优化模板"""
        analysis = await self.analyze_template(template_id)
        template = self.manager.templates[template_id]

        optimized_content = template.content

        # 简单优化：移除多余的空行
        optimized_content = re.sub(r"\n\s*\n\s*\n", "\n\n", optimized_content)

        # 优化：合并连续的空格
        optimized_content = re.sub(r" {2,}", " ", optimized_content)

        # 更新模板
        self.manager.update_template(template_id, optimized_content)

        return optimized_content


# ============================================================================
# 7. 使用示例
# ============================================================================

async def example_custom_prompts():
    """自定义提示词示例"""

    # 1. 创建管理器
    print("\n=== 创建提示词模板管理器 ===")
    manager = PromptTemplateManager()

    # 2. 创建预定义模板
    print("\n=== 创建预定义模板 ===")
    create_predefined_templates(manager)

    # 3. 渲染Stage 1模板
    print("\n=== 渲染Stage 1模板 ===")
    variables1 = {
        "content": "This is a research paper about machine learning...",
        "style": "academic",
        "target_slides": 10
    }
    rendered1 = await manager.render("stage1_academic", variables1)
    print(f"渲染时间: {rendered1.render_time:.3f}s")
    print(f"内容预览:\n{rendered1.content[:300]}...")

    # 4. 渲染Stage 2模板
    print("\n=== 渲染Stage 2模板 ===")
    variables2 = {
        "outline": "# Introduction\n- Point 1\n- Point 2",
        "theme": "academic",
        "theme_color": "#2c3e50"
    }
    rendered2 = await manager.render("stage2_academic", variables2)
    print(f"内容预览:\n{rendered2.content[:300]}...")

    # 5. 渲染错误处理模板
    print("\n=== 渲染错误处理模板 ===")
    error_variables = {
        "error_message": "LLM API timeout",
        "current_state": "Processing stage 1",
        "error_analysis": "API响应超时",
        "solution_steps": "1. 检查网络连接\n2. 增加超时时间\n3. 使用备用API",
        "prevention": "实施重试机制和超时控制",
        "retry_attempts": 2,
        "max_retries": 3
    }
    rendered3 = await manager.render("error_handling", error_variables)
    print(f"内容预览:\n{rendered3.content[:300]}...")

    # 6. 列出所有模板
    print("\n=== 模板列表 ===")
    templates = manager.list_templates()
    for template in templates:
        print(f"\n{template.name} ({template.template_id}):")
        print(f"  类型: {template.prompt_type.value}")
        print(f"  版本: {template.version}")
        print(f"  变量数: {len(template.variables)}")
        print(f"  标签: {', '.join(template.tags)}")

    # 7. 显示指标
    print("\n=== 模板指标 ===")
    metrics = manager.get_all_metrics()
    for template_id, metric in metrics.items():
        print(f"\n{template_id}:")
        print(f"  使用次数: {metric.usage_count}")
        print(f"  平均延迟: {metric.average_latency:.3f}s")
        print(f"  Token数: {metric.token_count}")
        print(f"  最后使用: {metric.last_used.strftime('%H:%M:%S') if metric.last_used else 'N/A'}")

    # 8. 分析和优化
    print("\n=== 模板分析 ===")
    optimizer = PromptOptimizer(manager)
    analysis = await optimizer.analyze_template("stage1_academic")
    print(f"分析结果:")
    for key, value in analysis.items():
        if key != "suggestions":
            print(f"  {key}: {value}")

    if analysis["suggestions"]:
        print(f"  建议:")
        for suggestion in analysis["suggestions"]:
            print(f"    - {suggestion}")

    # 9. 优化模板
    print("\n=== 优化模板 ===")
    optimized = await optimizer.optimize_template("stage1_academic")
    print(f"优化后的模板长度: {len(optimized)}")


# ============================================================================
# 8. 高级功能：A/B测试
# ============================================================================

class ABTestManager:
    """A/B测试管理器

    比较不同提示词模板的效果。
    """

    def __init__(self, manager: PromptTemplateManager):
        self.manager = manager
        self.tests: Dict[str, Dict[str, Any]] = {}

    def create_test(
        self,
        test_name: str,
        template_a: str,
        template_b: str,
        traffic_split: float = 0.5
    ):
        """创建A/B测试"""
        self.tests[test_name] = {
            "template_a": template_a,
            "template_b": template_b,
            "traffic_split": traffic_split,
            "metrics_a": {"count": 0, "success": 0, "latency": []},
            "metrics_b": {"count": 0, "success": 0, "latency": []},
        }

    def select_template(self, test_name: str) -> str:
        """选择模板"""
        if test_name not in self.tests:
            raise ValueError(f"Test not found: {test_name}")

        test = self.tests[test_name]
        return test["template_a"] if random.random() < test["traffic_split"] else test["template_b"]

    def record_result(self, test_name: str, template_id: str, latency: float, success: bool):
        """记录结果"""
        if test_name not in self.tests:
            return

        test = self.tests[test_name]
        key = "metrics_a" if template_id == test["template_a"] else "metrics_b"

        test[key]["count"] += 1
        if success:
            test[key]["success"] += 1
        test[key]["latency"].append(latency)

    def get_results(self, test_name: str) -> Dict[str, Any]:
        """获取测试结果"""
        if test_name not in self.tests:
            return {}

        test = self.tests[test_name]

        results = {}
        for key in ["metrics_a", "metrics_b"]:
            metrics = test[key]
            template_id = test[key.replace("metrics", "template")]
            success_rate = metrics["success"] / max(metrics["count"], 1)
            avg_latency = sum(metrics["latency"]) / max(len(metrics["latency"]), 1)

            results[template_id] = {
                "count": metrics["count"],
                "success_rate": success_rate,
                "average_latency": avg_latency,
            }

        return results


# ============================================================================
# 9. 主函数
# ============================================================================

if __name__ == "__main__":
    import random
    asyncio.run(example_custom_prompts())
