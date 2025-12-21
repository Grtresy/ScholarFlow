#!/usr/bin/env python3
"""
基础示例 03: 基础工作流运行
学习如何直接调用 LangGraph 工作流
"""

import asyncio
from pathlib import Path
from typing import TypedDict, List

# 假设我们从实际项目中导入
# from app.graph.workflow import create_workflow
# from app.graph.state import WorkflowState, create_initial_state


# 示例 1: 模拟 WorkflowState
class WorkflowState(TypedDict, total=False):
    """工作流状态"""
    task_id: str
    status: str
    pdf_path: str
    presentation_style: str
    markdown_text: str
    chunks: List[str]
    merged_outline: str
    marp_markdown: str
    output_path: str
    progress_percentage: int


def create_initial_state(task_id: str, pdf_path: str, presentation_style: str = "academic") -> WorkflowState:
    """创建初始状态"""
    return {
        "task_id": task_id,
        "status": "pending",
        "pdf_path": pdf_path,
        "presentation_style": presentation_style,
        "max_chars": 6000,
        "target_chunks": 6,
        "progress_percentage": 0,
    }


# 示例 2: 模拟工作流节点
def node_initialize(state: WorkflowState) -> WorkflowState:
    """初始化节点"""
    print(f"\n🔧 初始化任务: {state['task_id']}")
    print(f"  PDF 文件: {state['pdf_path']}")
    print(f"  演示风格: {state['presentation_style']}")

    # 验证 PDF 文件
    pdf_path = Path(state['pdf_path'])
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

    return {
        "status": "initialized",
        "progress_percentage": 10,
    }


def node_parse_pdf(state: WorkflowState) -> WorkflowState:
    """PDF 解析节点"""
    print(f"\n📄 解析 PDF 文件...")
    print(f"  正在处理: {state['pdf_path']}")

    # 模拟 PDF 解析
    # 实际实现会调用 MinerU API
    mock_markdown = """
# 示例论文

## 摘要
这是一篇示例论文的摘要。

## 引言
介绍了研究背景和意义。

## 方法
描述了研究方法。

## 结果
展示了实验结果。

## 结论
总结了研究结论。
"""

    return {
        "status": "pdf_parsed",
        "markdown_text": mock_markdown,
        "progress_percentage": 25,
    }


def node_split_markdown(state: WorkflowState) -> WorkflowState:
    """文本分块节点"""
    print(f"\n✂️  文本分块...")

    markdown = state.get('markdown_text', '')
    # 简单按标题分块
    chunks = [
        "### 摘要\n这是一篇示例论文的摘要。",
        "### 引言\n介绍了研究背景和意义。",
        "### 方法\n描述了研究方法。",
        "### 结果\n展示了实验结果。",
        "### 结论\n总结了研究结论。",
    ]

    print(f"  文本已分块为 {len(chunks)} 个片段")

    return {
        "status": "text_split",
        "chunks": chunks,
        "chunks_count": len(chunks),
        "progress_percentage": 40,
    }


def node_stage1_process(state: WorkflowState) -> WorkflowState:
    """Stage 1 处理节点"""
    print(f"\n🧠 Stage 1: 生成大纲...")

    chunks = state.get('chunks', [])
    style = state.get('presentation_style', 'academic')

    # 模拟为每个 chunk 生成大纲
    results = []
    for i, chunk in enumerate(chunks, 1):
        print(f"  处理第 {i}/{len(chunks)} 个片段")
        # 实际实现会调用 LLM API

        # 模拟 LLM 输出
        outline = f"""
## 幻灯片 {i}
- 要点 1
- 要点 2
- 要点 3
"""
        results.append({
            "chunk_index": i - 1,
            "outline": outline,
        })

    print(f"  ✅ 已生成 {len(results)} 个大纲片段")

    return {
        "status": "stage1_completed",
        "stage1_results": results,
        "progress_percentage": 65,
    }


def node_merge_outlines(state: WorkflowState) -> WorkflowState:
    """合并大纲节点"""
    print(f"\n🔗 合并大纲片段...")

    results = state.get('stage1_results', [])
    style = state.get('presentation_style', 'academic')

    # 合并所有大纲
    merged = "# 演示大纲\n\n"
    for result in results:
        merged += result['outline'] + "\n\n"

    print(f"  ✅ 大纲已合并，总长度: {len(merged)} 字符")

    return {
        "status": "outlines_merged",
        "merged_outline": merged,
        "progress_percentage": 75,
    }


def node_stage2_process(state: WorkflowState) -> WorkflowState:
    """Stage 2 处理节点"""
    print(f"\n🎨 Stage 2: 转换为 Marp 格式...")

    outline = state.get('merged_outline', '')
    style = state.get('presentation_style', 'academic')

    # 转换为 Marp Markdown
    marp_md = f"""---
marp: true
theme: {style}
---

# 学术论文演示

{outline}
"""

    print(f"  ✅ 已转换为 Marp 格式")

    return {
        "status": "stage2_completed",
        "marp_markdown": marp_md,
        "progress_percentage": 90,
    }


def node_render(state: WorkflowState) -> WorkflowState:
    """渲染节点"""
    print(f"\n🎬 渲染演示文稿...")

    marp_md = state.get('marp_markdown', '')
    task_id = state.get('task_id', 'unknown')

    # 保存 Marp Markdown
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    md_path = output_dir / f"{task_id}.md"
    md_path.write_text(marp_md, encoding='utf-8')

    print(f"  ✅ Marp Markdown 已保存: {md_path}")

    # 实际实现会调用 Marp CLI 渲染
    # output_path = render_marp(md_path, 'pptx')

    return {
        "status": "completed",
        "output_path": str(md_path),
        "progress_percentage": 100,
    }


