"""
调试端点，用于可视化工作流状态和进度。
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
import json
import os
from datetime import datetime

# 创建路由
router = APIRouter(prefix="/debug", tags=["debug"])

# 检查点存储路径
CHECKPOINT_DIR = "data/checkpoints"


@router.get("/dashboard", response_class=HTMLResponse)
async def debug_dashboard():
    """显示调试仪表板"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ScholarFlow Debug Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .status { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold; }
            .status-running { background: #e3f2fd; color: #1976d2; }
            .status-completed { background: #e8f5e9; color: #388e3c; }
            .status-error { background: #ffebee; color: #d32f2f; }
            .status-pending { background: #fff3e0; color: #f57c00; }
            pre { background: #f5f5f5; padding: 15px; border-radius: 4px; overflow-x: auto; font-size: 12px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .refresh-btn { background: #667eea; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
            .refresh-btn:hover { background: #5568d3; }
        </style>
        <script>
            function refreshDashboard() {
                window.location.reload();
            }
            setInterval(refreshDashboard, 5000); // 每5秒自动刷新
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔍 ScholarFlow Debug Dashboard</h1>
                <p>实时监控工作流状态和进度</p>
                <button class="refresh-btn" onclick="refreshDashboard()">🔄 刷新</button>
            </div>

            <div class="card">
                <h2>📊 服务器状态</h2>
                <div class="grid">
                    <div>
                        <h3>FastAPI 服务器</h3>
                        <p><strong>状态:</strong> <span class="status status-running">运行中</span></p>
                        <p><strong>端口:</strong> 8000</p>
                        <p><strong>URL:</strong> <a href="http://localhost:8000" target="_blank">http://localhost:8000</a></p>
                    </div>
                    <div>
                        <h3>React 前端</h3>
                        <p><strong>状态:</strong> <span class="status status-running">运行中</span></p>
                        <p><strong>端口:</strong> 5173</p>
                        <p><strong>URL:</strong> <a href="http://localhost:5173" target="_blank">http://localhost:5173</a></p>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>🔧 API 端点</h2>
                <ul>
                    <li><strong>健康检查:</strong> <a href="/health" target="_blank">/health</a></li>
                    <li><strong>API 文档:</strong> <a href="/docs" target="_blank">/docs</a></li>
                    <li><strong>上传 PDF:</strong> POST /api/upload</li>
                    <li><strong>下载结果:</strong> GET /api/download/{task_id}</li>
                    <li><strong>创建任务:</strong> POST /api/v2/tasks</li>
                    <li><strong>任务状态:</strong> GET /api/v2/tasks/{task_id}/status</li>
                    <li><strong>任务结果:</strong> GET /api/v2/tasks/{task_id}/result</li>
                </ul>
            </div>

            <div class="card">
                <h2>📁 工作流文件</h2>
                <p><strong>工作流定义:</strong> app/graph/workflow.py</p>
                <p><strong>状态管理:</strong> app/graph/state.py</p>
                <p><strong>节点实现:</strong> app/graph/nodes/</p>
                <p><strong>检查点存储:</strong> data/checkpoints/</p>
            </div>

            <div class="card">
                <h2>🚀 使用说明</h2>
                <ol>
                    <li>访问 <a href="http://localhost:5173" target="_blank">前端应用</a> 上传 PDF 文件</li>
                    <li>选择演示文稿样式和配置</li>
                    <li>监控工作流进度（步骤 1-10）</li>
                    <li>在需要时进行人工审查</li>
                    <li>下载生成的演示文稿</li>
                </ol>
            </div>

            <div class="card">
                <h2>⚙️ 工作流步骤</h2>
                <ol>
                    <li><strong>初始化</strong> - 创建工作流线程和初始状态</li>
                    <li><strong>解析 PDF</strong> - 提取 PDF 内容</li>
                    <li><strong>分块内容</strong> - 将内容分割为可处理的块</li>
                    <li><strong>阶段 1 处理</strong> - 生成初始大纲</li>
                    <li><strong>合并大纲</strong> - 整合多个大纲</li>
                    <li><strong>人工审查</strong> - 等待用户批准/拒绝</li>
                    <li><strong>阶段 2 处理</strong> - 转换为 Marp 格式</li>
                    <li><strong>渲染</strong> - 生成最终演示文稿</li>
                    <li><strong>完成</strong> - 工作流完成</li>
                </ol>
            </div>

            <div class="card">
                <h2>🐛 调试信息</h2>
                <p><strong>更新时间:</strong> """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
                <p><strong>环境:</strong> 开发环境</p>
                <p><strong>版本:</strong> v2.0.0</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/status")
async def debug_status():
    """返回调试状态信息"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "fastapi": {
                "status": "running",
                "port": 8000,
                "url": "http://localhost:8000"
            },
            "frontend": {
                "status": "running",
                "port": 5173,
                "url": "http://localhost:5173"
            }
        },
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "upload": "POST /api/upload",
            "download": "GET /api/download/{task_id}",
            "create_task": "POST /api/v2/tasks",
            "get_status": "GET /api/v2/tasks/{task_id}/status",
            "get_result": "GET /api/v2/tasks/{task_id}/result"
        },
        "workflow": {
            "definition": "app/graph/workflow.py",
            "state": "app/graph/state.py",
            "nodes": "app/graph/nodes/",
            "checkpoints": "data/checkpoints/"
        }
    }


@router.get("/workflow-graph", response_class=HTMLResponse)
async def workflow_graph():
    """显示工作流程图"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ScholarFlow 工作流程图</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1400px; margin: 0 auto; }
            .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .flowchart { display: flex; flex-direction: column; align-items: center; gap: 20px; }
            .step { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 25px; border-radius: 8px; min-width: 200px; text-align: center; font-weight: bold; }
            .arrow { font-size: 24px; color: #667eea; }
            .branch { display: flex; gap: 20px; justify-content: center; }
            .branch-step { background: #48bb78; color: white; padding: 10px 20px; border-radius: 6px; min-width: 150px; text-align: center; }
            .loop { border: 2px dashed #667eea; padding: 20px; border-radius: 8px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1>🔄 ScholarFlow 工作流程图</h1>
                <p>学术论文到演示文稿的完整转换流程</p>
            </div>

            <div class="card">
                <div class="flowchart">
                    <div class="step">🚀 开始工作流</div>
                    <div class="arrow">↓</div>
                    <div class="step">📄 初始化 (Initialization)</div>
                    <div class="arrow">↓</div>
                    <div class="step">📑 解析 PDF (Parse PDF)</div>
                    <div class="arrow">↓</div>
                    <div class="step">✂️ 分块内容 (Split Markdown)</div>
                    <div class="arrow">↓</div>

                    <div class="loop">
                        <div class="step">🔄 阶段 1 处理 (Stage 1 Process)</div>
                        <div class="arrow">↓</div>
                        <div class="step">🔀 合并大纲 (Merge Outlines)</div>
                        <div class="arrow">↓</div>
                        <div class="branch">
                            <div class="branch-step">✅ 人工审查 (Human Review)</div>
                        </div>
                        <div class="arrow">↓</div>
                        <div class="step">📝 阶段 2 处理 (Stage 2 Process)</div>
                        <div class="arrow">↓</div>
                        <div class="step">🎨 渲染 (Render)</div>
                        <div class="arrow">↓</div>
                        <div class="step">✅ 工作流完成</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>🔍 详细说明</h2>
                <ul>
                    <li><strong>初始化:</strong> 创建工作流线程和初始状态，设置任务 ID 和配置</li>
                    <li><strong>解析 PDF:</strong> 使用 MinerU 从 PDF 提取 Markdown 内容和图片</li>
                    <li><strong>分块内容:</strong> 将长文档分割为可管理的块，便于 LLM 处理</li>
                    <li><strong>阶段 1 处理:</strong> 使用 DeepSeek LLM 为每个块生成演示大纲</li>
                    <li><strong>合并大纲:</strong> 将多个块的大纲合并为连贯的演示结构</li>
                    <li><strong>人工审查:</strong> 暂停工作流，等待用户批准或拒绝大纲</li>
                    <li><strong>阶段 2 处理:</strong> 将大纲转换为 Marp Markdown 格式</li>
                    <li><strong>渲染:</strong> 使用 Marp CLI 生成最终的 PPTX/HTML/PDF 演示文稿</li>
                </ul>
            </div>

            <div class="card">
                <h2>💡 关键特性</h2>
                <ul>
                    <li>✅ <strong>人机交互:</strong> 支持在关键点暂停工作流进行人工审查</li>
                    <li>✅ <strong>实时状态:</strong> 通过 WebSocket/SSE 提供实时进度更新</li>
                    <li>✅ <strong>状态持久化:</strong> 使用 Checkpointer 保存工作流状态</li>
                    <li>✅ <strong>错误处理:</strong> 完善的错误捕获和恢复机制</li>
                    <li>✅ <strong>多种样式:</strong> 支持学术、大众科学、商业推介三种演示风格</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
