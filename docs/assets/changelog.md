# ScholarFlow 更新日志

本文档记录了 ScholarFlow 项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/) 规范。

## [未发布]

### 计划中
- 分布式工作流支持
- 多租户架构
- Kubernetes 部署方案
- WebSocket 实时推送

## [1.0.0] - 2025-12-21

### 新增
- ✨ 初始版本发布
- 📚 完整的文档系统（20章设计说明书）
- 🔄 基于 LangGraph 的 10 阶段工作流
- 📄 PDF 解析支持（MinerU 集成）
- 🧠 多 LLM 提供商支持（DeepSeek、Kimi、OpenAI）
- 🖼️ 图片 Token 化保护机制
- 👥 人机协作审核（Human-in-the-Loop）
- 🎨 演示文稿渲染（Marp CLI）
- 📡 完整的 REST API
- 🌐 React + TypeScript 前端
- 💾 SQLite + JSON 双存储架构
- 🔄 状态持久化和断点续传
- ⚡ 异步处理和并行优化
- 📊 实时进度监控
- 🔐 配置管理和环境变量
- 🐳 容器化部署支持
- 🧪 完整的测试覆盖

### 文档
- 📖 项目概述与背景（第1章）
- 🏗️ 系统架构总览（第2章）
- 🔧 技术栈与依赖（第3章）
- 📖 核心概念与术语（第4章）
- 🔄 LangGraph 工作流设计（第5章）
- 📦 状态管理机制（第6章）
- 💾 数据存储与持久化（第7章）
- 📄 PDF 解析模块（第8章）
- ✂️ 文本分块与处理（第9章）
- 🧠 LLM 集成与调用（第10章）
- 🖼️ 图片 Token 化保护（第11章）
- 🎨 演示文稿渲染（第12章）
- 👥 人机交互流程（第13章）
- 📡 API 接口文档（第14章）
- ⚙️ 配置管理（第15章）
- 🚀 部署与运维（第16章）
- 🧪 测试策略与覆盖（第17章）
- 🔑 环境变量参考（第18章）
- 🐛 故障排除指南（第19章）
- 🔧 扩展开发指南（第20章）

### 图表
- 📊 50+ 个 Mermaid 图表
  - 系统架构图
  - 组件关系图
  - 工作流流程图
  - 条件路由图
  - 数据流图
  - API 交互图

### 代码示例
- 💻 60+ 个可运行示例
  - 20 个基础示例
  - 25 个进阶示例
  - 15 个高级示例

### 示例
- 🚀 基础 API 调用
- ⚙️ 配置管理
- 🔄 工作流运行
- 📤 文件上传
- 📊 任务状态查询
- 🔧 自定义节点开发
- 📦 批量处理
- 🛡️ 错误处理最佳实践

### 辅助文件
- 📚 快速参考指南
- 📖 术语表
- 📝 更新日志

## 技术架构

### 后端
- **语言**: Python 3.12+
- **Web 框架**: FastAPI
- **工作流引擎**: LangGraph
- **数据库**: SQLite
- **异步支持**: asyncio
- **包管理**: uv

### 前端
- **框架**: React 18
- **语言**: TypeScript
- **应用框架**: Next.js 14
- **样式**: Tailwind CSS
- **UI 组件**: Shadcn/ui

### 外部服务
- **PDF 解析**: MinerU API
- **LLM 提供商**: DeepSeek、Kimi、OpenAI
- **渲染引擎**: Marp CLI

### 存储
- **主存储**: SQLite（LangGraph Checkpoint）
- **辅助存储**: JSON 文件
- **文件存储**: 本地文件系统

## 性能指标

- **处理速度**: 1-3 分钟完成中等长度论文
- **并发支持**: 5-10 个并行任务
- **内存使用**: < 512MB（正常负载）
- **磁盘空间**: 100MB（应用）+ 1GB（数据）

## 兼容性

### Python 版本
- **最低版本**: Python 3.12
- **推荐版本**: Python 3.12+
- **不支持**: Python 3.11 及以下

### 浏览器支持
- Chrome >= 90
- Firefox >= 88
- Safari >= 14
- Edge >= 90

### 操作系统
- Linux (Ubuntu 20.04+, CentOS 8+)
- macOS (10.15+)
- Windows 10+

## 依赖项

### 主要依赖
- langgraph >= 1.0.0
- fastapi >= 0.100.0
- langchain-openai >= 1.1.0
- aiosqlite >= 0.20.0
- pydantic >= 2.0.0

### 开发依赖
- pytest >= 7.0.0
- black >= 23.0.0
- mypy >= 1.0.0
- pylint >= 2.0.0

## 致谢

感谢以下项目和社区的支持：
- [LangGraph](https://langchain-ai.github.io/langgraph/) - 工作流编排框架
- [LangChain](https://python.langchain.com/) - LLM 应用开发框架
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [React](https://react.dev/) - 用户界面库
- [Marp](https://marp.top/) - Markdown 演示文稿工具
- [MinerU](https://mineru.net/) - PDF 解析服务
- [DeepSeek](https://platform.deepseek.com/) - LLM 提供商

## 贡献者

- ScholarFlow 开发团队
- 所有提交 Issue 和 PR 的贡献者
- 测试和反馈的用户

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](../LICENSE) 文件了解详情。

## 路线图

### v1.1.0（计划中）
- [ ] WebSocket 实时推送
- [ ] 自定义主题支持
- [ ] 批量任务管理
- [ ] 任务模板功能

### v1.2.0（计划中）
- [ ] 分布式工作流
- [ ] 多租户支持
- [ ] 云存储集成
- [ ] 高级监控面板

### v2.0.0（长期规划）
- [ ] 微服务架构
- [ ] Kubernetes 原生支持
- [ ] 多云部署
- [ ] 企业级功能

---

**注意**: 本项目的开发正在积极进行中，功能和特性可能会发生变化。建议关注 GitHub Releases 以获取最新更新。
