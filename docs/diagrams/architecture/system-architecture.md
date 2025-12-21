# 系统整体架构图

## Mermaid 图表

```mermaid
graph TB
    %% 用户层
    User[👤 用户] --> |上传PDF| Frontend[🌐 前端应用<br/>React + TypeScript<br/>Port 3000]

    %% 前后端通信
    Frontend --> |HTTP/REST| API[⚡ FastAPI 服务器<br/>Port 8000]
    Frontend --> |WebSocket/SSE| API

    %% 后端服务
    API --> |调用| Workflow[🔄 LangGraph 工作流<br/>Port 8123]

    %% 工作流节点
    Workflow --> Init[1️⃣ 初始化]
    Workflow --> PDF[2️⃣ PDF解析]
    Workflow --> Split[3️⃣ 文本分块]
    Workflow --> Stage1[4️⃣ Stage1处理]
    Workflow --> Merge[5️⃣ 合并大纲]
    Workflow --> Review[6️⃣ 人工审核]
    Workflow --> Stage2[7️⃣ Stage2处理]
    Workflow --> Render[8️⃣ 渲染]

    %% 外部服务
    PDF --> MinerU[📄 MinerU API<br/>PDF解析]
    Stage1 --> LLM1[🧠 LLM提供商<br/>DeepSeek/Kimi/OpenAI]
    Stage2 --> LLM2[🧠 LLM提供商]
    Render --> Marp[🎨 Marp CLI<br/>演示文稿渲染]

    %% 存储层
    Workflow --> Storage[💾 存储层]
    Storage --> SQLite[(🗄️ SQLite<br/>LangGraph Checkpoint)]
    Storage --> JSON[(📁 JSON<br/>任务快照)]
    Storage --> Files[📂 文件系统<br/>PDF/图片/输出]

    %% 样式
    classDef userClass fill:#e1f5fe
    classDef frontendClass fill:#f3e5f5
    classDef backendClass fill:#e8f5e9
    classDef workflowClass fill:#fff3e0
    classDef serviceClass fill:#fce4ec
    classDef storageClass fill:#f1f8e9

    class User userClass
    class Frontend frontendClass
    class API backendClass
    class Workflow,Init,PDF,Split,Stage1,Merge,Review,Stage2,Render workflowClass
    class MinerU,LLM1,LLM2,Marp serviceClass
    class Storage,SQLite,JSON,Files storageClass
```

## 架构说明

### 分层架构

1. **表现层**: React 前端应用
   - 用户界面
   - 文件上传
   - 任务监控
   - 结果展示

2. **接口层**: FastAPI 服务器
   - REST API
   - 请求路由
   - 参数验证
   - 响应序列化

3. **业务层**: LangGraph 工作流
   - 10个处理节点
   - 状态管理
   - 条件路由
   - 错误处理

4. **服务层**: 外部服务集成
   - MinerU PDF解析
   - LLM文本处理
   - Marp渲染引擎

5. **数据层**: 存储系统
   - SQLite 持久化
   - JSON 快速访问
   - 文件系统

### 数据流

1. 用户通过前端上传 PDF
2. FastAPI 接收并存储文件
3. 调用 LangGraph 工作流启动处理
4. 工作流节点依次执行
5. 外部服务完成特定任务
6. 结果存储到数据库和文件系统
7. 前端展示最终结果

### 核心特性

- ✅ 前后端分离
- ✅ 微服务架构
- ✅ 状态持久化
- ✅ 错误恢复
- ✅ 人机协作
