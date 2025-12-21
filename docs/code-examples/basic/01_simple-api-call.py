#!/usr/bin/env python3
"""
基础示例 01: 简单 API 调用
学习如何调用 ScholarFlow 的基本 API
"""

import asyncio
import aiohttp
import json
from pathlib import Path

# API 配置
API_BASE_URL = "http://localhost:8000/api"
TASK_ID = "example-task-001"


async def check_task_status(session: aiohttp.ClientSession, task_id: str):
    """查询任务状态"""
    url = f"{API_BASE_URL}/tasks/{task_id}"

    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ 任务状态: {data.get('status')}")
                print(f"📊 进度: {data.get('progress_percentage', 0)}%")
                return data
            else:
                print(f"❌ 查询失败: {response.status}")
                return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


async def upload_pdf(session: aiohttp.ClientSession, pdf_path: str):
    """上传 PDF 文件"""
    url = f"{API_BASE_URL}/upload"

    try:
        with open(pdf_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=Path(pdf_path).name)

            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ 上传成功: {result['filename']}")
                    print(f"📁 文件路径: {result['path']}")
                    return result
                else:
                    print(f"❌ 上传失败: {response.status}")
                    return None
    except FileNotFoundError:
        print(f"❌ 文件不存在: {pdf_path}")
        return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


async def create_task(session: aiohttp.ClientSession, pdf_path: str):
    """创建转换任务"""
    url = f"{API_BASE_URL}/tasks"

    payload = {
        "pdf_path": pdf_path,
        "presentation_style": "academic",  # academic, popular, business
        "max_chars": 6000,
        "target_chunks": 6
    }

    try:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ 任务创建成功")
                print(f"🆔 任务ID: {result['task_id']}")
                print(f"📋 状态: {result['status']}")
                return result
            else:
                print(f"❌ 创建失败: {response.status}")
                result = await response.text()
                print(f"错误信息: {result}")
                return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


async def download_result(session: aiohttp.ClientSession, task_id: str):
    """下载转换结果"""
    url = f"{API_BASE_URL}/download/{task_id}"

    try:
        async with session.get(url) as response:
            if response.status == 200:
                # 获取文件名
                content_disposition = response.headers.get('Content-Disposition', '')
                filename = "presentation.pptx"
                if 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[1].strip('"')

                # 保存文件
                output_path = Path("downloads") / filename
                output_path.parent.mkdir(exist_ok=True)

                content = await response.read()
                output_path.write_bytes(content)

                print(f"✅ 下载成功: {output_path}")
                return output_path
            else:
                print(f"❌ 下载失败: {response.status}")
                return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


async def main():
    """主函数"""
    print("=" * 60)
    print("📚 ScholarFlow API 调用示例")
    print("=" * 60)

    # 检查 API 服务器是否运行
    print("\n🔍 检查 API 服务器状态...")

    async with aiohttp.ClientSession() as session:
        # 测试连接
        try:
            async with session.get(f"{API_BASE_URL}/") as response:
                if response.status == 200:
                    print("✅ API 服务器运行正常")
                else:
                    print(f"⚠️  API 服务器响应异常: {response.status}")
        except Exception:
            print("❌ 无法连接到 API 服务器")
            print("请确保运行: uvicorn app.api.main:app --host 0.0.0.0 --port 8000")
            return

        # 示例 1: 上传 PDF
        print("\n" + "=" * 60)
        print("📤 示例 1: 上传 PDF 文件")
        print("=" * 60)

        pdf_path = "data/test-paper.pdf"
        upload_result = await upload_pdf(session, pdf_path)

        if not upload_result:
            print("⚠️  上传失败，跳过后续示例")
            return

        # 示例 2: 创建任务
        print("\n" + "=" * 60)
        print("🚀 示例 2: 创建转换任务")
        print("=" * 60)

        task_result = await create_task(session, upload_result['path'])

        if not task_result:
            print("⚠️  创建任务失败")
            return

        task_id = task_result['task_id']

        # 示例 3: 轮询任务状态
        print("\n" + "=" * 60)
        print("⏳ 示例 3: 轮询任务状态")
        print("=" * 60)

        max_attempts = 30
        attempt = 0

        while attempt < max_attempts:
            attempt += 1
            print(f"\n🔄 第 {attempt} 次查询...")

            status = await check_task_status(session, task_id)

            if status:
                progress = status.get('progress_percentage', 0)

                if progress >= 100 or status.get('status') == 'completed':
                    print("✅ 任务完成!")
                    break
                elif status.get('status') == 'failed':
                    print("❌ 任务失败")
                    error_msg = status.get('error_message', '未知错误')
                    print(f"错误信息: {error_msg}")
                    break

            # 等待 2 秒后再次查询
            await asyncio.sleep(2)

        if attempt >= max_attempts:
            print("⏰ 查询超时，请稍后手动检查")

        # 示例 4: 下载结果
        print("\n" + "=" * 60)
        print("💾 示例 4: 下载转换结果")
        print("=" * 60)

        if progress >= 100:
            result_path = await download_result(session, task_id)
            if result_path:
                print(f"\n🎉 演示文稿已保存到: {result_path}")

        print("\n" + "=" * 60)
        print("✨ 示例完成!")
        print("=" * 60)


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())


"""
💡 学习要点:

1. API 基础调用
   - 使用 aiohttp 进行异步 HTTP 请求
   - 处理文件上传 (multipart/form-data)
   - 处理 JSON 请求和响应

2. 任务状态轮询
   - 定期查询任务状态
   - 根据进度判断是否完成
   - 处理异步任务

3. 错误处理
   - 检查 HTTP 状态码
   - 捕获和处理异常
   - 提供用户友好的错误信息

4. 文件操作
   - 下载二进制文件
   - 保存到本地文件系统
   - 从 Content-Disposition 提取文件名

📝 扩展练习:

1. 添加命令行参数支持
2. 实现进度条显示
3. 支持批量上传多个 PDF
4. 添加重试机制
5. 实现断点续传

🔗 相关文档:

- FastAPI 文档: https://fastapi.tiangolo.com/
- aiohttp 文档: https://docs.aiohttp.org/
- ScholarFlow API: 见第14章
"""
