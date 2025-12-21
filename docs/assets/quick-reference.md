# ScholarFlow 快速参考指南

## 🚀 快速开始

### 环境搭建
```bash
# 1. 克隆项目
git clone https://github.com/your-org/ScholarFlow.git
cd ScholarFlow

# 2. 安装依赖
uv sync

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 添加 API 密钥

# 4. 启动服务
# 终端1: 启动 LangGraph
uvicorn app.api.main:app --host 0.0.0.0 --port 8000

# 终端2: 启动前端
cd frontend && npm install && npm run dev
```

### API 密钥配置
```bash
# .env 文件
LLM_API_KEY=sk-your-deepseek-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

MINERU_API_KEY=your-mineru-key
MINERU_ENDPOINT=https://api.opendatalab.org.cn
```

## 📡 常用 API 调用

### 上传 PDF
```python
import requests

response = requests.post(
    "http://localhost:8000/api/upload",
    files={"file": open("paper.pdf", "rb")}
)
pdf_info = response.json()
```

### 创建任务
```python
response = requests.post(
    "http://localhost:8000/api/tasks",
    json={
        "pdf_path": pdf_info["path"],
        "presentation_style": "academic",
        "max_chars": 6000,
        "target_chunks": 6
    }
)
task = response.json()
task_id = task["task_id"]
```

### 查询状态
```python
import time

while True:
    response = requests.get(f"http://localhost:8000/api/tasks/{task_id}")
    status = response.json()

    if status["progress_percentage"] >= 100:
        print("完成!")
        break

    print(f"进度: {status['progress_percentage']}%")
    time.sleep(2)
```

### 下载结果
```python
response = requests.get(f"http://localhost:8000/api/download/{task_id}")
with open("presentation.pptx", "wb") as f:
    f.write(response.content)
```

## 🔧 开发命令

### 代码质量
```bash
# 格式化代码
black app/ tests/
isort app/ tests/

# 类型检查
mypy app/

# 代码检查
pylint app/
```

### 测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_workflow.py -v

# 生成覆盖率报告
pytest --cov=app --cov-report=html
```

### 调试
```bash
# 启用调试模式
export DEBUG=True

# 查看日志
tail -f logs/app.log

# 启用详细日志
export LOG_LEVEL=DEBUG
```

## 📁 目录结构

```
ScholarFlow/
├── app/                    # 后端代码
│   ├── api/               # API 端点
│   ├── graph/             # LangGraph 工作流
│   ├── services/          # 业务服务
│   └── storage/           # 存储层
├── frontend/              # 前端代码
├── docs/                  # 文档
├── tests/                 # 测试
└── data/                  # 数据目录
    ├── upload/            # 上传的PDF
    ├── workflows/         # 工作流数据
    └── outputs/           # 生成的演示文稿
```

## 🔑 核心概念

### 工作流节点
| 节点 | 功能 | 输入 | 输出 |
|------|------|------|------|
| initialize | 初始化 | 任务参数 | 初始状态 |
| parse_pdf | PDF解析 | PDF文件 | Markdown+图片 |
| split_markdown | 文本分块 | Markdown | 文本块 |
| stage1_process | 生成大纲 | 文本块 | 大纲列表 |
| merge_outlines | 合并大纲 | 大纲列表 | 统一大纲 |
| human_review | 人工审核 | 大纲 | 审核意见 |
| stage2_process | 格式转换 | 大纲 | Marp Markdown |
| render | 渲染 | Marp Markdown | PPTX/PDF |

### 任务状态
| 状态 | 说明 | 进度 |
|------|------|------|
| pending | 等待处理 | 0% |
| initialized | 已初始化 | 5% |
| parsing | 解析PDF | 10-20% |
| splitting | 文本分块 | 25-30% |
| stage1_processing | Stage1处理 | 40-60% |
| merging | 合并大纲 | 65-70% |
| human_review | 人工审核 | 70% |
| stage2_processing | Stage2处理 | 75-85% |
| rendering | 渲染 | 90% |
| completed | 完成 | 100% |
| failed | 失败 | 0% |

## ⚙️ 配置参数

### 环境变量
```bash
# LLM 配置
LLM_API_KEY              # LLM API 密钥
LLM_BASE_URL            # LLM 基础 URL
LLM_MODEL               # 模型名称
LLM_MAX_TOKENS          # 最大 token 数
LLM_TEMPERATURE         # 温度参数

# MinerU 配置
MINERU_API_KEY          # MinerU API 密钥
MINERU_ENDPOINT         # MinerU 端点

