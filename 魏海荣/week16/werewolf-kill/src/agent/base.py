from agents import Agent, Runner, set_default_openai_api, set_tracing_disabled
from src.schemas.system_config import load_system_config

set_default_openai_api("chat_completions")
set_tracing_disabled(True)

config = load_system_config("config/system_config.json")


class BaseAgent:
    """
    基础角色代理类

    所有具体角色代理都继承此类，提供通用功能和接口。
    """

    def __init__(self):
        self.agent = Agent(
            name="",
            model=config.default_model,
            instructions="你好",
        )
    
    async def run(self, input: str):
        """
        运行代理，处理输入并返回输出

        Args:
            input: 输入字符串，通常是游戏状态描述或行动请求

        Returns:
            输出字符串，通常是角色的行动决策或信息反馈
        """
        output = await Runner.run(self.agent, input)
        return output