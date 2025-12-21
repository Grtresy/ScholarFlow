#!/usr/bin/env python3
"""
高级代码示例13: 多格式渲染系统
=================================

本示例展示如何构建一个功能完整的多格式演示文稿渲染系统，
用于ScholarFlow中的最终输出生成。

功能特性:
- 多输出格式支持（PPTX、PDF、HTML、Markdown）
- 自定义主题引擎
- 动态样式生成
- 图片优化
- 字体管理
- 批量渲染
- 渲染队列管理
- 质量控制

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
from collections import defaultdict, deque
import hashlib
import base64

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class OutputFormat(Enum):
    """输出格式"""
    PPTX = "pptx"
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    IMAGE = "image"
    VIDEO = "video"


class RenderQuality(Enum):
    """渲染质量"""
    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"
    ULTRA = "ultra"


class ThemeStyle(Enum):
    """主题风格"""
    ACADEMIC = "academic"
    BUSINESS = "business"
    CREATIVE = "creative"
    MINIMAL = "minimal"
    TECH = "tech"


@dataclass
class RenderRequest:
    """渲染请求"""
    request_id: str
    content: str
    format: OutputFormat
    theme: str
    quality: RenderQuality = RenderQuality.STANDARD
    options: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class RenderResult:
    """渲染结果"""
    request_id: str
    output_path: str
    file_size: int
    render_time: float
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Theme:
    """主题"""
    theme_id: str
    name: str
    style: ThemeStyle
    css_template: str
    color_scheme: Dict[str, str]
    fonts: Dict[str, str]
    layout_config: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 2. 主题管理器
# ============================================================================

class ThemeManager:
    """主题管理器

    管理演示文稿主题的创建、应用和自定义。
    """

    def __init__(self):
        self.themes: Dict[str, Theme] = {}
        self.custom_css_cache: Dict[str, str] = {}

    def create_theme(
        self,
        theme_id: str,
        name: str,
        style: ThemeStyle,
        primary_color: str = "#1a73e8",
        secondary_color: str = "#34a853",
        background_color: str = "#ffffff"
    ) -> Theme:
        """创建主题"""

        # 定义CSS模板
        css_template = f"""
/* $theme_name 主题样式 */

{{{{ marpTheme }}}}

:root {{
    --primary-color: {primary_color};
    --secondary-color: {secondary_color};
    --background-color: {background_color};
    --text-color: #202124;
    --accent-color: #ea4335;
}}

/* 标题样式 */
h1 {{
    color: var(--primary-color);
    font-size: 2.5em;
    margin-bottom: 0.5em;
}}

h2 {{
    color: var(--secondary-color);
    font-size: 2em;
    margin-bottom: 0.4em;
}}

h3 {{
    color: var(--text-color);
    font-size: 1.5em;
    margin-bottom: 0.3em;
}}

/* 列表样式 */
ul, ol {{
    margin-left: 2em;
}}

li {{
    margin: 0.5em 0;
}}

/* 代码块样式 */
pre {{
    background-color: #f5f5f5;
    padding: 1em;
    border-radius: 5px;
    overflow-x: auto;
}}

code {{
    font-family: 'Monaco', 'Courier New', monospace;
}}

/* 表格样式 */
table {{
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}}

th, td {{
    border: 1px solid #ddd;
    padding: 0.5em;
    text-align: left;
}}

th {{
    background-color: var(--primary-color);
    color: white;
}}

/* 引用样式 */
blockquote {{
    border-left: 4px solid var(--primary-color);
    padding-left: 1em;
    margin-left: 0;
    font-style: italic;
    color: #666;
}}

/* 图片样式 */
img {{
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
}}

/* 强调样式 */
strong {{
    color: var(--accent-color);
}}

em {{
    color: var(--secondary-color);
}}

