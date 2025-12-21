# ScholarFlow 项目设计说明书

## 项目概述

ScholarFlow 是一个基于 LangGraph 的智能学术文献演示文稿生成系统，能够将 PDF 论文自动转换为专业的演示幻灯片。

## 文档目录

### 核心章节
1. **项目概述与背景** - 项目简介和核心价值
2. **系统架构总览** - 整体架构和组件关系
3. **技术栈与依赖** - 前后端技术栈
4. **LangGraph工作流设计** - 10节点工作流详解
5. **状态管理机制** - WorkflowState和状态流转
6. **数据存储与持久化** - SQLite + JSON双存储
7. **PDF解析模块** - MinerU集成
8. **文本分块与处理** - 分块算法
9. **LLM集成与调用** - 多提供商支持
10. **图片Token化保护** - 三阶段保护机制
11. **演示文稿渲染** - Marp引擎
12. **人机交互流程** - HITL机制
13. **API接口文档** - 所有API端点
14. **配置管理** - 环境变量
15. **部署与运维** - 部署和监控
16. **测试策略与覆盖** - 测试金字塔
17. **环境变量参考** - 完整清单
18. **故障排除指南** - 常见问题
19. **扩展开发指南** - 自定义开发

### 图表目录（50个）
- **架构类图表** - 系统架构、组件关系、部署架构
- **工作流图表** - LangGraph流程、节点详情、路由逻辑
- **数据流图表** - 状态持久化、Token化流程
- **API交互图表** - 调用时序、人机交互

### 代码示例（60个）
- **基础示例（20个）** - API调用、配置、工作流运行
- **进阶示例（25个）** - 自定义节点、批量处理、性能优化
- **高级示例（15个）** - 企业级应用、分布式架构

## 快速开始

1. 阅读第1-4章了解系统架构
2. 查看 `code-examples/basic/` 学习基础用法
3. 参考第14章配置API密钥
4. 按照第16章进行部署

## 核心特性

- ✅ 基于LangGraph的10阶段工作流
- ✅ 支持并行处理和人工审核
- ✅ 双存储机制（SQLite + JSON）
- ✅ 图片Token化保护
- ✅ 多LLM提供商支持（DeepSeek、Kimi、OpenAI）
- ✅ 完整的API和前端界面

## 文档结构

```
docs/
├── 01-20章.md                     # 20个章节文档
├── diagrams/                      # 50个图表
│   ├── architecture/              # 架构图
│   ├── workflow/                  # 工作流图
│   ├── dataflow/                  # 数据流图
│   └── api-interaction/           # API图
├── code-examples/                 # 60个示例
│   ├── basic/                     # 基础示例
│   ├── intermediate/              # 进阶示例
│   └── advanced/                  # 高级示例
└── assets/                        # 辅助文件
    ├── quick-reference.md
    ├── glossary.md
    └── changelog.md
```

## 技术栈

**后端**: Python 3.12+ / FastAPI / LangGraph
**前端**: React + TypeScript / Next.js
**PDF解析**: MinerU API
**渲染**: Marp CLI
**存储**: SQLite + JSON

## 联系方式

- 项目主页: https://github.com/your-org/ScholarFlow
- 问题反馈: GitHub Issues
