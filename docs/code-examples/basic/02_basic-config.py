#!/usr/bin/env python3
"""
基础示例 02: 基本配置设置
学习如何配置和加载 ScholarFlow 的设置
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from dataclasses import dataclass


# 示例 1: 使用环境变量
def load_env_config():
    """从环境变量加载配置"""
    config = {
        "LLM_API_KEY": os.getenv("LLM_API_KEY", ""),
        "LLM_BASE_URL": os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
        "LLM_MODEL": os.getenv("LLM_MODEL", "deepseek-chat"),
        "MINERU_API_KEY": os.getenv("MINERU_API_KEY", ""),
        "FASTAPI_HOST": os.getenv("FASTAPI_HOST", "0.0.0.0"),
        "FASTAPI_PORT": int(os.getenv("FASTAPI_PORT", "8000")),
        "DATA_DIR": os.getenv("DATA_DIR", "data"),
    }

    print("🔧 从环境变量加载配置:")
    for key, value in config.items():
        # 隐藏敏感信息
        display_value = value[:10] + "..." if len(str(value)) > 10 and "KEY" in key else value
        print(f"  {key}: {display_value}")

    return config


# 示例 2: 使用 Pydantic 模型
class Settings(BaseModel):
    """使用 Pydantic 定义配置模型"""
    # LLM 配置
    llm_api_key: str = Field(..., description="LLM API 密钥")
    llm_base_url: str = Field(default="https://api.deepseek.com", description="LLM 基础 URL")
    llm_model: str = Field(default="deepseek-chat", description="LLM 模型名称")
    llm_max_tokens: int = Field(default=4000, description="最大 token 数")
    llm_temperature: float = Field(default=0.7, description="温度参数")

    # MinerU 配置
    mineru_api_key: str = Field(..., description="MinerU API 密钥")
    mineru_endpoint: str = Field(default="https://api.opendatalab.org.cn", description="MinerU 端点")

    # 服务器配置
    fastapi_host: str = Field(default="0.0.0.0", description="FastAPI 主机")
    fastapi_port: int = Field(default=8000, description="FastAPI 端口")
    langgraph_host: str = Field(default="0.0.0.0", description="LangGraph 主机")
    langgraph_port: int = Field(default=8123, description="LangGraph 端口")

    # 存储配置
    data_dir: Path = Field(default=Path("data"), description="数据目录")
    storage_backend: str = Field(default="local", description="存储后端")

    # 调试配置
    debug: bool = Field(default=False, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def load_pydantic_config():
    """使用 Pydantic 加载配置"""
    try:
        settings = Settings()
        print("\n✅ Pydantic 配置加载成功:")
        print(f"  LLM 模型: {settings.llm_model}")
        print(f"  FastAPI 端口: {settings.fastapi_port}")
        print(f"  数据目录: {settings.data_dir}")
        return settings
    except Exception as e:
        print(f"\n❌ 配置加载失败: {e}")
        print("请检查 .env 文件或环境变量")
        return None


# 示例 3: 使用数据类
@dataclass
class WorkflowConfig:
    """工作流配置"""
    # 工作流参数
    max_chars: int = 6000
    target_chunks: int = 6
    max_retries: int = 3
    chunk_overlap: int = 200

    # 演示风格
    presentation_style: str = "academic"  # academic, popular, business

    # 处理选项
    enable_human_review: bool = True
    enable_parallel_processing: bool = True
    max_parallel_chunks: int = 5

    # 输出选项
    output_format: str = "pptx"  # pptx, pdf, html
    output_dir: str = "outputs"

    def __post_init__(self):
        """验证配置"""
        valid_styles = ["academic", "popular", "business"]
        if self.presentation_style not in valid_styles:
            raise ValueError(f"无效的演示风格: {self.presentation_style}")

        valid_formats = ["pptx", "pdf", "html"]
        if self.output_format not in valid_formats:
            raise ValueError(f"无效的输出格式: {self.output_format}")


def load_workflow_config():
    """加载工作流配置"""
    config = WorkflowConfig()
    print("\n⚙️  工作流配置:")
    print(f"  演示风格: {config.presentation_style}")
    print(f"  最大字符数: {config.max_chars}")
    print(f"  目标分块数: {config.target_chunks}")
    print(f"  输出格式: {config.output_format}")
    print(f"  人工审核: {'✅' if config.enable_human_review else '❌'}")
    print(f"  并行处理: {'✅' if config.enable_parallel_processing else '❌'}")
    return config


# 示例 4: 配置文件管理
class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

    def save_config(self, name: str, config: dict):
        """保存配置到文件"""
        config_path = self.config_dir / f"{name}.json"

        import json
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"✅ 配置已保存到: {config_path}")

    def load_config(self, name: str) -> Optional[dict]:
        """从文件加载配置"""
        config_path = self.config_dir / f"{name}.json"

        if not config_path.exists():
            print(f"⚠️  配置文件不存在: {config_path}")
            return None

        import json
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"✅ 配置已加载: {config_path}")
            return config
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
            return None

    def list_configs(self):
        """列出所有配置文件"""
        configs = list(self.config_dir.glob("*.json"))
        if configs:
            print(f"\n📋 现有配置文件 ({len(configs)} 个):")
            for config in configs:
                print(f"  - {config.name}")
        else:
            print("\n📋 没有找到配置文件")
        return configs


def create_sample_configs():
    """创建示例配置文件"""
    manager = ConfigManager()

    # 示例配置 1: 开发环境
    dev_config = {
        "name": "development",
        "description": "开发环境配置",
        "settings": {
            "debug": True,
            "log_level": "DEBUG",
            "fastapi_port": 8000,
        },
        "llm": {
            "model": "deepseek-chat",
            "temperature": 0.7,
        }
    }
    manager.save_config("development", dev_config)

    # 示例配置 2: 生产环境
    prod_config = {
        "name": "production",
        "description": "生产环境配置",
        "settings": {
            "debug": False,
            "log_level": "WARNING",
            "fastapi_port": 80,
        },
        "llm": {
            "model": "deepseek-chat",
            "temperature": 0.5,
        }
    }
    manager.save_config("production", prod_config)

    # 示例配置 3: 测试环境
    test_config = {
        "name": "testing",
        "description": "测试环境配置",
        "settings": {
            "debug": True,
            "log_level": "INFO",
            "fastapi_port": 8001,
        },
        "llm": {
            "model": "deepseek-chat",
            "temperature": 0.3,
        }
    }
    manager.save_config("testing", test_config)


# 示例 5: 配置验证
def validate_config(config: dict) -> bool:
    """验证配置是否有效"""
    required_keys = [
        "LLM_API_KEY",
        "MINERU_API_KEY",
    ]

    missing_keys = [key for key in required_keys if not config.get(key)]

    if missing_keys:
        print("\n❌ 配置验证失败:")
        print(f"  缺少必需的配置项: {', '.join(missing_keys)}")
        return False

    print("\n✅ 配置验证通过")
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("⚙️  ScholarFlow 配置管理示例")
    print("=" * 60)

    # 示例 1: 环境变量配置
    print("\n" + "=" * 60)
    print("📋 示例 1: 环境变量配置")
    print("=" * 60)
    env_config = load_env_config()
    validate_config(env_config)

    # 示例 2: Pydantic 模型
    print("\n" + "=" * 60)
    print("📋 示例 2: Pydantic 模型配置")
    print("=" * 60)
    pydantic_config = load_pydantic_config()

    # 示例 3: 数据类配置
    print("\n" + "=" * 60)
    print("📋 示例 3: 工作流配置")
    print("=" * 60)
    workflow_config = load_workflow_config()

    # 示例 4: 配置文件管理
    print("\n" + "=" * 60)
    print("📋 示例 4: 配置文件管理")
    print("=" * 60)
    create_sample_configs()

    config_manager = ConfigManager()
    config_manager.list_configs()

    # 加载一个配置文件
    dev_config = config_manager.load_config("development")
    if dev_config:
        print(f"\n📖 开发环境配置详情:")
        print(f"  调试模式: {dev_config['settings']['debug']}")
        print(f"  日志级别: {dev_config['settings']['log_level']}")
        print(f"  LLM 模型: {dev_config['llm']['model']}")

    # 示例 5: 配置验证
    print("\n" + "=" * 60)
    print("🔍 示例 5: 配置验证")
    print("=" * 60)

    # 测试有效配置
    valid_config = {
        "LLM_API_KEY": "sk-xxx",
        "MINERU_API_KEY": "xxx",
    }
    validate_config(valid_config)

    # 测试无效配置
    invalid_config = {
        "LLM_API_KEY": "sk-xxx",
        # 缺少 MINERU_API_KEY
    }
    validate_config(invalid_config)

    print("\n" + "=" * 60)
    print("✨ 配置示例完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()


"""
💡 学习要点:

1. 配置加载方式
   - 环境变量: 最灵活，支持容器化
   - Pydantic 模型: 类型安全，自动验证
   - 数据类: Pythonic，简单直接
   - 配置文件: 持久化，易于管理

2. 配置优先级
   - 显式传入参数
   - 环境变量
   - 配置文件
   - 默认值

3. 配置验证
   - 必需字段检查
   - 类型验证
   - 业务规则验证

4. 敏感信息处理
   - 不在日志中打印密钥
   - 支持从环境变量加载
   - 配置文件权限控制

📝 最佳实践:

1. 使用环境变量存储敏感信息
2. 为不同环境创建不同配置
3. 配置默认值，提供灵活性
4. 验证配置有效性
5. 记录配置加载过程

🔗 相关文档:

- Pydantic: https://docs.pydantic.dev/
- Python 环境变量: https://docs.python.org/3/library/os.html#os.getenv
"""
