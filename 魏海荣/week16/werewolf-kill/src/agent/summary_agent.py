"""
Summary Agent 模块

对局结束后，第一视角总结经验并保存到对应角色的经验库中。
使用工厂模式，根据角色类型构建不同的总结提示词。

核心方法：
- summarize(): 根据对局记录生成经验总结
- _build_summary_prompt(): 构建角色特定的总结提示词
"""

import json
from typing import Optional, Dict, Any, List

from agents import Agent, Runner, set_default_openai_api, set_tracing_disabled
from src.schemas.system_config import load_system_config
from src.memory.experience import ExperienceEntry, get_experience_manager

set_default_openai_api("chat_completions")
set_tracing_disabled(True)
config = load_system_config("config/system_config.json")


class SummaryAgent:
    """
    Summary Agent 工厂类

    负责创建和管理不同角色的经验总结 Agent 实例。
    每个 SummaryAgent 绑定一个角色类型，生成对应的 AI 总结提示词。

    使用方式：
        agent = SummaryAgent.create("werewolf")
        experience = await agent.summarize(game_record)
    """

    # 角色总结提示词模板
    ROLE_SUMMARY_TEMPLATES: Dict[str, Dict[str, str]] = {
        "werewolf": {
            "role_intro": """你是狼人杀游戏中的一只狼人。你的任务是回顾整场对局，以第一视角总结经验教训。

狼人的胜利条件：消灭所有好人（或好人数量<=狼人数量）
狼人的核心玩法：
- 夜间与同伴协调击杀目标
- 白天隐藏身份，伪装成好人发言
- 通过投票引导舆论指向好人
- 关键时刻可以跳神牌自证或转移怀疑

思考以下问题：
1. 你的隐藏伪装策略是否成功？什么时候被怀疑的？
2. 夜间击杀目标选择是否合理？有没有击杀关键神职？
3. 投票时是否成功引导了舆论？
4. 与狼人同伴的配合如何？
5. 整体战略有哪些可以改进的地方？""",
            "outcome_analysis": {
                "win": "狼人阵营取得了胜利。分析狼队做对了什么：",
                "lose": "好人阵营取得了胜利。分析狼队做错了什么："
            }
        },
        "prophet": {
            "role_intro": """你是狼人杀游戏中的一名预言家。你的任务是回顾整场对局，以第一视角总结经验教训。

预言家的胜利条件：帮助好人消灭所有狼人
预言家的核心玩法：
- 每晚可以查验一名玩家的真实身份
- 选择合适的时机公开查验结果
- 需要平衡信息暴露和自身安全
- 通过发言帮助好人分析局势

思考以下问题：
1. 你查验玩家的顺序是否合理？有没有先查高收益目标？
2. 公开查验结果的时机是否合适？有没有被质疑假预言家？
3. 你的发言是否有效帮助了好人分辨狼人？
4. 你有没有被狼人针对或被误导？""",
            "outcome_analysis": {
                "win": "好人阵营取得了胜利，你作为预言家功不可没。分析你做对了什么：",
                "lose": "好人阵营失败了。分析你的查验和发言有哪些失误："
            }
        },
        "witch": {
            "role_intro": """你是狼人杀游戏中的一名女巫。你的任务是回顾整场对局，以第一视角总结经验教训。

女巫的胜利条件：帮助好人消灭所有狼人
女巫的核心玩法：
- 拥有一瓶解药（救活被狼人击杀的人）和一瓶毒药（毒死一人）
- 解药通常在关键时刻使用（如救预言家）
- 毒药需要精准判断，使用不当会害好人
- 可以根据被击杀情况判断狼人目标

思考以下问题：
1. 你使用解药的时机是否正确？救了谁？为什么？
2. 你使用毒药的判断是否准确？毒对了人还是毒错了？
3. 你的药都用在什么轮次？是否过于保守或激进？
4. 你有没有被狼人误导或骗药？""",
            "outcome_analysis": {
                "win": "好人阵营取得了胜利。分析你用药的策略：",
                "lose": "好人阵营失败了。分析你的用药决策有哪些失误："
            }
        },
        "hunter": {
            "role_intro": """你是狼人杀游戏中的一名猎人。你的任务是回顾整场对局，以第一视角总结经验教训。

猎人的胜利条件：帮助好人消灭所有狼人
猎人的核心玩法：
- 死亡时可以带走一名玩家（被女巫毒死不能发动）
- 尽量在死亡时带走狼人
- 存活时可以跳猎人牌自证
- 发言和行为可以适当激进

思考以下问题：
1. 你死亡时的追刀是否准确？带走了狼人还是好人？
2. 你有没有在合适的时机跳猎人牌自证？
3. 你被狼人针对的情况如何？
4. 你的整体发言和行为策略是否有效？""",
            "outcome_analysis": {
                "win": "好人阵营取得了胜利。分析你作为猎人的贡献：",
                "lose": "好人阵营失败了。分析你有哪些失误："
            }
        },
        "villager": {
            "role_intro": """你是狼人杀游戏中的一名平民。你的任务是回顾整场对局，以第一视角总结经验教训。

平民的胜利条件：帮助好人消灭所有狼人
平民的核心玩法：
- 没有任何特殊能力，只能通过发言和分析判断狼人
- 仔细观察每位玩家的发言内容和行为模式
- 注意哪些玩家在回避关键问题
- 通过投票将狼人出局

思考以下问题：
1. 你的发言分析是否有效帮助了好人找出狼人？
2. 你的投票是否准确？有没有投错好人？
3. 你有没有被狼人的伪装误导？
4. 你对局势的判断哪些是对的，哪些是错的？""",
            "outcome_analysis": {
                "win": "好人阵营取得了胜利。分析你作为平民的贡献：",
                "lose": "好人阵营失败了。分析你的判断和投票有哪些失误："
            }
        }
    }

    @classmethod
    def create(cls, role_type: str) -> "SummaryAgent":
        """
        工厂方法：创建指定角色的 SummaryAgent

        Args:
            role_type: 角色类型 (werewolf/prophet/witch/hunter/villager)

        Returns:
            SummaryAgent 实例
        """
        if role_type not in cls.ROLE_SUMMARY_TEMPLATES:
            role_type = "villager"  # 默认使用平民模板
        return cls(role_type)

    def __init__(self, role_type: str):
        """初始化 SummaryAgent"""
        self.role_type = role_type
        self.template = self.ROLE_SUMMARY_TEMPLATES.get(role_type, self.ROLE_SUMMARY_TEMPLATES["villager"])
        self.instructions = self._build_instructions()

        self.agent = Agent(
            name=f"summary_{role_type}_agent",
            model=config.default_model,
            instructions=self.instructions,
        )

    def _build_instructions(self) -> str:
        """构建总结提示词"""
        return f"""你是一个狼人杀游戏的经验总结专家。你的任务是根据对局记录，以第一视角总结该角色在游戏中的经验教训。

{self.template['role_intro']}

## 输出要求

请分析以下对局记录，给出经验总结。你必须输出JSON格式的总结，格式如下：

{{
    "situation": "情境描述：简要描述本局游戏的关键局势和你的处境",
    "available_actions": ["可选行动1", "可选行动2", "..."],
    "chosen_action": "你实际选择的行动",
    "outcome": "结果：success/failed/neutral",
    "result_reason": "结果原因：解释为什么这个行动导致了这样的结果",
    "key_learning": "关键教训：总结一条最重要的经验教训，用于指导未来游戏"
}}

请确保：
1. situation 要具体描述当时的局势，包括存活人数、阵营对比、关键事件等
2. available_actions 要列出2-4个当时可选的主要行动
3. chosen_action 要明确你实际做了什么
4. outcome 要客观评估结果：success（成功达成目标）、failed（导致失败）、neutral（无直接影响）
5. result_reason 要分析因果关系
6. key_learning 要提炼出可复用的经验

只输出JSON，不要输出其他内容。"""

    def _format_game_record(self, game_record: Dict[str, Any]) -> str:
        """
        将对局记录格式化为文本

        Args:
            game_record: 对局记录字典

        Returns:
            格式化的对局记录文本
        """
        lines = []

        # 基本信息
        lines.append(f"【对局基本信息】")
        lines.append(f"对局ID：{game_record.get('game_id', 'unknown')}")
        lines.append(f"角色：{self.role_type}")
        lines.append(f"阵营：{'狼人阵营' if self.role_type == 'werewolf' else '好人阵营'}")
        lines.append(f"胜负：{'胜利' if game_record.get('win') else '失败'}")
        lines.append(f"存活状态：{'存活' if game_record.get('survived') else '死亡'}")

        if death_info := game_record.get('death_info'):
            lines.append(f"死亡时间：第{death_info.get('day', '?')}天")
            lines.append(f"死亡原因：{death_info.get('reason', 'unknown')}")

        # 存活玩家
        if alive_players := game_record.get('alive_players'):
            lines.append(f"\n【存活玩家】({len(alive_players)}人)：{', '.join(alive_players)}")

        # 死亡玩家
        if dead_players := game_record.get('dead_players'):
            lines.append(f"\n【死亡玩家】({len(dead_players)}人)：{', '.join(dead_players)}")

        # 夜间行动记录
        if night_actions := game_record.get('night_actions'):
            lines.append(f"\n【夜间行动记录】")
            for night in night_actions:
                lines.append(f"  第{night.get('day', '?')}夜：{night.get('action', '')}")

        # 白天发言记录
        if speeches := game_record.get('speech_records'):
            lines.append(f"\n【白天发言记录】")
            for day, day_speeches in speeches.items():
                lines.append(f"  第{day}天：")
                for pid, speech in day_speeches.items():
                    truncated = speech[:80] + "..." if len(speech) > 80 else speech
                    lines.append(f"    {pid}：{truncated}")

        # 投票记录
        if votes := game_record.get('vote_records'):
            lines.append(f"\n【投票记录】")
            for day, day_votes in votes.items():
                lines.append(f"  第{day}天：")
                for voter, voted in day_votes.items():
                    lines.append(f"    {voter} → {voted}")

        # 角色私有信息（如果有）
        if private_info := game_record.get('private_info'):
            lines.append(f"\n【角色私有信息】")
            if self.role_type == "werewolf":
                if fellows := private_info.get('fellow_werewolves'):
                    lines.append(f"  狼人同伴：{', '.join(fellows)}")
            elif self.role_type == "prophet":
                if checks := private_info.get('checked_players'):
                    lines.append(f"  查验记录：{checks}")
            elif self.role_type == "witch":
                if saves := private_info.get('save_used'):
                    lines.append(f"  解药状态：{'已使用' if saves else '未使用'}")
                if poisons := private_info.get('poison_used'):
                    lines.append(f"  毒药状态：{'已使用' if poisons else '未使用'}")

        # 胜利/失败原因
        if self.role_type == "werewolf":
            outcome_key = "win" if game_record.get('win') else "lose"
        else:
            # 好人阵营根据是否有狼人存活判断
            werewolf_alive = game_record.get('werewolf_count', 0) > 0
            outcome_key = "lose" if not werewolf_alive else "win"
            # 但如果自己是狼人且狼人赢了，用win
            if self.role_type == "werewolf":
                outcome_key = "win" if game_record.get('win') else "lose"

        lines.append(f"\n{self.template['outcome_analysis'].get(outcome_key, '分析本局：')}")

        return "\n".join(lines)

    async def summarize(self, game_record: Dict[str, Any]) -> ExperienceEntry:
        """
        根据对局记录生成经验总结

        Args:
            game_record: 对局记录，包含以下字段：
                - game_id: 对局ID
                - role_type: 角色类型
                - win: 是否胜利
                - survived: 是否存活
                - death_info: 死亡信息 {day, reason}
                - alive_players: 存活玩家列表
                - dead_players: 死亡玩家列表
                - night_actions: 夜间行动记录
                - speech_records: 发言记录
                - vote_records: 投票记录
                - private_info: 角色私有信息

        Returns:
            ExperienceEntry: 经验条目
        """
        formatted_record = self._format_game_record(game_record)

        prompt = f"""{self.instructions}

## 对局记录

{formatted_record}

请根据以上对局记录，以第一视角总结本局游戏中的关键经验教训。"""

        try:
            output = await Runner.run(self.agent, prompt)
            response_text = output.output_text

            # 解析 JSON
            json_str = response_text
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()

            data = json.loads(json_str)

            # 创建经验条目
            experience = ExperienceEntry(
                game_id=game_record.get('game_id', 'unknown'),
                situation=data.get('situation', ''),
                available_actions=data.get('available_actions', []),
                chosen_action=data.get('chosen_action', ''),
                outcome=data.get('outcome', 'neutral'),
                result_reason=data.get('result_reason', ''),
                key_learning=data.get('key_learning', ''),
            )

            # 保存到经验库
            exp_manager = get_experience_manager()
            exp_manager.add_experience(
                role_type=self.role_type,
                game_id=experience.game_id,
                situation=experience.situation,
                available_actions=experience.available_actions,
                chosen_action=experience.chosen_action,
                outcome=experience.outcome,
                result_reason=experience.result_reason,
                key_learning=experience.key_learning,
            )

            return experience

        except json.JSONDecodeError:
            # 解析失败，返回空经验
            return ExperienceEntry(
                game_id=game_record.get('game_id', 'unknown'),
                situation="解析失败",
                available_actions=[],
                chosen_action="unknown",
                outcome="neutral",
                result_reason="LLM返回格式错误，无法解析",
                key_learning="无",
            )

    # ==================== 同步版本 ====================

    def summarize_sync(self, game_record: Dict[str, Any]) -> ExperienceEntry:
        """同步版本的经验总结"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.summarize(game_record))
                    return future.result()
            else:
                return loop.run_until_complete(self.summarize(game_record))
        except RuntimeError:
            return asyncio.run(self.summarize(game_record))


# ==================== 便捷函数 ====================

async def summarize_game(
    game_record: Dict[str, Any],
    role_type: Optional[str] = None
) -> ExperienceEntry:
    """
    便捷函数：对指定角色进行经验总结

    Args:
        game_record: 对局记录
        role_type: 角色类型，如果为None则从game_record中获取

    Returns:
        ExperienceEntry
    """
    if role_type is None:
        role_type = game_record.get('role_type', 'villager')

    agent = SummaryAgent.create(role_type)
    return await agent.summarize(game_record)


def summarize_game_sync(
    game_record: Dict[str, Any],
    role_type: Optional[str] = None
) -> ExperienceEntry:
    """同步版本的经验总结"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, summarize_game(game_record, role_type))
                return future.result()
        else:
            return loop.run_until_complete(summarize_game(game_record, role_type))
    except RuntimeError:
        return asyncio.run(summarize_game(game_record, role_type))
