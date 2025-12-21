# 第5章 LangGraph工作流设计

## 5.1 工作流概述

### 5.1.1 什么是LangGraph工作流

LangGraph是LangChain生态系统中的工作流编排框架，专门用于构建复杂的有状态多智能体应用。ScholarFlow采用LangGraph作为核心工作流引擎，将PDF到演示文稿的转换过程建模为一个10阶段的状态驱动工作流。

**核心理念**:
- **状态驱动**: 工作流的执行完全由状态控制
- **节点编排**: 10个独立的处理节点，职责单一
- **条件路由**: 动态决定下一步执行路径
- **状态持久化**: 自动保存和恢复工作流状态
- **中断恢复**: 支持在任意节点暂停和恢复

### 5.1.2 工作流特性

| 特性 | 说明 | 价值 |
|------|------|------|
| **状态管理** | 使用TypedDict定义清晰的状态模型 | 类型安全、易维护 |
| **节点化设计** | 每个节点职责单一，可独立测试 | 模块化、低耦合 |
| **条件边** | 基于状态动态决定路由 | 灵活性、适应性 |
| **循环支持** | Stage1并行处理使用循环 | 性能优化 |
| **检查点** | 自动状态持久化 | 可靠性、可恢复 |
| **错误处理** | 内置错误恢复机制 | 健壮性 |

## 5.2 工作流架构

### 5.2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                     │
├─────────────────────────────────────────────────────────────┤
│  WorkflowState (30+ fields)                                │
│  ├── 任务信息: task_id, status, created_at                  │
│  ├── 输入数据: pdf_path, presentation_style                 │
│  ├── 处理结果: chunks, stage1_results, merged_outline       │
│  ├── 审核信息: needs_human_review, human_feedback           │
│  └── 输出结果: marp_markdown, output_path                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   10个处理节点                              │
├─────────────────────────────────────────────────────────────┤
│ 1.initialize → 2.parse_pdf → 3.split_markdown              │
│ ↓                                                          │
│ 4.stage1_process (循环) → 5.merge_outlines                 │
│ ↓                                                          │
│ 6.human_review → 7.process_feedback                        │
│ ↓                                                          │
│ 8.stage2_process → 9.render                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   条件边与路由                              │
├─────────────────────────────────────────────────────────────┤
│ • Stage1循环: 继续处理 OR 合并大纲                         │
│ • 合并后路由: 人工审核 OR 直接Stage2                       │
│ • 反馈后路由: 重新生成 OR 继续处理                         │
│ • 错误处理: 重试 OR 结束                                   │
└─────────────────────────────────────────────────────────────┘
```

### 5.2.2 节点分类

**初始化节点**:
- `initialize`: 验证输入，创建初始状态

**处理节点**:
- `parse_pdf`: PDF解析，提取内容
- `split_markdown`: 文本分块
- `stage1_process`: 生成大纲
- `merge_outlines`: 合并大纲
- `stage2_process`: 转换为Marp格式
- `render`: 渲染演示文稿

**交互节点**:
- `human_review`: 人工审核暂停点

**控制节点**:
- `process_feedback`: 处理反馈
- `handle_error`: 错误处理

## 5.3 节点详细设计

### 5.3.1 initialize节点

**文件位置**: `app/graph/nodes/initialization.py`

**职责**: 验证输入并创建初始状态

**输入状态**:
```python
{
    "task_id": "user_provided",
    "pdf_path": "user_provided",
    "presentation_style": "user_provided",
    "max_chars": 6000,
    "target_chunks": 6
}
```

**处理逻辑**:
```python
def node_initialize(state: WorkflowState) -> WorkflowState:
    """初始化节点"""
    # 1. 验证PDF文件存在
    if not Path(state["pdf_path"]).exists():
        raise FileNotFoundError(f"PDF文件不存在: {state['pdf_path']}")

    # 2. 创建初始状态
    initial_state = {
        "status": "initialized",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "retry_count": 0,
        "max_retries": 3,
        "progress_percentage": 10,
        "execution_log": []
    }

    # 3. 合并到输入状态
    state.update(initial_state)

    return state