/* 页脚样式 */
footer {{
    font-size: 0.8em;
    color: #666;
    position: fixed;
    bottom: 10px;
    right: 10px;
}}
        """

        # 定义配色方案
        color_scheme = {
            "primary": primary_color,
            "secondary": secondary_color,
            "background": background_color,
            "text": "#202124",
            "accent": "#ea4335",
            "muted": "#666666",
        }

        # 定义字体
        fonts = {
            "heading": "Arial, sans-serif",
            "body": "Arial, sans-serif",
            "code": "Monaco, Courier New, monospace",
        }

        # 定义布局配置
        layout_config = {
            "slide_width": "1280px",
            "slide_height": "720px",
            "margin": "40px",
            "title_position": "top",
            "footer_position": "bottom",
        }

        theme = Theme(
            theme_id=theme_id,
            name=name,
            style=style,
            css_template=css_template,
            color_scheme=color_scheme,
            fonts=fonts,
            layout_config=layout_config
        )

        self.themes[theme_id] = theme
        logger.info(f"Created theme: {name}")
        return theme

    def get_theme(self, theme_id: str) -> Optional[Theme]:
        """获取主题"""
        return self.themes.get(theme_id)

    def list_themes(self, style: Optional[ThemeStyle] = None) -> List[Theme]:
        """列出主题"""
        themes = list(self.themes.values())
        if style:
            themes = [t for t in themes if t.style == style]
        return themes

    def customize_theme(
        self,
        theme_id: str,
        updates: Dict[str, Any]
    ) -> Theme:
        """自定义主题"""
        if theme_id not in self.themes:
            raise ValueError(f"Theme not found: {theme_id}")

        theme = self.themes[theme_id]

        # 更新属性
        if "primary_color" in updates:
            theme.color_scheme["primary"] = updates["primary_color"]

        if "secondary_color" in updates:
            theme.color_scheme["secondary"] = updates["secondary_color"]

        if "background_color" in updates:
            theme.color_scheme["background"] = updates["background_color"]

        if "fonts" in updates:
            theme.fonts.update(updates["fonts"])

        # 重新生成CSS
        theme.css_template = self._generate_css(theme)

        logger.info(f"Customized theme: {theme_id}")
        return theme

    def _generate_css(self, theme: Theme) -> str:
        """生成CSS"""
        # 简化实现：根据主题属性生成CSS
        primary = theme.color_scheme.get("primary", "#1a73e8")
        secondary = theme.color_scheme.get("secondary", "#34a853")
        background = theme.color_scheme.get("background", "#ffffff")

        return f"""
:root {{
    --primary-color: {primary};
    --secondary-color: {secondary};
    --background-color: {background};
}}

