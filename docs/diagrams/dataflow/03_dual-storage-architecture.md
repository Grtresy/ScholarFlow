# 双存储架构图

## 概述
展示ScholarFlow的SQLite + JSON双存储架构设计。

```mermaid
graph TB
    subgraph "应用层"
        A1[Workflow Nodes]
        A2[API Endpoints]
        A3[Checkpointer Interface]
    end

    subgraph "存储抽象层"
        S1[Storage Interface]
        S2[Checkpointer Abstraction]
    end

    subgraph "主存储层 - SQLite"
        DB[(SQLite数据库<br/>checkpoints.db)]
        DB_T1[WAL文件]
        DB_T2[共享内存文件]
        DB_T3[回滚日志]
    end

    subgraph "快速访问层 - JSON"
        J1[任务目录<br/>tasks/]
        J2[任务文件<br/>{task_id}.json]
        J3[元数据缓存]
    end

    subgraph "文件系统"
        FS1[上传目录<br/>upload/]
        FS2[中间目录<br/>intermediate/]
        FS3[输出目录<br/>output/]
    end

    A1 --> S1
    A2 --> S1
    A3 --> S2
    S1 --> DB
    S1 --> J1
    S2 --> DB
    J1 --> J2
    J2 --> J3

    DB --> DB_T1
    DB --> DB_T2
    DB --> DB_T3

    A1 --> FS2
    A2 --> FS3
    A2 --> FS1

    style DB fill:#e3f2fd
    style J1 fill:#fff3e0
    style FS1 fill:#e8f5e9
    style FS2 fill:#fff9c4
    style FS3 fill:#f3e5f5
```

## 存储职责分工

### SQLite数据库 - 权威存储
**职责**：
- 存储完整的WorkflowState
- 支持LangGraph Checkpoint机制
- 提供ACID事务保证
- 支持版本控制和回溯

**优势**：
- ✅ **事务安全**：WAL模式确保数据一致性
- ✅ **高并发**：支持读写并发
- ✅ **可靠性**：成熟的存储引擎
- ✅ **版本控制**：自动管理状态版本

**使用场景**：
- 工作流状态持久化
- 断点恢复
- 状态回溯
- 长事务处理

### JSON文件 - 快速访问层
**职责**：
- 存储任务元数据快照
- 提供快速查询接口
- 支持简单的条件过滤
- 便于调试和日志分析

**优势**：
- ✅ **快速读取**：直接文件I/O，无需解析
- ✅ **人类可读**：易于调试和查看
- ✅ **简单查询**：grep、jq等工具直接操作
- ✅ **轻量级**：无额外依赖

**使用场景**：
- 任务列表查询
- 状态概览
- 调试分析
- 简单统计

## 存储格式对比

### SQLite存储格式
```sql
-- 表结构
CREATE TABLE checkpoint (
    thread_id TEXT NOT NULL,           -- 任务ID
    node_name TEXT NOT NULL,           -- 节点名称
    checkpoint_ns TEXT NOT NULL,       -- 命名空间
    payload BLOB NOT NULL,             -- 状态数据(JSON序列化)
    PRIMARY KEY (thread_id, node_name, checkpoint_ns)
);

-- 索引
CREATE INDEX idx_thread_id ON checkpoint(thread_id);
CREATE INDEX idx_node_name ON checkpoint(node_name);

-- 示例数据
INSERT INTO checkpoint VALUES (
    'task_001',
    'parse_pdf',
    'default',
    '{"task_id": "task_001", "status": "parsing", ...}'
);
```

### JSON存储格式
```json
{
  "task_id": "task_001",
  "status": "parsing",
  "created_at": "2024-12-21T10:30:00",
  "updated_at": "2024-12-21T10:35:00",
  "progress_percentage": 25.0,
  "current_step": "正在解析PDF",
  "pdf_path": "data/upload/paper.pdf",
  "markdown_text": "...",
  "execution_log": [
    {
      "timestamp": "2024-12-21T10:30:00",
      "event": "task_created"
    }
  ],
  "metadata": {
    "source": "scholarflow",
    "version": "2.0.0"
  }
}
```

