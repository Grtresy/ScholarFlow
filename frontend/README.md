# ScholarFlow Frontend

这是 ScholarFlow 的前端界面，基于 Next.js 14, Tailwind CSS 和 Shadcn UI 构建。

## 快速开始

### 1. 安装依赖
\`\`\`bash
npm install
\`\`\`

### 2. 配置环境变量
在 \`frontend\` 目录下创建 \`.env.local\` 文件：
\`\`\`env
NEXT_PUBLIC_API_URL=http://localhost:8000
\`\`\`

### 3. 启动开发服务器
\`\`\`bash
npm run dev
\`\`\`

## 核心功能
- **PDF 上传**：支持拖拽上传论文。
- **实时进度**：轮询后端 API 展示工作流执行状态。
- **人工审核**：在生成幻灯片前，支持在线编辑和批准大纲。
- **结果下载**：任务完成后可直接下载生成的 PPTX/PDF 文件。