```

**输出状态**:
```python
{
    "status": "initialized",
    "progress_percentage": 10,
    "created_at": "2025-01-01T10:00:00",
    "retry_count": 0,
    "execution_log": [{"node": "initialize", "status": "completed"}]
}
```

### 5.3.2 parse_pdf节点

**文件位置**: `app/graph/nodes/pdf_parsing.py`

**职责**: 使用MinerU解析PDF，提取Markdown和图片

**处理逻辑**:
```python
async def node_parse_pdf(state: WorkflowState) -> WorkflowState:
    """PDF解析节点"""
    # 1. 调用MinerU客户端
    mineru_client = MinerUClient()

    # 2. 解析PDF
    result = await mineru_client.parse_pdf(state["pdf_path"])

    # 3. 获取Markdown和图片
    markdown_text = result["markdown"]
    image_paths = result["images"]

    # 4. Token化图片引用
    image_manager = ImageManager(Path("data/intermediate"))
    tokenized_text, image_token_map = image_manager.tokenize_image_references_enhanced(
        markdown_content=markdown_text,
        task_id=state["task_id"]
    )

    # 5. 更新状态
    return {
        "status": "pdf_parsed",
        "markdown_text": markdown_text,
        "image_paths": image_paths,
        "tokenized_text": tokenized_text,
        "image_token_map": image_token_map,
        "token_count": len(image_token_map),
        "progress_percentage": 25
    }
```

**关键特性**:
- ✅ 异步处理
- ✅ 图片Token化保护
- ✅ 错误处理和重试
- ✅ 进度跟踪

### 5.3.3 split_markdown节点

**文件位置**: `app/graph/nodes/text_splitting.py`

**职责**: 将Markdown文本分割为可处理的块

**处理逻辑**:
```python
def node_split_markdown(state: WorkflowState) -> WorkflowState:
    """文本分块节点"""
    # 1. 获取Token化后的文本
    tokenized_text = state["tokenized_text"]

    # 2. 使用分块器
    from app.services.llm.split import split_markdown, merge_chunks

    # 3. 按max_chars分块
    chunks = split_markdown(tokenized_text, max_chars=state["max_chars"])

    # 4. 合并到目标数量
    if state["target_chunks"] > 0:
        chunks = merge_chunks(chunks, target_count=state["target_chunks"])

    # 5. 更新状态
    return {
        "status": "text_split",
        "chunks": chunks,
        "chunks_count": len(chunks),
        "progress_percentage": 40
    }
```

**分块策略**:
- 按Markdown标题(#, ##)拆分章节
- 大章节按段落二次拆分
- 控制每块长度（max_chars）
- 合并短块以达到目标数量

### 5.3.4 stage1_process节点

**文件位置**: `app/graph/nodes/stage1_processing.py`

**职责**: 为每个文本块生成幻灯片大纲

**处理逻辑**:
```python
async def node_stage1_process(state: WorkflowState) -> WorkflowState:
    """Stage1处理节点"""
    # 1. 获取当前处理的chunk索引
    current_index = state.get("current_chunk_index", 0)
    chunks = state["chunks"]

    # 2. 处理当前chunk
    chunk = chunks[current_index]

    # 3. 调用LLM生成大纲
    llm_client = LLMClient()
    prompt_template = get_stage1_prompt(state["presentation_style"])

    outline = await llm_client.generate_outline(
        content=chunk,
        style=state["presentation_style"],
        prompt_template=prompt_template
    )

    # 4. 累积结果
    stage1_results = state.get("stage1_results", [])
    stage1_results.append({
        "chunk_index": current_index,
        "outline": outline
    })

    # 5. 更新状态（推进索引）
    return {
        "current_chunk_index": current_index + 1,
        "stage1_results": stage1_results,
        "status": "stage1_processing"
    }
```

**并行处理**:
```python
# 在workflow.py中定义循环边
workflow.add_conditional_edges(
    "stage1_process",
    route_after_stage1,
    {
        "continue": "stage1_process",  # 循环
        "merge": "merge_outlines"      # 退出
    }
)

def route_after_stage1(state):
    if state["current_chunk_index"] < state["chunks_count"]:
        return "continue"
    else:
        return "merge"
