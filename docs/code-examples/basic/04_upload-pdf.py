#!/usr/bin/env python3
"""
基础示例 04: 文件上传
学习如何上传 PDF 文件到 ScholarFlow
"""

import os
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, List
import aiofiles


async def upload_single_pdf(session: aiohttp.ClientSession, pdf_path: str, api_url: str = "http://localhost:8000") -> Optional[dict]:
    """
    上传单个 PDF 文件

    Args:
        session: aiohttp 会话
        pdf_path: PDF 文件路径
        api_url: API 基础 URL

    Returns:
        上传结果或 None
    """
    url = f"{api_url}/api/upload"

    # 验证文件存在
    if not Path(pdf_path).exists():
        print(f"❌ 文件不存在: {pdf_path}")
        return None

    # 检查文件大小
    file_size = Path(pdf_path).stat().st_size
    max_size = 100 * 1024 * 1024  # 100MB

    if file_size > max_size:
        print(f"❌ 文件过大: {file_size / 1024 / 1024:.2f}MB (最大 {max_size / 1024 / 1024}MB)")
        return None

    try:
        print(f"📤 正在上传: {pdf_path}")
        print(f"  文件大小: {file_size / 1024:.2f}KB")

        # 准备文件数据
        with open(pdf_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=Path(pdf_path).name, content_type='application/pdf')

            # 发送请求
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ 上传成功!")
                    print(f"  文件名: {result.get('filename')}")
                    print(f"  路径: {result.get('path')}")
                    print(f"  大小: {result.get('size', 0) / 1024:.2f}KB")
                    return result
                else:
                    print(f"❌ 上传失败: HTTP {response.status}")
                    error_text = await response.text()
                    print(f"  错误: {error_text}")
                    return None

    except Exception as e:
        print(f"❌ 上传异常: {e}")
        return None


async def upload_multiple_pdfs(session: aiohttp.ClientSession, pdf_paths: List[str], api_url: str = "http://localhost:8000") -> List[dict]:
    """
    批量上传多个 PDF 文件

    Args:
        session: aiohttp 会话
        pdf_paths: PDF 文件路径列表
        api_url: API 基础 URL

    Returns:
        上传结果列表
    """
    print(f"\n🚀 开始批量上传 {len(pdf_paths)} 个文件...")

    results = []
    for i, pdf_path in enumerate(pdf_paths, 1):
        print(f"\n{'=' * 60}")
        print(f"📄 文件 {i}/{len(pdf_paths)}")
        print(f"{'=' * 60}")

        result = await upload_single_pdf(session, pdf_path, api_url)
        if result:
            results.append(result)

    print(f"\n🎉 批量上传完成: {len(results)}/{len(pdf_paths)} 成功")
    return results


async def upload_with_progress(session: aiohttp.ClientSession, pdf_path: str, api_url: str = "http://localhost:8000"):
    """
    带进度的文件上传

    Args:
        session: aiohttp 会话
        pdf_path: PDF 文件路径
        api_url: API 基础 URL
    """
    url = f"{api_url}/api/upload"

    file_path = Path(pdf_path)
    if not file_path.exists():
        print(f"❌ 文件不存在: {pdf_path}")
        return

    # 读取文件
    file_size = file_path.stat().st_size

    async def file_reader():
        """异步文件读取器"""
        async with aiofiles.open(pdf_path, 'rb') as f:
            chunk_size = 1024 * 1024  # 1MB
            uploaded = 0

            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break

                uploaded += len(chunk)
                progress = (uploaded / file_size) * 100
                print(f"\r  进度: {progress:.1f}% ({uploaded}/{file_size} bytes)", end='', flush=True)

                yield chunk

    try:
        print(f"📤 正在上传: {pdf_path}")
        print(f"  文件大小: {file_size / 1024 / 1024:.2f}MB")

        data = aiohttp.FormData()
        data.add_field('file', file_reader(), filename=file_path.name, content_type='application/pdf')

        async with session.post(url, data=data) as response:
            if response.status == 200:
                result = await response.json()
                print(f"\n✅ 上传成功!")
                return result
            else:
                print(f"\n❌ 上传失败: HTTP {response.status}")
                return None

    except Exception as e:
        print(f"\n❌ 上传异常: {e}")
        return None


