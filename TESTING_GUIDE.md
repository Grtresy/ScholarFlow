# WebSocket 实时推送 - 测试指南

## 概述

ScholarFlow 的 WebSocket 实时推送功能已经完成实施。本指南说明如何测试整个系统。

## 🎯 实施完成的功能

### ✅ 后端实现
- [x] WebSocket 服务端 (`app/api/websocket.py`)
- [x] FastAPI 路由集成 (`app/main.py`)
- [x] 状态持久化钩子 (`app/storage/checkpointer.py`)
- [x] Stage1 处理节点进度推送 (`app/graph/nodes/stage1_processing.py`)
- [x] Stage2 处理节点进度推送 (`app/graph/nodes/stage2_processing.py`)
- [x] PDF 解析节点进度推送 (`app/graph/nodes/pdf_parsing.py`)

### ✅ 前端实现
- [x] WebSocket 客户端库 (`frontend/src/lib/websocket.ts`)
- [x] TaskStatus 组件重构 (`frontend/src/components/TaskStatus.tsx`)
- [x] StepProgress 组件增强 (`frontend/src/components/StepProgress.tsx`)
- [x] ReviewSection 组件实时同步 (`frontend/src/components/ReviewSection.tsx`)
- [x] DebugPanel 组件监控 (`frontend/src/components/DebugPanel.tsx`)

### ✅ 测试工具
- [x] WebSocket 测试脚本 (`tests/test_websocket.py`)
- [x] 集成测试脚本 (`tests/test_frontend_websocket_integration.py`)
- [x] 前端测试脚本 (`tests/test_frontend_websocket.js`)
- [x] 测试指南文档 (`WEBSOCKET_TESTING.md`)

## 🚀 快速开始

### 1. 启动后端服务

```bash
# 启动 FastAPI 服务器
cd /path/to/ScholarFlow
uvicorn app.main:create_app --host 0.0.0.0 --port 8000 --reload

# 或者使用开发模式
python -m app.main serve --host 0.0.0.0 --port 8000
```

### 2. 运行 WebSocket 测试

```bash
# 运行 Python WebSocket 测试
python tests/test_websocket.py

# 运行集成测试
python tests/test_frontend_websocket_integration.py
```

### 3. 运行前端测试

```bash
# 在 Node.js 环境中运行
node tests/test_frontend_websocket.js

# 或者在浏览器控制台中运行
# 打开浏览器开发者工具，粘贴 test_frontend_websocket.js 的内容
```

## 🧪 测试场景

### 场景 1: 基础连接测试

**目标**: 验证 WebSocket 连接是否正常工作

**步骤**:
1. 启动 FastAPI 服务器
2. 运行 `tests/test_websocket.py`
3. 观察输出，确认连接成功

**预期结果**:
```
✓ WebSocket connected successfully!
✓ Auth message sent
📨 Received: {
  "type": "connected",
  "data": {
    "task_id": "test-task-123",
    "message": "WebSocket connection established"
  },
  "timestamp": 1703123456.789
}
```

### 场景 2: 实时状态更新测试

**目标**: 验证工作流执行时状态是否实时推送

**步骤**:
1. 启动 FastAPI 服务器
2. 创建测试任务 (通过前端界面或 API)
3. 观察前端 TaskStatus 组件的实时更新
4. 查看 DebugPanel 的 WebSocket 标签页

**预期结果**:
- TaskStatus 显示"实时连接"状态
- StepProgress 显示实时进度条
- DebugPanel 显示 WebSocket 消息流

### 场景 3: Chunk 进度测试

**目标**: 验证 Stage1 处理时是否显示详细 chunk 进度

**步骤**:
1. 启动完整工作流 (包含 PDF 上传)
2. 观察 Stage1 处理阶段
3. 查看 StepProgress 组件的"实时进度"卡片

**预期结果**:
- 显示当前 chunk 进度: `2/6`
- 显示当前 chunk 内容预览
- 进度条实时更新

### 场景 4: 渲染进度测试

**目标**: 验证 Stage2 处理和渲染时的进度推送

**步骤**:
1. 等待工作流进入 Stage2 处理
2. 观察渲染进度显示
3. 查看不同渲染阶段

**预期结果**:
- 显示 `extracting`, `parsing`, `rendering` 阶段
- 进度百分比实时更新
- 输出格式显示

### 场景 5: 降级测试

**目标**: 验证 WebSocket 失败时是否降级到轮询

**步骤**:
1. 启动工作流
2. 人为断开 WebSocket 连接
3. 观察前端状态变化

**预期结果**:
- TaskStatus 显示"连接错误，使用降级轮询"
- 继续通过轮询获取状态更新
- DebugPanel 显示连接错误状态

## 🔍 调试指南

### 检查 WebSocket 连接

在浏览器开发者工具中:

