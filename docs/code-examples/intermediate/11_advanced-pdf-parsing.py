#!/usr/bin/env python3
"""
高级代码示例11: 高级PDF解析
============================

本示例展示如何构建一个功能完整的高级PDF解析系统，
用于ScholarFlow中的PDF文档处理和内容提取。

功能特性:
- 多格式支持（PDF、图片、扫描件）
- 智能内容识别
- 图像提取与处理
- 表格检测与解析
- 数学公式识别
- 多语言支持
- 批量处理
- 进度监控

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
import hashlib
from pathlib import Path
from collections import defaultdict, deque
import re
import base64
from io import BytesIO

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 数据结构和枚举
# ============================================================================

class DocumentType(Enum):
    """文档类型"""
    ACADEMIC_PAPER = "academic_paper"
    TECHNICAL_REPORT = "technical_report"
    BOOK_CHAPTER = "book_chapter"
    PRESENTATION = "presentation"
    UNKNOWN = "unknown"


class ImageFormat(Enum):
    """图像格式"""
    JPEG = "jpeg"
    PNG = "png"
    TIFF = "tiff"
    BMP = "bmp"
    SVG = "svg"


class ExtractionMode(Enum):
    """提取模式"""
    FAST = "fast"          # 快速提取
    BALANCED = "balanced"  # 平衡模式
    DETAILED = "detailed"  # 详细提取
    OCR = "ocr"           # OCR模式


@dataclass
class PDFMetadata:
    """PDF元数据"""
    filename: str
    file_size: int
    page_count: int
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    encrypted: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedImage:
    """提取的图像"""
    image_id: str
    page_number: int
    format: ImageFormat
    width: int
    height: int
    data: bytes
    hash: str
    alt_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedTable:
    """提取的表格"""
    table_id: str
    page_number: int
    rows: int
    columns: int
    data: List[List[str]]
    headers: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedFormula:
    """提取的公式"""
    formula_id: str
    page_number: int
    latex: Optional[str] = None
    mathml: Optional[str] = None
    image_data: Optional[bytes] = None
    position: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """提取结果"""
    document_id: str
    metadata: PDFMetadata
    content: str
    pages: List[Dict[str, Any]]
    images: List[ExtractedImage]
    tables: List[ExtractedTable]
    formulas: List[ExtractedFormula]
    document_type: DocumentType
    language: str = "en"
    extraction_mode: ExtractionMode = ExtractionMode.BALANCED
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 2. 文档类型检测器
# ============================================================================

class DocumentTypeDetector:
    """文档类型检测器"""

    def __init__(self):
        self.patterns = {
            DocumentType.ACADEMIC_PAPER: [
                r"abstract",
                r"introduction",
                r"methodology",
                r"references",
                r"bibliography",
                r"doi:",
                r"issn:",
            ],
            DocumentType.TECHNICAL_REPORT: [
                r"technical report",
                r"white paper",
                r"specification",
                r"requirements",
                r"implementation",
            ],
            DocumentType.BOOK_CHAPTER: [
                r"chapter \d+",
                r"part \d+",
                r"section \d+",
            ],
        }

    def detect(self, content: str, metadata: PDFMetadata) -> DocumentType:
        """检测文档类型"""
        content_lower = content.lower()
        metadata_text = f"{metadata.title or ''} {metadata.subject or ''}".lower()

        scores = defaultdict(float)

        for doc_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower))
                scores[doc_type] += matches * 2

                if pattern in metadata_text:
                    scores[doc_type] += 5

        # 根据页数辅助判断
        if metadata.page_count < 5:
            scores[DocumentType.PRESENTATION] = 10

        # 返回得分最高的类型
        if not scores:
            return DocumentType.UNKNOWN

        return max(scores.items(), key=lambda x: x[1])[0]


# ============================================================================
# 3. 智能内容提取器
# ============================================================================

class SmartContentExtractor:
    """智能内容提取器"""

    def __init__(self, mode: ExtractionMode = ExtractionMode.BALANCED):
        self.mode = mode
        self.noise_patterns = [
            r"page \d+",
            r"header",
            r"footer",
            r"watermark",
        ]

    async def extract_text(self, page_data: Dict[str, Any]) -> str:
        """提取文本"""
        # 模拟文本提取
        if self.mode == ExtractionMode.FAST:
            # 快速模式：仅提取主要文本
            text = page_data.get("text", "")[:1000]
        elif self.mode == ExtractionMode.DETAILED:
            # 详细模式：提取所有文本包括注释
            text = page_data.get("text", "") + "\n" + page_data.get("annotations", "")
        else:
            # 平衡模式
            text = page_data.get("text", "")

        # 清理噪声
        for pattern in self.noise_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        return text.strip()

    async def detect_structure(self, content: str) -> Dict[str, Any]:
        """检测文档结构"""
        structure = {
            "title": None,
            "abstract": None,
            "sections": [],
            "references": [],
        }

        # 检测标题
        title_match = re.search(r"^(.+?)\n", content, re.MULTILINE)
        if title_match:
            structure["title"] = title_match.group(1).strip()

        # 检测章节
        section_pattern = r"\n(#+)\s+(.+?)\n"
        sections = re.findall(section_pattern, content)
        for level, title in sections:
            structure["sections"].append({
                "level": len(level),
                "title": title.strip(),
                "content": ""
            })

        # 检测摘要
        abstract_match = re.search(
            r"(?:abstract|summary)[:\s]+(.*?)(?:\n\n|\n[A-Z])",
            content,
            re.IGNORECASE | re.DOTALL
        )
        if abstract_match:
            structure["abstract"] = abstract_match.group(1).strip()

        # 检测参考文献
        ref_pattern = r"\n(references|bibliography)[:\s]*(.*)"
        ref_match = re.search(ref_pattern, content, re.IGNORECASE | re.DOTALL)
        if ref_match:
            structure["references"] = ref_match.group(2).strip()

        return structure


# ============================================================================
# 4. 图像处理器
# ============================================================================

class ImageProcessor:
    """图像处理器"""

    def __init__(self):
        self.supported_formats = {".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".svg"}

    async def extract_images(
        self,
        page_data: Dict[str, Any]
    ) -> List[ExtractedImage]:
        """提取图像"""
        images = []
        page_number = page_data.get("page_number", 1)

        # 模拟图像提取
        for i, img_data in enumerate(page_data.get("images", [])):
            image = ExtractedImage(
                image_id=f"img_{page_number}_{i:03d}",
                page_number=page_number,
                format=ImageFormat(img_data.get("format", "jpeg")),
                width=img_data.get("width", 800),
                height=img_data.get("height", 600),
                data=img_data.get("data", b""),
                hash=hashlib.sha256(img_data.get("data", b"")).hexdigest(),
                alt_text=img_data.get("alt_text", f"Image {i+1}")
            )
            images.append(image)

        return images

    async def optimize_image(
        self,
        image: ExtractedImage,
        max_width: int = 1200,
        quality: int = 85
    ) -> ExtractedImage:
        """优化图像"""
        # 模拟图像优化
        if image.width > max_width:
            scale = max_width / image.width
            image.width = int(image.width * scale)
            image.height = int(image.height * scale)

        # 压缩（模拟）
        original_size = len(image.data)
        image.data = image.data[:int(original_size * 0.7)]  # 模拟压缩

        return image


# ============================================================================
# 5. 表格检测器
# ============================================================================

class TableDetector:
    """表格检测器"""

    async def detect_tables(
        self,
        page_data: Dict[str, Any]
    ) -> List[ExtractedTable]:
        """检测表格"""
        tables = []
        page_number = page_data.get("page_number", 1)

        # 模拟表格检测
        for i, table_data in enumerate(page_data.get("tables", [])):
            table = ExtractedTable(
                table_id=f"table_{page_number}_{i:03d}",
                page_number=page_number,
                rows=table_data.get("rows", 0),
                columns=table_data.get("columns", 0),
                data=table_data.get("data", []),
                headers=table_data.get("headers", [])
            )
            tables.append(table)

        return tables

    async def extract_table_data(self, table_region: Dict[str, Any]) -> List[List[str]]:
        """提取表格数据"""
        # 模拟表格数据提取
        return [
            ["Header 1", "Header 2", "Header 3"],
            ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
            ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"],
        ]


# ============================================================================
# 6. 数学公式识别器
# ============================================================================

class FormulaRecognizer:
    """数学公式识别器"""

    def __init__(self):
        self.inline_pattern = r"\$(.+?)\$"
        self.display_pattern = r"\$\$(.+?)\$\$"

    async def detect_formulas(
        self,
        content: str,
        page_number: int
    ) -> List[ExtractedFormula]:
        """检测数学公式"""
        formulas = []

        # 检测行内公式
        for match in re.finditer(self.inline_pattern, content):
            formula = ExtractedFormula(
                formula_id=f"formula_inline_{len(formulas)}",
                page_number=page_number,
                latex=match.group(1).strip(),
                position={
                    "start": match.start(),
                    "end": match.end()
                }
            )
            formulas.append(formula)

        # 检测块级公式
        for match in re.finditer(self.display_pattern, content, re.DOTALL):
            formula = ExtractedFormula(
                formula_id=f"formula_display_{len(formulas)}",
                page_number=page_number,
                latex=match.group(1).strip(),
                position={
                    "start": match.start(),
                    "end": match.end()
                }
            )
            formulas.append(formula)

        return formulas


# ============================================================================
# 7. OCR处理器
# ============================================================================

class OCRProcessor:
    """OCR处理器"""

    def __init__(self):
        self.supported_languages = ["en", "zh", "es", "fr", "de", "ja", "ko"]

    async def extract_text_from_image(
        self,
        image: ExtractedImage,
        language: str = "en"
    ) -> str:
        """从图像提取文本"""
        # 模拟OCR处理
        if language not in self.supported_languages:
            language = "en"

        # 这里应该调用实际的OCR服务（如Tesseract）
        return f"OCR extracted text from image {image.image_id} (lang: {language})"

    async def detect_language(self, image: ExtractedImage) -> str:
        """检测图像中的语言"""
        # 模拟语言检测
        return "en"


# ============================================================================
# 8. 高级PDF解析器
# ============================================================================

class AdvancedPDFParser:
    """高级PDF解析器

    功能特性:
    - 多模式提取
    - 智能文档分类
    - 图像和表格处理
    - 公式识别
    - OCR支持
    - 批量处理
    - 进度监控
    """

    def __init__(
        self,
        mode: ExtractionMode = ExtractionMode.BALANCED,
        enable_ocr: bool = False,
        language: str = "en"
    ):
        self.mode = mode
        self.enable_ocr = enable_ocr
        self.language = language

        # 组件
        self.type_detector = DocumentTypeDetector()
        self.content_extractor = SmartContentExtractor(mode)
        self.image_processor = ImageProcessor()
        self.table_detector = TableDetector()
        self.formula_recognizer = FormulaRecognizer()
        self.ocr_processor = OCRProcessor()

        # 统计信息
        self.stats = {
            "documents_processed": 0,
            "pages_processed": 0,
            "images_extracted": 0,
            "tables_detected": 0,
            "formulas_recognized": 0,
            "ocr_performed": 0,
        }

    async def parse_pdf(
        self,
        pdf_path: str,
        progress_callback: Optional[Callable] = None
    ) -> ExtractionResult:
        """解析PDF文档"""
        start_time = datetime.now()

        # 模拟PDF解析
        document_id = str(uuid.uuid4())

        # 提取元数据
        metadata = await self._extract_metadata(pdf_path)

        # 处理每一页
        pages_content = []
        all_images = []
        all_tables = []
        all_formulas = []

        for page_num in range(1, metadata.page_count + 1):
            # 模拟页面数据
            page_data = await self._process_page(pdf_path, page_num)

            # 提取内容
            content = await self.content_extractor.extract_text(page_data)

            # 检测结构
            structure = await self.content_extractor.detect_structure(content)

            # 提取图像
            images = await self.image_processor.extract_images(page_data)
            all_images.extend(images)

            # 检测表格
            tables = await self.table_detector.detect_tables(page_data)
            all_tables.extend(tables)

            # 识别公式
            formulas = await self.formula_recognizer.detect_formulas(
                content,
                page_num
            )
            all_formulas.extend(formulas)

            pages_content.append({
                "page_number": page_num,
                "content": content,
                "structure": structure,
                "images_count": len(images),
                "tables_count": len(tables),
                "formulas_count": len(formulas),
            })

            # 更新进度
            if progress_callback:
                progress = page_num / metadata.page_count * 100
                progress_callback(progress)

            # 更新统计
            self.stats["pages_processed"] += 1
            self.stats["images_extracted"] += len(images)
            self.stats["tables_detected"] += len(tables)
            self.stats["formulas_recognized"] += len(formulas)

        # 合并所有内容
        full_content = "\n".join([p["content"] for p in pages_content])

        # 检测文档类型
        doc_type = self.type_detector.detect(full_content, metadata)

        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds()

        # 更新统计
        self.stats["documents_processed"] += 1

        return ExtractionResult(
            document_id=document_id,
            metadata=metadata,
            content=full_content,
            pages=pages_content,
            images=all_images,
            tables=all_tables,
            formulas=all_formulas,
            document_type=doc_type,
            language=self.language,
            extraction_mode=self.mode,
            processing_time=processing_time
        )

    async def _extract_metadata(self, pdf_path: str) -> PDFMetadata:
        """提取PDF元数据"""
        # 模拟元数据提取
        return PDFMetadata(
            filename=Path(pdf_path).name,
            file_size=1024000,
            page_count=10,
            title="Sample Document",
            author="Unknown",
            subject="Research Paper"
        )

    async def _process_page(self, pdf_path: str, page_number: int) -> Dict[str, Any]:
        """处理单个页面"""
        # 模拟页面处理
        return {
            "page_number": page_number,
            "text": f"Content of page {page_number}" * 100,
            "images": [
                {
                    "format": "jpeg",
                    "width": 800,
                    "height": 600,
                    "data": b"image_data",
                    "alt_text": f"Image on page {page_number}"
                }
            ],
            "tables": [
                {
                    "rows": 3,
                    "columns": 3,
                    "data": [["A", "B", "C"], ["1", "2", "3"], ["4", "5", "6"]],
                    "headers": ["A", "B", "C"]
                }
            ],
            "annotations": []
        }

    async def batch_parse(
        self,
        pdf_paths: List[str],
        max_concurrent: int = 3
    ) -> List[ExtractionResult]:
        """批量解析PDF"""
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def process_single(pdf_path: str) -> ExtractionResult:
            async with semaphore:
                return await self.parse_pdf(pdf_path)

        # 并发处理
        tasks = [process_single(path) for path in pdf_paths]
        results = await asyncio.gather(*tasks)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "mode": self.mode.value,
            "ocr_enabled": self.enable_ocr,
            "language": self.language,
        }


# ============================================================================
# 9. 使用示例
# ============================================================================

async def example_advanced_pdf_parsing():
    """高级PDF解析示例"""

    # 1. 创建解析器
    print("\n=== 创建PDF解析器 ===")
    parser = AdvancedPDFParser(
        mode=ExtractionMode.DETAILED,
        enable_ocr=True,
        language="en"
    )

    # 2. 解析单个PDF
    print("\n=== 解析单个PDF ===")
    pdf_path = "./sample.pdf"
    result = await parser.parse_pdf(pdf_path)

    print(f"文档ID: {result.document_id}")
    print(f"文档类型: {result.document_type.value}")
    print(f"页数: {result.metadata.page_count}")
    print(f"提取内容长度: {len(result.content)}")
    print(f"图像数量: {len(result.images)}")
    print(f"表格数量: {len(result.tables)}")
    print(f"公式数量: {len(result.formulas)}")
    print(f"处理时间: {result.processing_time:.2f}s")

    # 3. 显示页面摘要
    print("\n=== 页面摘要 ===")
    for page in result.pages[:3]:  # 只显示前3页
        print(f"\n第{page['page_number']}页:")
        print(f"  内容长度: {len(page['content'])}")
        print(f"  图像: {page['images_count']}")
        print(f"  表格: {page['tables_count']}")
        print(f"  公式: {page['formulas_count']}")
        if page["structure"]["title"]:
            print(f"  标题: {page['structure']['title']}")

    # 4. 显示图像信息
    print("\n=== 图像信息 ===")
    for img in result.images[:3]:  # 只显示前3个图像
        print(f"图像 {img.image_id}:")
        print(f"  页面: {img.page_number}")
        print(f"  尺寸: {img.width}x{img.height}")
        print(f"  格式: {img.format.value}")
        print(f"  哈希: {img.hash[:16]}...")
        if img.alt_text:
            print(f"  描述: {img.alt_text}")

    # 5. 显示表格信息
    print("\n=== 表格信息 ===")
    for table in result.tables[:3]:  # 只显示前3个表格
        print(f"表格 {table.table_id}:")
        print(f"  页面: {table.page_number}")
        print(f"  尺寸: {table.rows}x{table.columns}")
        if table.headers:
            print(f"  表头: {table.headers}")

    # 6. 显示公式信息
    print("\n=== 公式信息 ===")
    for formula in result.formulas[:3]:  # 只显示前3个公式
        print(f"公式 {formula.formula_id}:")
        print(f"  页面: {formula.page_number}")
        if formula.latex:
            print(f"  LaTeX: {formula.latex}")

    # 7. 批量解析示例
    print("\n\n=== 批量解析示例 ===")
    pdf_paths = ["./doc1.pdf", "./doc2.pdf", "./doc3.pdf"]
    batch_results = await parser.batch_parse(pdf_paths, max_concurrent=2)

    print(f"批量处理完成，共 {len(batch_results)} 个文档")

    # 8. 显示统计信息
    print("\n=== 统计信息 ===")
    stats = parser.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


# ============================================================================
# 10. 高级功能：自定义提取器
# ============================================================================

class CustomExtractor:
    """自定义提取器

    允许用户自定义提取逻辑。
    """

    def __init__(self):
        self.extractors: Dict[str, Callable] = {}

    def register(self, name: str, extractor_func: Callable):
        """注册自定义提取器"""
        self.extractors[name] = extractor_func
        logger.info(f"Registered custom extractor: {name}")

    async def extract(self, name: str, data: Any) -> Any:
        """执行自定义提取"""
        if name not in self.extractors:
            raise ValueError(f"Extractor not found: {name}")

        return await self.extractors[name](data)


# ============================================================================
# 11. 主函数
# ============================================================================

if __name__ == "__main__":
    asyncio.run(example_advanced_pdf_parsing())