/* 基础样式 */
h1, h2, h3 {{
    color: var(--primary-color);
}}
        """


# ============================================================================
# 3. 图片优化器
# ============================================================================

class ImageOptimizer:
    """图片优化器

    优化演示文稿中的图片以提高渲染质量。
    """

    def __init__(self):
        self.supported_formats = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"}
        self.max_width = 1920
        self.max_height = 1080
        self.quality_settings = {
            RenderQuality.DRAFT: 60,
            RenderQuality.STANDARD: 75,
            RenderQuality.HIGH: 85,
            RenderQuality.ULTRA: 95,
        }

    async def optimize_image(
        self,
        image_data: bytes,
        quality: RenderQuality = RenderQuality.STANDARD
    ) -> bytes:
        """优化图片"""
        # 模拟图片优化
        # 实际实现中应该使用PIL或其他图像处理库

        target_quality = self.quality_settings[quality]

        # 模拟压缩
        compressed_size = int(len(image_data) * target_quality / 100)
        optimized_data = image_data[:compressed_size]

        logger.info(f"Optimized image: {len(image_data)} -> {len(optimized_data)} bytes")
        return optimized_data

    async def generate_thumbnail(
        self,
        image_data: bytes,
        width: int = 320,
        height: int = 180
    ) -> bytes:
        """生成缩略图"""
        # 模拟缩略图生成
        # 实际实现中应该使用图像处理库
        thumbnail_size = width * height // 10
        thumbnail = image_data[:thumbnail_size]

        return thumbnail

    async def validate_image(self, image_data: bytes) -> Dict[str, Any]:
        """验证图片"""
        # 模拟图片验证
        return {
            "valid": True,
            "width": 800,
            "height": 600,
            "format": "jpeg",
            "size": len(image_data),
            "has_transparency": False,
        }


# ============================================================================
# 4. 渲染引擎接口
# ============================================================================

class RenderEngine(ABC):
    """渲染引擎基类"""

    @abstractmethod
    async def render(
        self,
        request: RenderRequest,
        theme: Theme,
        content: str
    ) -> RenderResult:
        """渲染演示文稿"""
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[OutputFormat]:
        """获取支持的格式"""
        pass


# ============================================================================
# 5. Marp渲染引擎
# ============================================================================

class MarpRenderEngine(RenderEngine):
    """Marp渲染引擎"""

    def __init__(self, theme_manager: ThemeManager, image_optimizer: ImageOptimizer):
        self.theme_manager = theme_manager
        self.image_optimizer = image_optimizer
        self.output_dir = Path("./output")
        self.output_dir.mkdir(exist_ok=True)

    def get_supported_formats(self) -> List[OutputFormat]:
        """获取支持的格式"""
        return [OutputFormat.PDF, OutputFormat.HTML, OutputFormat.PPTX]

    async def render(
        self,
        request: RenderRequest,
        theme: Theme,
        content: str
    ) -> RenderResult:
        """使用Marp渲染"""
        start_time = datetime.now()

        try:
            # 生成Marp Markdown
            marp_content = await self._generate_marp_content(content, theme, request)

            # 保存临时文件
            temp_file = self.output_dir / f"{request.request_id}.md"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(marp_content)

            # 执行Marp渲染（模拟）
            output_path = await self._execute_marp_render(temp_file, request)

            # 计算文件大小
            file_size = output_path.stat().st_size

            # 计算渲染时间
            render_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"Rendered {request.format.value} in {render_time:.2f}s")

            return RenderResult(
                request_id=request.request_id,
                output_path=str(output_path),
                file_size=file_size,
                render_time=render_time,
                success=True
            )

        except Exception as e:
            render_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Render failed: {e}")

            return RenderResult(
                request_id=request.request_id,
                output_path="",
                file_size=0,
                render_time=render_time,
                success=False,
                error=str(e)
            )

    async def _generate_marp_content(
        self,
        content: str,
        theme: Theme,
        request: RenderRequest
    ) -> str:
        """生成Marp Markdown内容"""
        # 替换主题变量
        css = theme.css_template.replace("{{ marpTheme }}", f"/* {theme.name} */")

        # 构建Marp文档
        marp_doc = f"""---
marp: true
theme: {theme.theme_id}
backgroundColor: {theme.color_scheme['background']}
color: {theme.color_scheme['text']}
paginate: true
---

<style>
{css}
</style>

{content}
"""

        return marp_doc

    async def _execute_marp_render(
        self,
        md_file: Path,
        request: RenderRequest
    ) -> Path:
        """执行Marp渲染命令"""
        # 模拟Marp CLI执行
        output_file = self.output_dir / f"{request.request_id}.{request.format.value}"

        # 实际实现中应该调用marp-cli：
        # marp {md_file} --output {output_file} --format {request.format.value}

        # 模拟渲染
        with open(output_file, 'wb') as f:
            f.write(b"Rendered content")

        return output_file


# ============================================================================
# 6. 自定义渲染引擎
# ============================================================================

class CustomHTMLEngine(RenderEngine):
    """自定义HTML渲染引擎"""

    def __init__(self, theme_manager: ThemeManager):
 = theme_manager
        self.theme_manager        self.output_dir = Path("./output")
        self.output_dir.mkdir(exist_ok=True)

    def get_supported_formats(self) -> List[OutputFormat]:
        """获取支持的格式"""
        return [OutputFormat.HTML, OutputFormat.MARKDOWN]

    async def render(
        self,
        request: RenderRequest,
        theme: Theme,
        content: str
    ) -> RenderResult:
        """渲染HTML"""
        start_time = datetime.now()

        try:
            # 生成HTML
            html_content = await self._generate_html(content, theme, request)

            # 保存文件
            output_file = self.output_dir / f"{request.request_id}.html"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            file_size = output_file.stat().st_size
            render_time = (datetime.now() - start_time).total_seconds()

            return RenderResult(
                request_id=request.request_id,
                output_path=str(output_file),
                file_size=file_size,
                render_time=render_time,
                success=True
            )

        except Exception as e:
            render_time = (datetime.now() - start_time).total_seconds()
            return RenderResult(
                request_id=request.request_id,
                output_path="",
                file_size=0,
                render_time=render_time,
                success=False,
                error=str(e)
            )

    async def _generate_html(
        self,
        content: str,
        theme: Theme,
        request: RenderRequest
    ) -> str:
        """生成HTML"""
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{theme.name}</title>
    <style>
        body {{
            font-family: {theme.fonts['body']};
            background-color: {theme.color_scheme['background']};
            color: {theme.color_scheme['text']};
            margin: 0;
            padding: 40px;
        }}
        .slide {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        {theme.css_template}
    </style>
</head>
<body>
    <div class="slide">
        {content}
    </div>
</body>
</html>"""
        return html


