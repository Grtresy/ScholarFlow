# ScholarFlow 术语表

## A

### API (Application Programming Interface)
应用程序编程接口，一组定义软件组件之间交互的协议和工具。

### ACID
数据库事务的四个属性：原子性(Atomicity)、一致性(Consistency)、隔离性(Isolation)、持久性(Durability)。

### Asyncio
Python 异步 I/O 库，用于编写并发代码。

## B

### Batch Processing
批量处理，一次性处理多个数据项以提高效率。

### Breakpoint
检查点，工作流在特定节点保存状态以便后续恢复。

## C

### Checkpointer
检查点保存器，负责保存和恢复工作流状态。

### Chunk
文本分块，将长文档分割成较小的可处理片段。

### Condition Edge
条件边，基于状态值决定工作流下一步执行路径的边。

## D

### Double Storage
双存储架构，同时使用 SQLite 和 JSON 两种存储方式。

## E

### Execution Log
执行日志，记录工作流节点执行历史的列表。

## F

### FastAPI
现代化的 Python Web 框架，用于构建高性能 API。

## H

### HITL (Human-in-the-Loop)
人机协作，在自动化流程中引入人工审核和决策。

### HTTP (HyperText Transfer Protocol)
超文本传输协议，互联网上应用最广泛的网络协议。

## L

### LangChain
构建基于大语言模型的应用的框架。

### LangGraph
LangChain 生态系统中的工作流编排框架，用于构建复杂的有状态多智能体应用。

### LLM (Large Language Model)
大语言模型，基于深度学习的自然语言处理模型。

## M

### Marp
Markdown 演示文稿渲染器，支持将 Markdown 转换为 PPTX/PDF/HTML。

### Markdown
轻量级标记语言，易于读写。

### MinerU
专业的 PDF 解析服务，能够高精度提取文本和图片。

### Mermaid
基于文本的图表绘制工具，支持流程图、时序图等。

## N

### Node
节点，工作流中的单个处理单元。

### Next.js
基于 React 的全栈框架，支持服务端渲染。

## P

### PDF (Portable Document Format)
便携式文档格式，一种文件格式。

### Progress Percentage
进度百分比，表示工作流完成的程度。

### Pydantic
Python 数据验证库，使用类型提示进行数据验证。

### Python
一种高级编程语言，以其简洁的语法和强大的库生态系统闻名。

## R

### REST API
表述性状态转移 API，一种基于 HTTP 的 API 设计风格。

### Resume
恢复，从保存的检查点继续执行工作流。

### Retry Count
重试计数器，记录节点失败后重试的次数。

## S

### SQLite
轻量级关系型数据库，无需独立服务器。

### Stage 1
第一阶段，为每个文本块生成幻灯片大纲的阶段。

### Stage 2
第二阶段，将大纲转换为 Marp Markdown 格式的阶段。

### StateGraph
状态图，基于状态的工作流图结构。

### State Management
状态管理，追踪和管理工作流执行过程中的数据。

## T

### Task ID
任务唯一标识符，用于区分不同的工作流实例。

### Task Status
任务状态，表示工作流当前所处的阶段。

### Thread ID
线程ID，用于标识工作流实例的检查点线程。

### Tokenization
令牌化，将复杂数据替换为简单标记的过程。

### TypedDict
Python 类型提示工具，定义字典的结构和类型。

## U

### UV
快速的 Python 包管理器和虚拟环境工具。

## W

### Workflow
工作流，完成特定任务的一系列步骤。

### Workflow Engine
工作流引擎，负责编排和执行工作流的组件。

### WorkflowState
工作流状态，包含工作流执行过程中的所有数据。

---

**说明**: 本术语表包含 ScholarFlow 项目中使用的主要技术术语和概念，按字母顺序排列。如有疑问，请参考完整文档或提交 Issue。

**贡献**: 欢迎提交 PR 来完善术语表！