```

### 5.3.5 merge_outlines节点

**文件位置**: `app/graph/nodes/outline_merging.py`

**职责**: 合并所有chunk的大纲为统一结构

**处理逻辑**:
```python
def node_merge_outlines(state: WorkflowState) -> WorkflowState:
    """合并大纲节点"""
    # 1. 获取所有stage1结果
    stage1_results = state["stage1_results"]

    # 2. 按chunk_index排序
    sorted_results = sorted(stage1_results, key=lambda x: x["chunk_index"])

    # 3. 合并大纲
    from app.services.llm.merge import merge_outlines

    merged_outline = merge_outlines(sorted_results)

    # 4. 判断是否需要人工审核
    needs_review = len(sorted_results) > 3 or state.get("enable_human_review", True)

    return {
        "status": "outlines_merged",
        "merged_outline": merged_outline,
        "needs_human_review": needs_review,
        "progress_percentage": 75
    }
```

**合并策略**:
- 按顺序合并所有大纲
- 去除重复内容
- 优化结构层次
- 统一格式风格

### 5.3.6 human_review节点

**文件位置**: `app/graph/nodes/human_review.py`

**职责**: 暂停工作流，等待人工审核

**处理逻辑**:
```python
def node_human_review(state: WorkflowState) -> WorkflowState:
    """人工审核节点"""
    # 1. 设置审核标志
    # 2. 中断工作流（通过interrupt_before配置）
    # 3. 保存检查点
    # 4. 等待外部resume调用

    return {
        "status": "human_review",
        "needs_human_review": True,
        "progress_percentage": 70
    }
```

**中断机制**:
```python
# 在workflow.py中配置中断点
def compile_workflow():
    return workflow.compile(
        checkpointer=checkpointer.saver,
        interrupt_before=["process_feedback"]  # 在process_feedback前中断
    )
```

### 5.3.7 process_feedback节点

**文件位置**: `app/graph/nodes/human_review.py`

**职责**: 处理人工反馈，决定后续路由

**处理逻辑**:
```python
def node_process_feedback(state: WorkflowState) -> WorkflowState:
    """处理反馈节点"""
    # 1. 解析人工反馈
    feedback = state.get("human_feedback", {})

    # 2. 提取决策
    approved = feedback.get("approved", False)
    action = feedback.get("action", "continue")

    # 3. 更新状态
    return {
        "approved": approved,
        "feedback_action": action,
        "status": "feedback_processed",
        "progress_percentage": 75
    }
```

**路由决策**:
```python
def route_after_feedback(state):
    if state.get("approved"):
        return "stage2"
    elif state.get("feedback_action") == "regenerate":
        return "stage1"
    else:
        return "end"
```

### 5.3.8 stage2_process节点

**文件位置**: `app/graph/nodes/stage2_processing.py`

**职责**: 将大纲转换为Marp Markdown格式

**处理逻辑**:
```python
async def node_stage2_process(state: WorkflowState) -> WorkflowState:
    """Stage2处理节点"""
    # 1. 获取合并后的大纲
    merged_outline = state["merged_outline"]

    # 2. 调用LLM转换为Marp格式
    llm_client = LLMClient()
    prompt_template = get_stage2_prompt(state["presentation_style"])

    marp_markdown = await llm_client.convert_to_marp(
        outline=merged_outline,
        style=state["presentation_style"],
        prompt_template=prompt_template
    )

    # 3. 恢复图片token
    image_manager = ImageManager(Path("data/intermediate"))
    final_markdown = image_manager.restore_tokens_to_markdown_enhanced(
        tokenized_content=marp_markdown,
        token_map=state["image_token_map"],
        output_format="marp"
    )

    return {
        "status": "stage2_completed",
        "marp_markdown": final_markdown,
        "progress_percentage": 90
    }
```

### 5.3.9 render节点

**文件位置**: `app/graph/nodes/rendering.py`

**职责**: 使用Marp CLI渲染最终演示文稿

**处理逻辑**:
```python
async def node_render(state: WorkflowState) -> WorkflowState:
    """渲染节点"""
    # 1. 保存Marp Markdown
    task_id = state["task_id"]
    output_dir = Path(f"data/workflows/output/{task_id}")
    output_dir.mkdir(parents=True, exist_ok=True)

    md_path = output_dir / "presentation.md"
    md_path.write_text(state["marp_markdown"], encoding='utf-8')

    # 2. 调用Marp渲染
    marp_engine = MarpEngine()
    output_path = await marp_engine.render(
        markdown_path=str(md_path),
        output_format="pptx",
        output_dir=str(output_dir)
    )

    return {
        "status": "completed",
        "output_path": output_path,
        "output_format": "pptx",
        "progress_percentage": 100
    }