def find_pdf_files(directory: str) -> List[str]:
    """
    查找目录下的所有 PDF 文件

    Args:
        directory: 目录路径

    Returns:
        PDF 文件路径列表
    """
    pdf_dir = Path(directory)
    if not pdf_dir.exists():
        print(f"⚠️  目录不存在: {directory}")
        return []

    # 递归查找 PDF 文件
    pdf_files = list(pdf_dir.rglob("*.pdf"))

    print(f"\n🔍 在 {directory} 中找到 {len(pdf_files)} 个 PDF 文件:")
    for pdf_file in pdf_files[:10]:  # 只显示前10个
        size = pdf_file.stat().st_size / 1024 / 1024
        print(f"  - {pdf_file.name} ({size:.2f}MB)")

    if len(pdf_files) > 10:
        print(f"  ... 还有 {len(pdf_files) - 10} 个文件")

    return [str(pdf_file) for pdf_file in pdf_files]


async def check_api_status(session: aiohttp.ClientSession, api_url: str = "http://localhost:8000"):
    """检查 API 服务器状态"""
    try:
        # 尝试访问根路径
        async with session.get(f"{api_url}/") as response:
            if response.status == 200:
                print("✅ API 服务器运行正常")
                return True
            else:
                print(f"⚠️  API 服务器响应异常: {response.status}")
                return False
    except Exception:
        print("❌ 无法连接到 API 服务器")
        print(f"请确保运行: uvicorn app.api.main:app --host 0.0.0.0 --port 8000")
        return False


async def main():
    """主函数"""
    print("=" * 60)
    print("📤 ScholarFlow 文件上传示例")
    print("=" * 60)

    api_url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        # 检查 API 状态
        print("\n🔍 检查 API 服务器状态...")
        api_ok = await check_api_status(session, api_url)

        if not api_ok:
            print("\n❌ API 服务器不可用，请先启动服务器")
            return

        # 示例 1: 单文件上传
        print("\n" + "=" * 60)
        print("📋 示例 1: 单文件上传")
        print("=" * 60)

        pdf_path = "data/sample-paper.pdf"
        result = await upload_single_pdf(session, pdf_path, api_url)

        if result:
            print(f"\n✅ 示例 1 完成")

        # 示例 2: 带进度的上传
        print("\n" + "=" * 60)
        print("📋 示例 2: 带进度的上传")
        print("=" * 60)

        pdf_path2 = "data/large-paper.pdf"
        result2 = await upload_with_progress(session, pdf_path2, api_url)

        if result2:
            print(f"\n✅ 示例 2 完成")

        # 示例 3: 批量上传
        print("\n" + "=" * 60)
        print("📋 示例 3: 批量上传")
        print("=" * 60)

        # 查找 PDF 文件
        pdf_dir = "data/pdfs"
        pdf_files = find_pdf_files(pdf_dir)

        if pdf_files:
            # 限制上传数量（避免过多请求）
            pdf_files = pdf_files[:3]
            results = await upload_multiple_pdfs(session, pdf_files, api_url)

            print(f"\n📊 批量上传结果:")
            print(f"  成功: {len(results)}")
            print(f"  失败: {len(pdf_files) - len(results)}")
        else:
            print(f"\n⚠️  没有找到 PDF 文件")

        # 示例 4: 上传验证
        print("\n" + "=" * 60)
        print("📋 示例 4: 上传验证")
        print("=" * 60)

        test_cases = [
            ("data/exists.pdf", True),  # 存在的文件
            ("data/not-exists.pdf", False),  # 不存在的文件
            ("data/empty.pdf", False),  # 空文件
            ("data/wrong-format.txt", False),  # 错误格式
        ]

        for pdf_path, should_succeed in test_cases:
            print(f"\n🧪 测试: {pdf_path}")
            result = await upload_single_pdf(session, pdf_path, api_url)

            if should_succeed and result:
                print("  ✅ 按预期成功")
            elif not should_succeed and not result:
                print("  ✅ 按预期失败")
            else:
                print("  ⚠️  结果不符合预期")

    print("\n" + "=" * 60)
    print("✨ 文件上传示例完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


"""
💡 学习要点:

1. 文件上传基础
   - 使用 aiohttp.FormData
   - 设置正确的 Content-Type
   - 处理文件二进制数据

2. 错误处理
   - 文件存在性检查
   - 文件大小限制
   - 网络异常处理
   - HTTP 状态码检查

3. 进度显示
   - 异步文件读取
   - 进度计算
   - 实时显示进度

4. 批量操作
   - 并发上传
   - 结果聚合
   - 错误隔离

📝 扩展练习:

1. 添加断点续传
2. 实现文件校验（MD5）
3. 添加压缩上传
4. 实现上传队列
5. 添加重试机制

🔗 相关文档:

- aiohttp: https://docs.aiohttp.org/
- 文件上传最佳实践: https://swagger.io/docs/specification/describing-request-body/file-upload/
"""