## 协同工作机制

### 写入流程
```python
def save_state(task_id: str, state: dict, node_name: str):
    """双存储写入"""
    # 1. 写入SQLite (主存储)
    save_to_sqlite(task_id, state, node_name)

    # 2. 写入JSON (快速访问)
    save_to_json(task_id, state)

    # 3. 验证一致性
    verify_consistency(task_id)

def save_to_sqlite(task_id: str, state: dict, node_name: str):
    """SQLite写入"""
    payload = json.dumps(state).encode('utf-8')
    checkpointer.save(
        thread_id=task_id,
        node_name=node_name,
        checkpoint_ns='default',
        value={'payload': payload}
    )

def save_to_json(task_id: str, state: dict):
    """JSON写入"""
    json_path = Path(f"data/workflows/tasks/{task_id}.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
```

### 读取流程
```python
def load_state(task_id: str) -> dict:
    """双存储读取"""
    # 1. 优先从SQLite读取完整状态
    sqlite_state = load_from_sqlite(task_id)

    # 2. 从JSON读取元数据(用于快速查询)
    json_metadata = load_from_json(task_id)

    # 3. 合并数据 (SQLite为主，JSON为辅)
    return merge_states(sqlite_state, json_metadata)

def load_from_sqlite(task_id: str) -> dict:
    """从SQLite加载完整状态"""
    # 获取最新checkpoint
    checkpoint = checkpointer.get(task_id, 'default')
    if checkpoint and 'payload' in checkpoint:
        return json.loads(checkpoint['payload'])
    return {}

def load_from_json(task_id: str) -> dict:
    """从JSON加载元数据"""
    json_path = Path(f"data/workflows/tasks/{task_id}.json")
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}
```

## 查询性能对比

| 查询类型 | SQLite | JSON | 推荐 |
|----------|--------|------|------|
| 获取完整状态 | O(log n) | O(1) | SQLite |
| 列出所有任务 | O(n) | O(n) | JSON |
| 按状态筛选 | O(n) | O(n) | JSON |
| 获取元数据 | O(log n) | O(1) | JSON |
| 状态历史 | O(log n) | ❌ | SQLite |
| 调试查看 | ❌ | O(1) | JSON |

## 优化策略

### 写入优化
1. **批量写入**：多个更新合并为一次写入
2. **异步写入**：后台线程执行JSON写入
3. **压缩存储**：大字段使用gzip压缩
4. **写前缓存**：先写内存再批量刷盘

### 读取优化
1. **预加载**：启动时加载活跃任务
2. **懒加载**：按需加载状态详情
3. **缓存策略**：LRU缓存热点数据
4. **索引优化**：SQLite创建合适索引

### 存储优化
1. **定期清理**：删除已完成的老任务
2. **归档策略**：历史数据移动到归档存储
3. **压缩整理**：SQLite VACUUM和JSON压缩
4. **监控告警**：存储大小和文件数量监控

## 容灾设计

### 数据冗余
- **双写保证**：SQLite和JSON同时写入
- **校验机制**：定期验证数据一致性
- **快照备份**：每日自动备份所有数据

### 故障恢复
- **损坏检测**：启动时检查数据库完整性
- **自动修复**：尝试从备份恢复
- **手动干预**：提供修复工具和文档

## 监控指标

| 指标 | SQLite | JSON | 告警阈值 |
|------|--------|------|----------|
| 数据库大小 | < 5GB | - | 80% |
| JSON文件数 | - | < 10000 | 80% |
| 写入延迟 | < 100ms | < 50ms | 100ms |
| 读取延迟 | < 50ms | < 10ms | 50ms |
| 错误率 | < 0.1% | < 0.1% | 1% |
| 一致性检查 | 每日 | 每日 | 失败告警 |