# 服务器配置
FASTAPI_HOST            # FastAPI 主机
FASTAPI_PORT            # FastAPI 端口
LANGGRAPH_HOST          # LangGraph 主机
LANGGRAPH_PORT          # LangGraph 端口

# 存储配置
DATA_DIR                # 数据目录
STORAGE_BACKEND         # 存储后端
```

### 工作流参数
```python
{
    "presentation_style": "academic",  # 演示风格
    "max_chars": 6000,                  # 最大字符数
    "target_chunks": 6,                 # 目标分块数
    "enable_human_review": True,        # 启用人工审核
    "enable_parallel_processing": True, # 启用并行处理
    "max_retries": 3                    # 最大重试次数
}
```

## 🐛 故障排除

### 常见错误

**错误**: `LLM API 密钥无效`
```bash
# 检查 .env 文件
cat .env | grep LLM_API_KEY

# 测试 API 连接
curl -H "Authorization: Bearer $LLM_API_KEY" $LLM_BASE_URL/models
```

**错误**: `PDF 文件解析失败`
```bash
# 检查 PDF 文件
file your-paper.pdf

# 检查 MinerU 状态
curl -H "Authorization: Bearer $MINERU_API_KEY" $MINERU_ENDPOINT/health
```

**错误**: `工作流卡住`
```bash
# 查看任务状态
curl http://localhost:8000/api/tasks

# 重置任务
curl -X DELETE http://localhost:8000/api/tasks/{task_id}
```

**错误**: `数据库锁定`
```bash
# 重启服务
pkill -f "uvicorn"
uvicorn app.api.main:app --host 0.0.0.0 --port 8000

# 清理 SQLite 锁文件
rm -f data/workflows/checkpoints.db-journal
```

### 日志查看
```bash
# 实时查看日志
tail -f logs/app.log

# 搜索错误
grep ERROR logs/app.log

# 查看特定任务日志
grep "task-123" logs/app.log
```

### 性能问题

**问题**: 处理速度慢
```bash
# 启用并行处理
export ENABLE_PARALLEL_PROCESSING=true

# 调整批次大小
export MAX_PARALLEL_CHUNKS=5

# 检查系统资源
top
htop
```

**问题**: 内存占用高
```bash
# 减少批次大小
export MAX_PARALLEL_CHUNKS=2

# 启用垃圾回收
export PYTHONMALLOC=malloc
export MALLOC_ARENA_MAX=2
```

## 📚 常用代码片段

### 异步工作流调用
```python
import asyncio
from app.graph.workflow import run_workflow

async def process_pdf(pdf_path: str):
    state = create_initial_state(
        task_id="demo",
        pdf_path=pdf_path,
        presentation_style="academic"
    )

    final_state = await run_workflow(state)
    return final_state["output_path"]

# 使用
result = asyncio.run(process_pdf("paper.pdf"))
```

### 自定义节点
```python
def custom_node(state: WorkflowState) -> WorkflowState:
    # 处理逻辑
    result = process(state["data"])

    return {
        "status": "completed",
        "result": result,
        "progress_percentage": state["progress_percentage"] + 20
    }
```

### 状态查询
```python
from app.storage.checkpointer import get_checkpointer

async def get_task_state(task_id: str):
    checkpointer = get_checkpointer()
    state = await checkpointer.load_state(task_id)
    return state
```

## 🎯 最佳实践

### 性能优化
1. **启用并行处理**: 设置 `enable_parallel_processing=true`
2. **调整批次大小**: 根据内存调整 `max_parallel_chunks`
3. **合理设置分块**: 平衡 `max_chars` 和 `target_chunks`
4. **使用缓存**: 避免重复处理相同文件

### 错误处理
1. **启用重试**: 设置合理的 `max_retries`
2. **记录日志**: 启用详细日志记录
3. **监控资源**: 定期检查内存和CPU使用
4. **备份数据**: 定期备份工作流数据

### 安全建议
1. **保护API密钥**: 使用环境变量，不提交到Git
2. **限制文件大小**: 设置合理的上传限制
3. **验证输入**: 始终验证PDF文件格式
4. **定期更新**: 保持依赖库最新

## 📞 获取帮助

- **文档**: [ScholarFlow 文档](../README.md)
- **GitHub**: https://github.com/your-org/ScholarFlow
- **Issues**: https://github.com/your-org/ScholarFlow/issues
- **讨论**: https://github.com/your-org/ScholarFlow/discussions

## 📝 更新日志

- **v1.0.0** - 初始版本，支持基础工作流
- **v1.1.0** - 添加人工审核功能
- **v1.2.0** - 优化并行处理性能
- **v1.3.0** - 添加图片Token化保护

---

**最后更新**: 2025-12-21