```

### 5.3.10 handle_error节点

**文件位置**: `app/graph/nodes/error_handling.py`

**职责**: 错误恢复和重试机制

**处理逻辑**:
```python
def node_handle_error(state: WorkflowState) -> WorkflowState:
    """错误处理节点"""
    # 1. 增加重试次数
    retry_count = state.get("retry_count", 0) + 1

    # 2. 检查是否超过最大重试
    if retry_count >= state.get("max_retries", 3):
        return {
            "status": "failed",
            "error_message": "超过最大重试次数",
            "retry_count": retry_count
        }

    # 3. 重置到解析阶段
    return {
        "status": "parsing",  # 重置到parse_pdf
        "retry_count": retry_count,
        "progress_percentage": 10  # 重置进度
    }
```

## 5.4 条件路由

### 5.4.1 路由类型

**简单边**:
```python
workflow.add_edge("initialize", "parse_pdf")
workflow.add_edge("parse_pdf", "split_markdown")
```

**条件边**:
```python
workflow.add_conditional_edges(
    "stage1_process",
    route_after_stage1,
    {
        "continue": "stage1_process",
        "merge": "merge_outlines"
    }
)
```

### 5.4.2 路由函数

**路由1: Stage1循环**
```python
def route_after_stage1(state: WorkflowState) -> str:
    current_index = state.get("current_chunk_index", 0)
    total_chunks = state.get("chunks_count", 0)

    if current_index < total_chunks:
        return "continue"  # 继续处理下一个chunk
    else:
        return "merge"     # 所有chunk处理完成
```

**路由2: 合并后路由**
```python
def route_after_merge(state: WorkflowState) -> str:
    if state.get("needs_human_review"):
        return "human_review"  # 需要人工审核
    else:
        return "stage2"        # 直接进入Stage2
```

**路由3: 反馈后路由**
```python
def route_after_feedback(state: WorkflowState) -> str:
    if state.get("approved"):
        return "stage2"         # 审核通过，继续
    elif state.get("feedback_action") == "regenerate":
        return "stage1"         # 要求重新生成
    else:
        return "end"            # 结束任务
```

**路由4: 错误处理**
```python
def route_after_error(state: WorkflowState) -> str:
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if retry_count < max_retries:
        return "retry"  # 可以重试
    else:
        return "end"    # 结束
```

## 5.5 并行处理

### 5.5.1 Stage1并行优化

**问题**: 顺序处理多个chunk效率低

**解决方案**: 循环 + 条件边

**实现**:
```python
# 1. 定义循环边
workflow.add_conditional_edges(
    "stage1_process",
    route_after_stage1,
    {
        "continue": "stage1_process",  # 循环回到自己
        "merge": "merge_outlines"      # 退出循环
    }
)

# 2. 在节点中推进索引
def node_stage1_process(state):
    current_index = state["current_chunk_index"]
    # 处理当前chunk...
    return {
        "current_chunk_index": current_index + 1,  # 推进索引
        "stage1_results": [...],  # 累积结果
    }
```

**效果**:
- ✅ 保持状态一致性
- ✅ 简化并行处理逻辑
- ✅ 易于理解和调试

### 5.5.2 真正的并行处理（可选）

如果需要真正的并行处理，可以使用：

```python
async def node_stage1_parallel(state: WorkflowState) -> WorkflowState:
    """并行处理所有chunks"""
    chunks = state["chunks"]

    # 并行处理
    tasks = [process_chunk(chunk) for chunk in chunks]
    results = await asyncio.gather(*tasks)

    return {
        "stage1_results": results,
        "status": "stage1_completed"
    }
```

**注意**: 并行处理需要考虑API限流和资源消耗

## 5.6 暂停与恢复

### 5.6.1 暂停机制

**配置中断点**:
```python
def compile_workflow():
    return workflow.compile(
        checkpointer=checkpointer.saver,
        interrupt_before=["process_feedback"]  # 在process_feedback前中断
    )
