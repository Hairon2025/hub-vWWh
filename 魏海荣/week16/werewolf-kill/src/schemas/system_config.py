import os
from pydantic import BaseModel, Field, model_validator

class SystemConfig(BaseModel):
    """LLM配置"""
    base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1", description="模型服务地址")
    api_key: str = Field(default="", description="模型服务API Key")
    default_model: str = Field(default="qwen-flash", description="默认使用的模型")

    @model_validator(mode="after")
    def after_load_hook(self) -> "SystemConfig":
        """加载后钩子，自动从环境变量覆盖配置"""
        env_key = os.environ.get("DASHSCOPE_API_KEY")

        if env_key:
            self.api_key = env_key 
        env_base_url = os.getenv("OPENAI_BASE_URL")
        if env_base_url:
            self.base_url = env_base_url
        # 将 key 注入环境变量供 SDK 使用
        os.environ["OPENAI_API_KEY"] = self.api_key
        os.environ["OPENAI_BASE_URL"] = self.base_url
        return self
    
def load_system_config(file_path: str) -> SystemConfig:
    """加载系统配置，优先从环境变量获取"""
    with open(file_path, "r", encoding="utf-8") as f:
        json_data = f.read()
    
    return SystemConfig.model_validate_json(json_data)