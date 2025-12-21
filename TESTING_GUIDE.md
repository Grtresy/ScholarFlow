# 测试指南：验证人类反馈意见是否有效

## 🎯 问题背景

用户反馈"请使用英文做PPT"后，生成的PPT仍然是中文，怀疑修改意见没有生效。

## 🔍 问题原因

**修复前的问题**：
- ✅ Stage 1 接收了修改意见
- ❌ Stage 2 **没有**接收修改意见
- 所以即使用户要求英文，Stage 2仍用中文模板生成PPT

**修复后的改进**：
- ✅ Stage 1 接收并使用修改意见
- ✅ Stage 2 也接收并使用修改意见
- 修改意见现在会影响整个流程

## 📝 测试步骤

### 1. 启动服务
```bash
# 启动FastAPI服务
python -m app.main serve

# 或者分别启动（推荐）
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload &
python langgraph_server.py --host 0.0.0.0 --port 8123 &
```

### 2. 创建测试任务
```bash
# 上传PDF文件
curl -X POST http://localhost:8000/api/upload \
  -F "file=@/path/to/your/paper.pdf"

# 启动工作流
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_path": "/path/to/uploaded/paper.pdf",
    "presentation_style": "academic",
    "max_chars": 6000,
    "target_chunks": 6,
    "enable_human_review": true
  }'
```

### 3. 等待到人类审核阶段
```bash
# 轮询检查状态
curl http://localhost:8000/api/tasks/{task_id}

# 当看到以下状态时，说明到了审核阶段：
# {
#   "status": "human_review",
#   "needs_human_review": true,
#   "review_points": [...]
# }
```

### 4. 提交带修改意见的反馈

**测试用例1：要求英文**
```bash
curl -X POST http://localhost:8000/api/tasks/{task_id}/human-feedback \
  -H "Content-Type: application/json" \
  -d '{
    "action": "regenerate",
    "comments": "请使用英文制作PPT，不要使用中文"
  }'
```

**测试用例2：要求更详细**
```bash
curl -X POST http://localhost:8000/api/tasks/{task_id}/human-feedback \
  -H "Content-Type: application/json" \
  -d '{
    "action": "regenerate",
    "comments": "请在每个部分添加更多详细解释和例子"
  }'
```

**测试用例3：要求简化**
```bash
curl -X POST http://localhost:8000/api/tasks/{task_id}/human-feedback \
  -H "Content-Type: application/json" \
  -d '{
    "action": "regenerate",
    "comments": "请简化内容，每页最多2个要点"
  }'
```

### 5. 验证修改意见是否生效

#### 方法1：检查工作流状态
```bash
# 查看执行日志
curl http://localhost:8000/api/tasks/{task_id} | jq '.execution_log'

# 应该看到类似记录：
# {
#   "timestamp": "2024-12-21T15:30:00",
#   "event": "human_feedback_received",
#   "approved": false,
#   "action": "regenerate",
#   "has_comments": true
# }
```

#### 方法2：检查生成的outline
等待工作流完成后，查看生成的outline：

```bash
# 查看合并后的outline
curl http://localhost:8000/api/tasks/{task_id} | jq '.merged_outline'

# 检查是否反映了修改意见
# 例如，如果要求英文，应该看到英文内容
# 如果要求详细，应该看到更多细节
```

#### 方法3：检查最终PPT
等待渲染完成，下载并查看最终PPT：

```bash
# 获取PPT下载链接
curl http://localhost:8000/api/tasks/{task_id} | jq '.output_path'

# 下载PPT
curl -o presentation.pptx http://localhost:8000/api/download/{task_id}
```

## ✅ 验证标准

### Stage 1验证（Outline生成）
- 如果要求"英文"，outline应该是英文
- 如果要求"详细"，outline应该包含更多细节
- 如果要求"简化"，outline应该更简洁

### Stage 2验证（Marp Markdown生成）
- 语言应该与修改要求一致
- 详细程度应该符合要求
- 结构应该符合要求

### 最终PPT验证
- 语言：英文/中文应该符合要求
- 内容：详细程度应该符合要求
- 结构：页数和要点数量应该符合要求

## 🔧 调试技巧

### 1. 查看详细日志
```bash
# 查看某个任务的完整状态
curl http://localhost:8000/api/tasks/{task_id} | python -m json.tool

# 特别关注这些字段：
# - user_modifications: 应该包含你的修改意见
# - execution_log: 应该记录反馈事件
# - merged_outline: 应该反映修改意见
# - marp_markdown: 应该反映修改意见
```

### 2. 检查prompt注入
如果你想验证修改意见是否正确注入到prompt，可以：

```python
# 临时在代码中添加日志
# 文件：app/graph/nodes/stage1_processing.py (第50行附近)
print(f"[DEBUG] User modifications: {user_modifications}")
print(f"[DEBUG] Generated prompt preview: {prompt[:200]}")

# 文件：app/graph/nodes/stage2_processing.py (第40行附近)
print(f"[DEBUG] User modifications: {user_modifications}")
print(f"[DEBUG] Generated prompt preview: {prompt[:200]}")
```

### 3. 对比测试
创建一个没有修改意见的任务作为对照组：

```bash
# 对照组：直接批准，不添加修改意见
curl -X POST http://localhost:8000/api/tasks/{task_id}/human-feedback \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true
  }'
```

对比两个任务的输出，验证修改意见的影响。

## 📊 预期结果

### 修改前 ❌
- 用户要求"英文PPT"
- Stage 1 可能生成英文outline
- Stage 2 仍用中文模板 → 最终PPT是中文

### 修改后 ✅
- 用户要求"英文PPT"
- Stage 1 生成英文outline
- Stage 2 接收修改意见 → 生成英文Marp Markdown
- 最终PPT是英文

## 🚨 常见问题

### Q: 修改意见没有生效？
A: 检查以下几点：
1. 是否在人类审核阶段提交反馈？
2. `action` 字段是否设置为 `"regenerate"`？
3. `comments` 字段是否包含修改意见？
4. 查看 `user_modifications` 字段是否被正确设置

### Q: Stage 1生效了但Stage 2没有？
A: 这是修复前的问题。现在两个阶段都应该生效了。

### Q: 如何测试更复杂的修改意见？
A: 可以尝试：
- "请添加更多图表"
- "请使用商业风格而非学术风格"
- "请减少技术细节，增加直观解释"
- "请将页数控制在10页以内"

## 📞 需要帮助？

如果测试中发现问题，请提供：
1. 任务ID
2. 提交的修改意见内容
3. 期望结果 vs 实际结果
4. 执行日志（`execution_log`字段）