# 示例 3: 简单工作流执行器
async def run_simple_workflow(initial_state: WorkflowState) -> WorkflowState:
    """运行简单工作流"""
    print("=" * 60)
    print("🚀 开始执行工作流")
    print("=" * 60)

    # 复制初始状态
    state = initial_state.copy()
    current_node = "initialize"

    # 工作流节点映射
    nodes = {
        "initialize": node_initialize,
        "parse_pdf": node_parse_pdf,
        "split_markdown": node_split_markdown,
        "stage1_process": node_stage1_process,
        "merge_outlines": node_merge_outlines,
        "stage2_process": node_stage2_process,
        "render": node_render,
    }

    # 顺序执行节点
    node_sequence = [
        "initialize",
        "parse_pdf",
        "split_markdown",
        "stage1_process",
        "merge_outlines",
        "stage2_process",
        "render",
    ]

    try:
        for node_name in node_sequence:
            print(f"\n{'=' * 60}")
            print(f"📍 当前节点: {node_name}")
            print(f"{'=' * 60}")

            # 执行节点
            node_func = nodes[node_name]
            updated_state = node_func(state)

            # 更新状态
            state.update(updated_state)

            # 检查是否完成
            if state.get('status') == 'completed':
                print(f"\n✅ 工作流执行完成!")
                break

    except Exception as e:
        print(f"\n❌ 工作流执行失败: {e}")
        state['status'] = 'failed'
        state['error'] = str(e)

    return state


# 示例 4: 带错误处理的工作流
async def run_workflow_with_error_handling(initial_state: WorkflowState) -> WorkflowState:
    """运行带错误处理的工作流"""
    try:
        return await run_simple_workflow(initial_state)
    except Exception as e:
        print(f"\n💥 未处理的异常: {e}")
        initial_state['status'] = 'failed'
        initial_state['error'] = str(e)
        return initial_state


# 示例 5: 异步工作流
async def async_node_stage1(state: WorkflowState) -> WorkflowState:
    """异步 Stage 1 处理"""
    print(f"\n🧠 异步 Stage 1 处理...")

    chunks = state.get('chunks', [])

    # 模拟异步 LLM 调用
    async def process_chunk(chunk):
        await asyncio.sleep(0.5)  # 模拟网络请求
        return f"处理结果: {chunk[:20]}..."

    # 并行处理所有 chunks
    tasks = [process_chunk(chunk) for chunk in chunks]
    results = await asyncio.gather(*tasks)

    print(f"  ✅ 并行处理完成")

    return {
        "status": "stage1_completed",
        "stage1_results": [{"index": i, "result": r} for i, r in enumerate(results)],
    }


async def run_async_workflow(initial_state: WorkflowState) -> WorkflowState:
    """运行异步工作流"""
    # 初始化和解析
    state = node_initialize(initial_state)
    state = node_parse_pdf(state)
    state = node_split_markdown(state)

    # 异步 Stage 1
    state = await async_node_stage1(state)

    # 继续后续步骤
    state = node_merge_outlines(state)
    state = node_stage2_process(state)
    state = node_render(state)

    return state


def main():
    """主函数"""
    print("=" * 60)
    print("🔄 ScholarFlow 工作流运行示例")
    print("=" * 60)

    # 示例 1: 基本工作流
    print("\n" + "=" * 60)
    print("📋 示例 1: 基本工作流")
    print("=" * 60)

    initial_state = create_initial_state(
        task_id="demo-001",
        pdf_path="data/sample-paper.pdf",
        presentation_style="academic"
    )

    final_state = asyncio.run(run_simple_workflow(initial_state))

    print(f"\n📊 最终状态:")
    print(f"  状态: {final_state.get('status')}")
    print(f"  进度: {final_state.get('progress_percentage', 0)}%")
    print(f"  输出: {final_state.get('output_path', 'N/A')}")

    # 示例 2: 异步工作流
    print("\n" + "=" * 60)
    print("📋 示例 2: 异步工作流")
    print("=" * 60)

    initial_state = create_initial_state(
        task_id="demo-async-001",
        pdf_path="data/sample-paper.pdf",
        presentation_style="popular"
    )

    final_state = asyncio.run(run_async_workflow(initial_state))

    print(f"\n📊 异步工作流结果:")
    print(f"  状态: {final_state.get('status')}")
    print(f"  进度: {final_state.get('progress_percentage', 0)}%")

    print("\n" + "=" * 60)
    print("✨ 工作流示例完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()


"""
💡 学习要点:

1. 工作流状态管理
   - 使用 TypedDict 定义状态结构
   - 状态在节点间传递
   - 节点返回状态更新

2. 节点设计模式
   - 单一职责原则
   - 输入状态 -> 输出状态
   - 错误处理机制

3. 工作流执行
   - 顺序执行节点
   - 状态更新和传递
   - 进度跟踪

4. 异步处理
   - 使用 asyncio 实现异步节点
   - 并行处理提高性能
   - await 等待异步操作

📝 扩展练习:

1. 添加条件分支
2. 实现循环处理
3. 添加检查点保存
4. 实现错误重试
5. 添加并行处理

🔗 相关文档:

- LangGraph: https://langchain-ai.github.io/langgraph/
- Python asyncio: https://docs.python.org/3/library/asyncio.html
"""
