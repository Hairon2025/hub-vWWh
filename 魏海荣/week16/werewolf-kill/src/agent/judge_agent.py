"""
裁判Agent模块

负责判定游戏规则、计算结果、推进游戏流程。
"""

from typing import List, Dict, Any, Optional

from agents import Agent, Runner
from agents import set_default_openai_api, set_tracing_disabled

from src.schemas.system_config import load_system_config

set_default_openai_api("chat_completions")
set_tracing_disabled(True)

config = load_system_config("config/system_config.json")


class JudgeAgent:
    """主持人AI代理（裁判）

    负责判定游戏规则、计算结果、推进游戏流程。
    """

    def __init__(self):
        instructions = """你是狼人杀游戏的主持人（裁判）。
你的职责是：
1. 按照游戏规则推进游戏流程
2. 收集并执行玩家的决策
3. 宣布每天的死亡结果
4. 判断游戏是否结束及胜利方

游戏流程：
1. 夜晚：依次执行狼人杀人、预言家查验、女巫用药
2. 白天：宣布死亡、公开辩论、投票处决

你必须输出JSON格式的游戏指令。
"""
        self.agent = Agent(
            name="Judge",
            model=config.default_model,
            instructions=instructions,
        )

    async def announce_death(
        self,
        deaths: List[str],
        cause: str,
        game_state: Optional[Dict[str, Any]] = None
    ) -> str:
        """宣布死亡结果

        Args:
            deaths: 死亡玩家ID列表
            cause: 死亡原因（night_kill, vote, shoot, poison）
            game_state: 游戏状态（可选）

        Returns:
            死亡公告文本
        """
        if not deaths:
            return "今晚无人死亡。"

        death_names = [f"玩家{p}" for p in deaths]
        cause_desc = {
            "night_kill": "昨夜",
            "vote": "投票",
            "shoot": "枪杀",
            "poison": "毒杀",
        }.get(cause, cause)

        announcement = f"{cause_desc}，以下玩家死亡：{', '.join(death_names)}"

        # 如果提供了 game_state，添加死亡玩家遗言
        if game_state:
            for player_id in deaths:
                player = game_state.get("players", {}).get(player_id)
                if player:
                    announcement += f"\n{player.get('name', f'玩家{player_id}')} 说："

        return announcement

    async def announce_phase(self, phase: str, day_number: int) -> str:
        """宣布游戏阶段

        Args:
            phase: 当前阶段 (night/day)
            day_number: 第几天

        Returns:
            阶段公告文本
        """
        if "night" in phase.lower():
            return f"第{day_number}夜开始，请各位保持安静。"
        else:
            return f"第{day_number}天，阳光照耀，请各位玩家开始发言。"

    async def judge_win_condition(
        self,
        alive_players: List[str],
        werewolf_count: int,
        village_count: int
    ) -> Dict[str, Any]:
        """判断胜利条件

        Args:
            alive_players: 存活玩家ID列表
            werewolf_count: 存活狼人数量
            village_count: 存活好人数量

        Returns:
            包含 winner 和 is_game_over 的字典
        """
        # 狼人胜利条件：消灭所有好人（只剩狼人或狼人赢）
        if werewolf_count >= village_count:
            return {
                "winner": "werewolf",
                "is_game_over": True,
                "reason": "狼人阵营胜利"
            }

        # 好人胜利条件：消灭所有狼人
        if werewolf_count == 0:
            return {
                "winner": "village",
                "is_game_over": True,
                "reason": "好人阵营胜利"
            }

        # 游戏继续
        return {
            "winner": None,
            "is_game_over": False,
            "reason": None
        }

    async def call_llm(self, prompt: str) -> Dict[str, Any]:
        """调用 LLM 获取裁判决策

        Args:
            prompt: 输入提示词

        Returns:
            LLM 返回的决策字典
        """
        import json
        try:
            output = await Runner.run(self.agent, prompt)
            response_text = output.output_text

            # 尝试解析 JSON
            json_str = response_text
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()

            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"action": "continue", "reasoning": "解析失败，继续游戏"}
        except Exception as e:
            return {"action": "continue", "reasoning": f"LLM调用失败: {str(e)}"}
