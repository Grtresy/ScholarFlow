# 项目结构说明

按照你提供的标准结构，这里把当前仓库的目录树与职责做一一对应：

```
ScholarFlow/ (当前仓库 root)
├── app/                  # 核心应用代码包
│   ├── core/             # 配置与日志等基础设施
│   │   ├── config.py     # 读取 .env 环境变量并缓存 Settings
│   │   └── logger.py     # 简易 logging 配置函数
│   ├── api/              # FastAPI/Flask 接口层占位文件
│   │   ├── endpoints.py  # upload/generate/render 接口占位
│   │   └── models.py     # Chunk/Outline 数据类
│   ├── main.py           # CLI/demo 入口，串起 split + merge
│   └── services/         # 业务模块集合
│       ├── parser/       # 解析/图像上传相关（Shi）
│       │   ├── mineru_client.py  # MinerU 调用占位
│       │   └── oss_uploader.py   # 图片上传占位
│       ├── llm/          # LLM 相关逻辑（Yang）
│       │   ├── text_splitter.py   # 拆 chunk/合并逻辑（原 split.py）
│       │   ├── outline_merger.py  # 合并大纲（原 merge.py）
│       │   ├── provider.py         # DeepSeek/OpenAI 封装占位
│       │   └── prompts/           # Prompt 配置
│       │       ├── prompt_templates.py  # 读取 Prompt 模板
│       │       └── Prompt 模板清单.md  # Stage1/2 prompt 文本
│       └── renderer/      # Marp 渲染（Zhong）
│           ├── marp_engine.py     # 调用 Marp CLI
│           └── styles/           # 预置 CSS 主题
│               ├── academic.css
│               ├── business.css
│               └── scipop.css
├── data/                 # 本地数据暂存层
│   ├── inputs/           # 上传的 PDF 等原始输入
│   ├── intermediate/     # MinerU 输出 Markdown + 图片
│   └── outputs/          # 最终生成的 PPTX/PDF/HTML
├── tests/                # 单元测试入口
│   └── test_split.py     # 仅测试拆分 chunk 行为
├── docker-compose.yml    # 启动 MinerU 等服务的示例编排
├── requirements.txt      # Python 依赖列表（FastAPI/DeepSeek/OpenAI）
├── pyproject.toml        # Poetry/build 约定（可扩展）
├── README.md             # 项目总体说明与使用文档
├── uv.lock               # 依赖锁（由 Poetry）
└── .env.example          # 推荐的环境变量配置模板
```

附加说明：
- `app/main.py` 可作为一个简单的 "Orchestrator" 示例，先拆 chunk 再合并，可供 CLI 或后端调用。
- `app/services/llm/prompts` 目录保持原始 Prompt markdown，`prompt_templates.py` 负责读取并可封装为字典。
- `tests/` 当前只有覆盖 `text_splitter` 的 smoke test，后续可以扩展至 `outline_merger`、`renderer` 等模块。
- `data/` 目录是开发时的临时空间，可在 `.gitignore` 中添加具体文件（如 MinerU 输出）以避免提交。