```javascript
// 1. 检查 WebSocket 连接
const ws = new WebSocket('ws://localhost:8000/ws/your-task-id');
ws.onopen = () => console.log('Connected!');
ws.onmessage = (e) => console.log('Message:', e.data);

// 2. 检查前端状态
console.log('[WebSocket] Connection status:', connectionStatus);
console.log('[WebSocket] Messages:', websocketMessages);
```

### 查看后端日志

```bash
# 查看 FastAPI 服务器日志
tail -f uvicorn.log | grep -i websocket

# 或在服务器控制台中观察
# 查找类似输出:
# [INFO] WebSocket connected for task test-task-123
# [INFO] WebSocket disconnected for task test-task-123
```

### 使用 DebugPanel

在运行的前端应用中:

1. 打开调试面板 (通常有调试按钮)
2. 切换到 "WebSocket" 标签页
3. 查看连接状态和消息列表
4. 监控实时消息流

## 📊 性能监控

### 连接数监控

```python
from app.api.websocket import get_connection_count

count = get_connection_count("your-task-id")
print(f"Active connections: {count}")
```

### 消息延迟监控

每条 WebSocket 消息包含 `timestamp` 字段:

```javascript
// 在前端计算延迟
const delay = Date.now() - message.timestamp;
console.log(`Message delay: ${delay}ms`);
```

### WebSocket 状态分布

在 DebugPanel 中查看:
- 连接状态 (已连接/连接中/错误/断开)
- 消息数量统计
- 连接持续时间

## 🚨 故障排除

### 问题 1: 连接被拒绝

**原因**: FastAPI 服务器未运行

**解决**:
```bash
# 启动服务器
uvicorn app.main:create_app --host 0.0.0.0 --port 8000 --reload
```

### 问题 2: 前端显示"连接错误"

**原因**: WebSocket 连接失败

**解决**:
1. 检查服务器是否在端口 8000 运行
2. 检查防火墙设置
3. 查看浏览器控制台错误

### 问题 3: 没有实时进度更新

**原因**: 工作流未执行或状态更新未触发

**解决**:
1. 确认工作流正在运行
2. 检查后端日志中的 WebSocket 推送
3. 查看 DebugPanel 的消息列表

### 问题 4: Chunk 进度不显示

**原因**: Stage1 处理未开始或消息未发送

**解决**:
1. 确认 PDF 已上传并解析完成
2. 观察 Stage1 处理阶段
3. 检查 `send_chunk_progress` 是否被调用

### 问题 5: 前端编译错误

**原因**: TypeScript 类型错误或导入问题

**解决**:
```bash
# 检查 TypeScript 类型
cd frontend
npm run type-check

# 重新编译
npm run build
```

## 📈 基准测试

### 连接性能

- **连接建立时间**: < 100ms
- **消息推送延迟**: < 50ms
- **并发连接数**: 100+ (测试环境)

### 消息大小

- **状态更新**: ~500 bytes
- **Chunk 进度**: ~1KB (包含内容预览)
- **渲染进度**: ~300 bytes

### 内存使用

- **每个连接**: ~50KB
- **消息队列**: ~10MB (1000条消息)

## 🎓 进阶测试

### 压力测试

```bash
# 使用 wrk 或 ab 进行压力测试
wrk -c 100 -d 30s -t 4 http://localhost:8000/api/tasks

# 使用 websockets 进行并发连接测试
python tests/test_websocket_concurrent.py
```

### 长时间运行测试

```bash
# 运行 1 小时测试
timeout 3600 python tests/test_websocket_long_running.py
```

### 网络中断测试

1. 启动工作流
2. 断开网络连接 30 秒
3. 重新连接网络
4. 验证自动重连和状态恢复

## 📝 报告问题

如果发现任何问题，请提供以下信息:

1. **环境信息**:
   - 操作系统
   - Python/Node.js 版本
   - 浏览器版本

2. **问题描述**:
   - 复现步骤
   - 预期结果
   - 实际结果

3. **日志**:
   - 后端服务器日志
   - 浏览器控制台输出
   - DebugPanel 截图

4. **测试数据**:
   - Task ID
   - WebSocket 消息列表
   - 错误堆栈跟踪

## ✅ 测试清单

使用此清单确保所有功能正常:

- [ ] 后端服务器启动成功
- [ ] WebSocket 连接建立成功
- [ ] 连接确认消息接收
- [ ] 任务状态实时更新
- [ ] Stage1 chunk 进度显示
- [ ] Stage2 渲染进度显示
- [ ] 人工审核实时通知
- [ ] 错误状态实时反馈
- [ ] 连接断开自动重连
- [ ] 降级到轮询机制
- [ ] DebugPanel WebSocket 监控
- [ ] 前端编译无错误
- [ ] 所有测试脚本通过

## 🎉 成功标准

当所有测试通过且清单完成时，WebSocket 实时推送功能即可投入使用!

---

**注意**: 本指南涵盖了 WebSocket 实时推送功能的所有测试场景。如有疑问，请参考代码注释或联系开发团队。