```

**中断流程**:
```
merge_outlines → human_review → process_feedback → [中断]
```

**状态保存**:
- 自动保存到SQLite checkpointer
- 手动保存到JSON快速访问层
- 记录执行日志

### 5.6.2 恢复机制

**恢复API**:
```python
async def resume_workflow(task_id: str, human_feedback: dict):
    # 1. 注入人工反馈
    config = {"configurable": {"thread_id": task_id}}
    await workflow.aupdate_state(config, {
        "human_feedback": human_feedback,
        "needs_human_review": False,
    })

    # 2. 恢复执行
    final_state = await workflow.ainvoke(None, config)
    return final_state
```

**恢复流程**:
```
[中断点] → process_feedback → route_after_feedback → stage2
```

## 5.7 错误处理

### 5.7.1 错误类型

**节点错误**:
- 网络请求失败
- 文件不存在
- LLM API错误
- 解析失败

**系统错误**:
- 磁盘空间不足
- 内存不足
- 权限错误

### 5.7.2 错误处理策略

**重试机制**:
```python
def node_with_retry(func):
    async def wrapper(state):
        try:
            return await func(state)
        except Exception as e:
            # 记录错误
            logger.error(f"节点执行失败: {e}")

            # 增加重试次数
            state["retry_count"] = state.get("retry_count", 0) + 1

            # 抛出异常，由handle_error处理
            raise
    return wrapper
```

**错误恢复**:
```python
workflow.add_edge("any_node", "handle_error")
workflow.add_conditional_edges(
    "handle_error",
    route_after_error,
    {
        "retry": "parse_pdf",  # 重试
        "end": "END"           # 结束
    }
)
```

### 5.7.3 错误日志

**执行日志**:
```python
def log_execution(state: WorkflowState, node_name: str):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "node": node_name,
        "status": state.get("status"),
        "progress": state.get("progress_percentage")
    }
    state.setdefault("execution_log", []).append(log_entry)
```

## 5.8 工作流执行示例

### 5.8.1 正常执行

```python
# 1. 创建初始状态
initial_state = create_initial_state(
    task_id="demo-001",
    pdf_path="paper.pdf",
    presentation_style="academic"
)

# 2. 编译工作流
workflow = create_workflow()
compiled = workflow.compile(checkpointer=checkpointer)

# 3. 执行工作流
final_state = await compiled.ainvoke(
    initial_state,
    config={"configurable": {"thread_id": "demo-001"}}
)

# 4. 检查结果
print(f"状态: {final_state['status']}")
print(f"输出: {final_state['output_path']}")
```

### 5.8.2 带审核的执行

```python
# 1. 执行到审核点
initial_state = create_initial_state(...)
final_state = await compiled.ainvoke(initial_state, config)

# 2. 检查是否需要审核
if final_state.get("needs_human_review"):
    print("等待人工审核...")

    # 3. 人工审核后提交反馈
    human_feedback = {
        "approved": True,
        "comments": "大纲看起来不错"
    }

    # 4. 恢复工作流
    final_state = await resume_workflow("demo-001", human_feedback)
```

## 5.9 性能优化

### 5.9.1 异步处理

所有I/O密集型操作都使用异步：
```python
async def node_parse_pdf(state):
    # 异步网络请求
    result = await mineru_client.parse_pdf(...)

async def node_stage1_process(state):
    # 异步LLM调用
    outline = await llm_client.generate_outline(...)
```

### 5.9.2 并行处理

Stage1使用循环优化，避免串行等待

### 5.9.3 状态优化

- 最小化状态大小
- 避免存储大对象
- 使用引用而非复制

## 5.10 章节导航

- **上一章**: [核心概念与术语](04_核心概念与术语.md) - 了解核心概念
- **下一章**: [第6章 - 状态管理机制](06_状态管理机制.md) - 深入状态管理
- **代码示例**: [工作流示例](code-examples/basic/03_run-workflow.py) - 学习使用
- **深入理解**: [第7章 - 数据存储与持久化](07_数据存储与持久化.md) - 存储机制

---

**本章要点**:
- ✅ 10个节点的工作流设计，职责单一
- ✅ 条件边实现动态路由和循环
- ✅ 支持并行处理和中断恢复
- ✅ 完整的错误处理和重试机制
- ✅ 异步处理提升性能
