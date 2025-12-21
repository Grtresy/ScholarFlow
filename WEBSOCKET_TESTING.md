# WebSocket 实时推送测试指南

## 概述

ScholarFlow 现在支持通过 WebSocket 实现实时工作流进度推送。以下是测试指南。

## 功能特性

### 1. WebSocket 端点
- **URL**: `ws://localhost:8000/ws/{task_id}`
- **协议**: JSON 消息格式
- **功能**: 实时接收工作流状态更新

### 2. 消息类型

#### 连接确认
```json
{
  "type": "connected",
  "data": {
    "task_id": "your-task-id",
    "message": "WebSocket connection established"
  },
  "timestamp": 1703123456.789
}
```

#### 状态更新
```json
{
  "type": "status_update",
  "data": {
    "task_id": "your-task-id",
    "status": "stage1_processing",
    "progress": 35.5,
    "current_step": "Stage 1: 处理chunk 2/6",
    "updated_fields": ["status", "progress_percentage", "current_step"]
  },
  "timestamp": 1703123456.789
}
```

#### Chunk 进度（Stage1）
```json
{
  "type": "chunk_progress",
  "data": {
    "task_id": "your-task-id",
    "chunk_index": 1,
    "total_chunks": 6,
    "completed_chunks": 2,
    "current_chunk_content": "This is a preview of the current chunk..."
  },
  "timestamp": 1703123456.789
}
```

#### 渲染进度（Stage2/渲染）
```json
{
  "type": "render_progress",
  "data": {
    "task_id": "your-task-id",
    "stage": "parsing",
    "percentage": 30.0,
    "output_format": "pptx"
  },
  "timestamp": 1703123456.789
}
```

#### 人工审核
```json
{
  "type": "review_required",
  "data": {
    "task_id": "your-task-id",
    "review_points": [
      {"point": "检查大纲结构", "status": "pending"},
      {"point": "确认内容准确性", "status": "pending"}
    ],
    "can_edit": true
  },
  "timestamp": 1703123456.789
}
```

#### 错误通知
```json
{
  "type": "error",
  "data": {
    "task_id": "your-task-id",
    "error_code": "LLM_API_ERROR",
    "error_message": "API rate limit exceeded",
    "node_name": "stage1_processing",
    "recovery_hint": "Please try again later"
  },
  "timestamp": 1703123456.789
}
```

#### 任务完成
```json
{
  "type": "completed",
  "data": {
    "task_id": "your-task-id",
    "result_url": "/api/download/your-task-id",
    "output_format": "pptx"
  },
  "timestamp": 1703123456.789
}
```

## 测试步骤

### 1. 启动 FastAPI 服务器
```bash
cd /path/to/ScholarFlow
uvicorn app.main:create_app --host 0.0.0.0 --port 8000 --reload
```

### 2. 使用 WebSocket 测试客户端

#### 使用 Python（推荐）
```python
import asyncio
import websockets
import json

async def test():
    task_id = "your-task-id"
    uri = f"ws://localhost:8000/ws/{task_id}"

    async with websockets.connect(uri) as websocket:
        print("Connected!")
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Received: {data}")

asyncio.run(test())
```

#### 使用 Node.js
```javascript
const WebSocket = require('ws');

const taskId = 'your-task-id';
const ws = new WebSocket(`ws://localhost:8000/ws/${taskId}`);

ws.on('open', () => {
    console.log('Connected!');
});

ws.on('message', (message) => {
    const data = JSON.parse(message);
    console.log('Received:', data);
});
```

#### 使用浏览器（开发者工具）
```javascript
const taskId = 'your-task-id';
const ws = new WebSocket(`ws://localhost:8000/ws/${taskId}`);

ws.onopen = () => console.log('Connected!');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

### 3. 创建测试任务

通过 REST API 创建一个新任务：
```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_path": "/path/to/your.pdf",
    "presentation_style": "academic",
    "max_chars": 6000,
    "target_chunks": 6
  }'
```

记录返回的 `task_id`，然后在 WebSocket 客户端中使用该 ID。

### 4. 验证消息推送

在工作流执行过程中，你应该能看到以下消息：

1. **初始状态** - `status_update`
2. **PDF解析** - `render_progress` (extracting stage)
3. **文本分割** - `status_update`
4. **Stage1处理** - `chunk_progress` (每个chunk)
5. **大纲合并** - `status_update`
6. **人工审核** - `review_required` (如果启用)
7. **Stage2处理** - `render_progress` (parsing stage)
8. **渲染** - `render_progress` (rendering stage)
9. **完成** - `completed`

## 故障排除

### 问题 1: 连接被拒绝
**原因**: FastAPI 服务器未运行
**解决**: 确保服务器在端口 8000 上运行

### 问题 2: 收到 "connected" 消息后无其他消息
**原因**: 工作流未开始或无活动连接
**解决**: 创建新任务并确保 task_id 正确

### 问题 3: 消息格式错误
**原因**: 消息不是有效的 JSON
**解决**: 检查消息内容，确保是有效的 JSON 字符串

### 问题 4: 导入错误
**原因**: 缺少依赖或路径问题
**解决**: 确保在项目根目录运行脚本

## 性能监控

### 连接数监控
```python
from app.api.websocket import get_connection_count

count = get_connection_count("your-task-id")
print(f"Active connections: {count}")
```

### 消息延迟监控
每条消息包含 `timestamp` 字段，你可以计算延迟：
```python
import time

# 在接收消息时
current_time = time.time()
delay = current_time - message['timestamp']
print(f"Message delay: {delay:.2f}s")
```

## 下一步计划

1. **前端集成** - 在 React 前端中实现 WebSocket 客户端
2. **连接管理** - 添加自动重连和心跳机制
3. **消息压缩** - 实现 gzip 压缩减少带宽
4. **身份验证** - 添加 WebSocket 认证机制

## 注意事项

- WebSocket 连接在任务完成后不会自动断开
- 如果客户端断开连接，状态更新将丢失（直到重新连接）
- 建议在生产环境中添加消息持久化和重放机制
- WebSocket 推送是异步的，不会阻塞主工作流