# ============================================================================
# 7. 多格式渲染器
# ============================================================================

class MultiFormatRenderer:
    """多格式渲染器

    统一管理多种渲染引擎，支持批量渲染和格式转换。
    """

    def __init__(self):
        self.theme_manager = ThemeManager()
        self.image_optimizer = ImageOptimizer()
        self.engines: Dict[OutputFormat, RenderEngine] = {}
        self.render_queue: deque = deque()
        self.active_renders: Dict[str, asyncio.Task] = {}

        # 注册默认引擎
        self._register_default_engines()

        # 统计信息
        self.stats = {
            "total_renders": 0,
            "successful_renders": 0,
            "failed_renders": 0,
            "render_times": [],
        }

    def _register_default_engines(self):
        """注册默认引擎"""
        marp_engine = MarpRenderEngine(self.theme_manager, self.image_optimizer)
        html_engine = CustomHTMLEngine(self.theme_manager)

        for fmt in marp_engine.get_supported_formats():
            self.engines[fmt] = marp_engine

        for fmt in html_engine.get_supported_formats():
            if fmt not in self.engines:
                self.engines[fmt] = html_engine

    def register_engine(self, format_type: OutputFormat, engine: RenderEngine):
        """注册渲染引擎"""
        self.engines[format_type] = engine
        logger.info(f"Registered engine for {format_type.value}")

    async def render(
        self,
        content: str,
        output_format: OutputFormat,
        theme_id: str,
        quality: RenderQuality = RenderQuality.STANDARD,
        options: Optional[Dict[str, Any]] = None
    ) -> RenderResult:
        """渲染演示文稿"""
        request = RenderRequest(
            request_id=str(uuid.uuid4()),
            content=content,
            format=output_format,
            theme=theme_id,
            quality=quality,
            options=options or {}
        )

        # 获取主题
        theme = self.theme_manager.get_theme(theme_id)
        if not theme:
            raise ValueError(f"Theme not found: {theme_id}")

        # 获取引擎
        engine = self.engines.get(output_format)
        if not engine:
            raise ValueError(f"No engine for format: {output_format.value}")

        # 执行渲染
        result = await engine.render(request, theme, content)

        # 更新统计
        self.stats["total_renders"] += 1
        if result.success:
            self.stats["successful_renders"] += 1
            self.stats["render_times"].append(result.render_time)
        else:
            self.stats["failed_renders"] += 1

        return result

    async def batch_render(
        self,
        requests: List[Dict[str, Any]]
    ) -> List[RenderResult]:
        """批量渲染"""
        tasks = []
        for req_data in requests:
            task = asyncio.create_task(
                self.render(
                    content=req_data["content"],
                    output_format=req_data["format"],
                    theme_id=req_data["theme"],
                    quality=req_data.get("quality", RenderQuality.STANDARD),
                    options=req_data.get("options", {})
                )
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        avg_render_time = (
            sum(self.stats["render_times"]) / max(len(self.stats["render_times"]), 1)
        )

        success_rate = (
            self.stats["successful_renders"] / max(self.stats["total_renders"], 1) * 100
        )

        return {
            **self.stats,
            "average_render_time": avg_render_time,
            "success_rate": success_rate,
            "registered_engines": [fmt.value for fmt in self.engines.keys()],
        }


# ============================================================================
# 8. 使用示例
# ============================================================================

async def example_multi_format_render():
    """多格式渲染示例"""

    # 1. 创建渲染器
    print("\n=== 创建多格式渲染器 ===")
    renderer = MultiFormatRenderer()

    # 2. 创建主题
    print("\n=== 创建主题 ===")
    academic_theme = renderer.theme_manager.create_theme(
        theme_id="academic_v1",
        name="Academic Theme",
        style=ThemeStyle.ACADEMIC,
        primary_color="#1a73e8",
        secondary_color="#34a853",
        background_color="#ffffff"
    )

    business_theme = renderer.theme_manager.create_theme(
        theme_id="business_v1",
        name="Business Theme",
        style=ThemeStyle.BUSINESS,
        primary_color="#2c3e50",
        secondary_color="#e74c3c",
        background_color="#ecf0f1"
    )

    print(f"创建了主题: {academic_theme.name}")
    print(f"创建了主题: {business_theme.name}")

    # 3. 列出主题
    print("\n=== 可用主题 ===")
    themes = renderer.theme_manager.list_themes()
    for theme in themes:
        print(f"  {theme.name} ({theme.style.value})")

    # 4. 渲染单个格式
    print("\n=== 渲染PDF ===")
    pdf_content = """
# 研究论文标题

## 摘要
本研究探讨了机器学习在自然语言处理中的应用。

## 方法
- 数据收集
- 模型训练
- 结果分析

## 结论
机器学习技术在NLP领域具有广阔的应用前景。
    """

    pdf_result = await renderer.render(
        content=pdf_content,
        output_format=OutputFormat.PDF,
        theme_id="academic_v1",
        quality=RenderQuality.HIGH
    )

    print(f"PDF渲染结果:")
    print(f"  文件: {pdf_result.output_path}")
    print(f"  大小: {pdf_result.file_size} bytes")
    print(f"  时间: {pdf_result.render_time:.2f}s")
    print(f"  成功: {pdf_result.success}")

    # 5. 渲染HTML
    print("\n=== 渲染HTML ===")
    html_result = await renderer.render(
        content=pdf_content,
        output_format=OutputFormat.HTML,
        theme_id="business_v1"
    )

    print(f"HTML渲染结果:")
    print(f"  文件: {html_result.output_path}")
    print(f"  成功: {html_result.success}")

    # 6. 自定义主题
    print("\n=== 自定义主题 ===")
    custom_theme = renderer.theme_manager.customize_theme(
        theme_id="academic_v1",
        updates={
            "primary_color": "#9c27b0",
            "secondary_color": "#ff9800",
        }
    )
    print(f"自定义主题颜色: {custom_theme.color_scheme}")

    # 7. 批量渲染
    print("\n=== 批量渲染 ===")
    batch_requests = [
        {
            "content": "# 幻灯片 1\n内容1",
            "format": OutputFormat.PDF,
            "theme": "academic_v1",
            "quality": RenderQuality.STANDARD
        },
        {
            "content": "# 幻灯片 2\n内容2",
            "format": OutputFormat.HTML,
            "theme": "business_v1",
            "quality": RenderQuality.STANDARD
        },
        {
            "content": "# 幻灯片 3\n内容3",
            "format": OutputFormat.MARKDOWN,
            "theme": "academic_v1",
            "quality": RenderQuality.DRAFT
        },
    ]

    batch_results = await renderer.batch_render(batch_requests)

    print(f"批量渲染完成: {len(batch_results)} 个文件")
    for i, result in enumerate(batch_results):
        print(f"  文件 {i+1}: {result.success} ({result.file_size} bytes)")

    # 8. 显示统计信息
    print("\n=== 渲染统计 ===")
    stats = renderer.get_stats()
    for key, value in stats.items():
        if key != "render_times":
            print(f"{key}: {value}")


# ============================================================================
# 9. 高级功能：格式转换
# ============================================================================

class FormatConverter:
    """格式转换器

    在不同输出格式之间进行转换。
    """

    def __init__(self, renderer: MultiFormatRenderer):
        self.renderer = renderer

    async def convert(
        self,
        source_file: str,
        source_format: OutputFormat,
        target_format: OutputFormat,
        theme_id: str
    ) -> RenderResult:
        """转换格式"""
        # 读取源文件内容
        with open(source_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 重新渲染为目标格式
        result = await self.renderer.render(
            content=content,
            output_format=target_format,
            theme_id=theme_id
        )

        return result


# ============================================================================
# 10. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_multi_format_render())
