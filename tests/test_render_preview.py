#!/usr/bin/env python
"""测试 render_preview API 端点"""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """创建测试客户端"""
    app = create_app()
    return TestClient(app)


def test_render_preview_basic(client: TestClient):
    """测试基本的 render_preview 功能"""
    test_markdown = """# 测试幻灯片

## 第一页

这是一个测试幻灯片。

- 列表项 1
- 列表项 2
- 列表项 3

**粗体文字**

---

## 第二页

第二页内容。
"""

    print("\n🧪 测试 render_preview 端点...")
    print(f"📝 发送的 Markdown 长度: {len(test_markdown)} 字符")

    response = client.post(
        "/api/render/preview",
        json={"markdown": test_markdown}
    )

    print(f"✅ 状态码: {response.status_code}")

    assert response.status_code == 200, f"期望状态码 200，得到 {response.status_code}"

    result = response.json()
    assert "html" in result, "响应中应包含 'html' 字段"

    html_content = result["html"]
    print(f"✅ 返回 HTML 长度: {len(html_content)} 字符")

    # 检查 HTML 是否包含 Marp 特定标记
    assert "marp" in html_content.lower(), "HTML 应包含 Marp 标记"

    # 检查是否包含基本结构
    assert "<!DOCTYPE html>" in html_content or "<html>" in html_content, "HTML 应包含基本结构"

    # 检查是否包含 Marp slide 标记
    assert "marp-slide" in html_content or "marp__slide" in html_content, "HTML 应包含 Marp slide 标记"

    print("✅ 所有断言通过!")

    # 可选：保存 HTML 到文件用于手动检查（仅在本地测试时）
    # import os
    # if os.getenv("CI") != "true":
    #     from pathlib import Path
    #     output_path = Path("/tmp/test_preview_output.html")
    #     with open(output_path, 'w', encoding='utf-8') as f:
    #         f.write(html_content)
    #     print(f"📄 HTML 已保存到: {output_path}")


def test_render_preview_empty_markdown(client: TestClient):
    """测试空 Markdown"""
    response = client.post(
        "/api/render/preview",
        json={"markdown": ""}
    )

    assert response.status_code == 200
    result = response.json()
    assert "html" in result
    assert len(result["html"]) > 0


def test_render_preview_complex_markdown(client: TestClient):
    """测试复杂的 Markdown 包含代码块和表格"""
    test_markdown = """# 复杂测试

## 代码示例

```python
def hello():
    print("Hello, World!")
```

## 表格

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| A   | B   | C   |

## 公式

E = mc²

---

## 图片

![测试图片](test.png)
"""

    response = client.post(
        "/api/render/preview",
        json={"markdown": test_markdown}
    )

    assert response.status_code == 200
    result = response.json()
    assert "html" in result
    assert len(result["html"]) > 0
