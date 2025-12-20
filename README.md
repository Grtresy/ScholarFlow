# 研绎——基于MinerU与大模型的智能学术文献演示生成Agent专题研究小组方案

**Team Members**: Shi Shangkun, Yang Jinyu, Zhong Xingyu

## 1. 选题方向与背景介绍

### 1.1 选题方向

智能体（Agent）实现：构建一个自动化工作流Agent，能够接收PDF格式的学术文献，通过多模态解析、语义理解与重构，最终自动输出高质量、可编辑的演示文稿（Slide Deck）。

### 1.2 背景与动机

在科研与工作中，快速阅读文献并进行汇报是高频需求。然而，传统的流程存在以下痛点：

- **PDF解析困难**：学术文献包含大量复杂的双栏排版、数学公式和图表，传统的PDF转Word/Text工具往往丢失结构信息，导致乱码。

- **转换效率低下**：从阅读理解到制作PPT需要大量的人工复制、粘贴和排版时间。

- **排版审美门槛**：制作美观的PPT需要设计能力，而基于Markdown的Marp工具虽然方便，但缺乏针对学术场景的自动化生成模板。

本项目旨在利用MinerU强大的PDF解析能力提取精准内容，结合DeepSeek大模型的逻辑总结能力，以及Marp的代码化排版优势，打造一个“读-写-画”一体化的智能演示生成Agent。

## 2. 拟解决的子任务与技术路线

我们将整个项目拆解为三个核心子任务：

### 任务一：高保真文档解析与多模态数据清洗

**目标**：将非结构化的PDF转换为机器可读的结构化数据（Markdown），并保留图片和公式。

**技术方案**：

- 使用MinerU (Magic-PDF)作为核心解析引擎，处理复杂的学术排版。

- 对象存储集成：鉴于MinerU提取的图片需要被大模型和前端引用，我们将搭建/接入对象存储服务（如OSS/S3），在解析过程中自动将图片上传云端，并在文本中替换为持久化URL链接。

### 任务二：基于Human-in-the-loop的内容重构工作流

**目标**：利用大模型生成符合演讲逻辑的幻灯片大纲及内容，并允许用户中途干预。

**技术方案**：

- Prompt Engineering：针对DeepSeek设计多套提示词模板（如“学术汇报风”、“科普简介风”、“商业路演风”）。

- HITL (人机回环)机制：设计中间态接口，Agent在生成大纲后暂停，允许用户手动调整重点章节，再继续生成详细Slide内容，确保准确性。

### 任务三：基于CSS的动态样式渲染与输出

**目标**：将大模型生成的Markdown文本渲染为美观的演示文稿。

**技术方案**：

- 放弃传统的PPTX模板，深入研究Marp (Markdown Presentation Ecosystem)。

- 编写定制化的CSS层叠样式表，设计适合学术展示的主题（字体、间距、代码高亮、公式渲染），实现“内容与样式分离”的自动化渲染。

## 3. 预估难点与挑战

- **跨模态上下文的一致性**：MinerU提取的图片（Figure/Table）需要准确对应到Slide的具体页面中，大模型容易产生幻觉（引用错误的图片链接）。

- **长文本的Token限制与逻辑压缩**：一篇几十页的论文浓缩为10-15页PPT，如何保证核心论点不丢失且逻辑连贯是Prompt调优的难点。

- **自动化工作流的稳定性**：将本地手动流程（PDF -> MinerU -> Upload -> LLM -> Marp）转化为自动化Pipeline时，需要处理API超时、格式校验等异常情况。

- **Marp的样式局限性**：Marp基于CSS，虽然灵活但在复杂动画和自由布局上不如传统PPT，需要通过高阶CSS技巧进行弥补。

## 4. 小组分工

### 史尚坤（全栈与工作流架构）

**负责模块**：任务一（解析与存储）及整体Pipeline搭建。

**具体工作**：

- 部署MinerU（本地或API对接）。

- 实现图片自动上传对象存储的脚本。

- 搭建后端服务，串联“解析-生成-渲染”全流程，实现Human-in-the-loop的交互接口。

### 杨谨毓（大模型与提示词工程）

**负责模块**：任务二（LLM逻辑核心）。

**具体工作**：

- 对DeepSeek模型进行Prompt调试，设计“学术/商业”不同风格的System Prompt。

- 解决长文本输入的上下文窗口问题（分块处理或摘要链）。

- 优化Slide的内容结构，确保生成的Markdown语法严格符合Marp要求。

### 仲星宇（前端渲染与视觉设计）

**负责模块**：任务三（Marp样式与最终呈现）。

**具体工作**：

- 研究Marp生态，编写2-3套高质量的CSS样式模板（Theme）。

- 设计最终的输出格式，确保数学公式（LaTeX）和图片在Slide中完美显示。

- 协助测试，提供人工反馈以优化Prompt的生成质量。

## 5. 参考资料

- MinerU (PDF解析): [https://github.com/opendatalab/MinerU](https://github.com/opendatalab/MinerU)

- DeepSeek API Docs: [https://platform.deepseek.com/](https://platform.deepseek.com/)

- Marp (Markdown Presentation): [https://marp.app/](https://marp.app/)

- CSS for Marp: [https://github.com/orgs/marp-team/discussions](https://github.com/orgs/marp-team/discussions) (社区样式参考)

> （注：文档部分内容由 AI 生成）
