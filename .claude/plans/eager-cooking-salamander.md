# ScholarFlow 文档和代码清理计划

## 目标

删除或合并所有没有用的文档和代码，简化项目结构，保留核心功能文档。

## 分析结果

### 重复的文档文件

1. **Prompt 模板文件** (重复，需要删除一个)
   - ❌ `app/services/llm/prompts/Prompt 模板清单.md` (旧位置)
   - ✅ `langchain/Prompt模板清单.md` (新位置，用于新工作流)

2. **文档目录** (docs/ 目录有太多重复和过时的文档)
   - 📝 需要合并或删除的文档

### 过时/重复的文档

在 `docs/` 目录下：
1. `COMPLETION_SUMMARY.md` - 过时总结
2. `FINAL_IMPLEMENTATION_REPORT.md` - 旧实施报告
3. `IMPLEMENTATION_SUMMARY.md` - 旧实施总结
4. `LLM_REFACTOR_SUMMARY.md` - LLM 重构总结
5. `UNIFIED_LLM_README.md` - 统一 LLM 说明（已过时）
6. `QUICK_REFERENCE.md` - 快速参考（已过时）
7. `marp官方文档.md` - 外部文档引用
8. `marp调用.md` - 过时文档

### 保留的文档

1. `docs/LLM_CONFIGURATION.md` - LLM 配置说明（仍有用）
2. `docs/LOG_VIEWER_GUIDE.md` - 日志查看器指南（仍有用）
3. `docs/PROJECT_STRUCTURE.md` - 项目结构说明（仍有用）
4. `docs/USAGE.md` - 使用说明（仍有用）
5. 根目录的 `README.md` - 项目主说明
6. 根目录的 `CLAUDE.md` - Claude 指南
7. 根目录的 `QUICK_START_NEW_WORKFLOW.md` - 新工作流快速开始
8. 根目录的 `WORKFLOW_REFACTOR_GUIDE.md` - 新工作流详细指南

### 测试文件分析

保留的测试文件：
1. `tests/test_workflow_mock.py` - 新工作流 Mock 测试（推荐）
2. `tests/test_workflow.py` - 新工作流组件测试
3. `tests/test_new_pipeline.py` - 新 Pipeline 测试
4. `tests/view_logs.py` - 日志查看器工具
5. `tests/test_llm_config.py` - LLM 配置测试
6. `tests/test_pipeline.py` - 旧 Pipeline 测试（保留以兼容）

可删除的测试：
- `tests/test_split.py` - 旧分块测试（功能已集成到新工作流）

## 清理计划

### Phase 1: 删除重复文件

1. **删除重复的 Prompt 模板**
   ```bash
   rm app/services/llm/prompts/Prompt\ 模板清单.md
   ```
   理由：使用 langchain/Prompt模板清单.md（新工作流使用）

### Phase 2: 删除 docs/ 目录下的过时文档

```bash
# 删除过时的总结和报告
rm docs/COMPLETION_SUMMARY.md
rm docs/FINAL_IMPLEMENTATION_REPORT.md
rm docs/IMPLEMENTATION_SUMMARY.md
rm docs/LLM_REFACTOR_SUMMARY.md
rm docs/UNIFIED_LLM_README.md
rm docs/QUICK_REFERENCE.md

# 删除外部文档引用
rm docs/marp官方文档.md
rm docs/marp调用.md
```

### Phase 3: 删除重复的 Prompt 目录

如果 `app/services/llm/prompts/` 目录为空，则删除整个目录：
```bash
# 检查目录是否为空
# 如果为空则删除
rmdir app/services/llm/prompts/
rmdir app/services/llm/prompts/ 2>/dev/null || true
```

### Phase 4: 删除过时的测试文件

```bash
rm tests/test_split.py
```

### Phase 5: 创建统一的文档索引

创建一个 `DOCUMENTATION_INDEX.md` 文件，列出所有保留的文档及其说明。

### Phase 6: 清理临时测试数据

删除测试生成的临时数据（如果需要保留日志以供参考，可选择性保留）：
- 可选择性清理 `data/intermediates/test_*` 目录
- 可选择性清理 `data/logs/test_*` 目录

## 保留的核心文件结构

```
ScholarFlow/
├── README.md                           # 项目主说明
├── CLAUDE.md                          # Claude 指南
├── QUICK_START_NEW_WORKFLOW.md        # 新工作流快速开始
├── WORKFLOW_REFACTOR_GUIDE.md         # 新工作流详细指南
├── docs/
│   ├── LLM_CONFIGURATION.md           # LLM 配置
│   ├── LOG_VIEWER_GUIDE.md            # 日志查看器
│   ├── PROJECT_STRUCTURE.md           # 项目结构
│   └── USAGE.md                       # 使用说明
├── langchain/
│   ├── Prompt模板清单.md              # Prompt 模板（唯一）
│   ├── split.py                       # 分块组件
│   └── merge.py                       # 合并组件
├── app/services/
│   ├── prompt_manager.py              # Prompt 管理器
│   ├── workflow_orchestrator.py       # 工作流编排器
│   └── pipeline.py                    # Pipeline
├── tests/
│   ├── test_workflow_mock.py          # Mock 测试
│   ├── test_workflow.py               # 组件测试
│   ├── test_new_pipeline.py           # Pipeline 测试
│   ├── test_llm_config.py             # LLM 配置测试
│   ├── test_pipeline.py               # 旧 Pipeline 测试
│   └── view_logs.py                   # 日志查看器
└── data/logs/                         # 日志文件（保留有用的）
```

## 预期结果

1. **减少文档数量** - 从 15+ 个文档减少到 8 个核心文档
2. **消除重复** - 删除所有重复的文档和代码
3. **提高可维护性** - 清晰的文件结构
4. **保留功能** - 所有核心功能文档都保留

## 执行顺序

1. 备份重要文档（可选）
2. 执行 Phase 1-4（删除操作）
3. 创建文档索引
4. 验证所有功能正常
5. 更新文档引用（如有必要）
