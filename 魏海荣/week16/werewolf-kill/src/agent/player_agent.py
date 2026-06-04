"""
Player Agent 模块

负责根据角色类型创建对应的 Agent 实例，并提供决策方法。
每个 PlayerAgent 封装了角色认知、决策逻辑和行动生成能力。

核心方法：
- decide_night_action(): 夜间行动决策（击杀/查验/用药等）
- decide_day_speech(): 白天发言决策
- decide_vote(): 投票决策
"""

import json
from typing import Optional, Dict, Any, List

from agents import Agent, Runner

from .base import BaseAgent
from src.roles import (
    Role,
    Werewolf,
    Prophet,
    Witch,
    Hunter,
    Villager,
)
from agents import set_default_openai_api, set_tracing_disabled
from src.schemas.system_config import load_system_config
from src.schemas.roles_schema import (
    GamePhaseState,
    NightActionResult,
    DayActionResult,
    VoteResult,
    SpeakResult,
    RoleType,
    ActionType
)
from src.memory import get_experience_manager

set_default_openai_api("chat_completions")
set_tracing_disabled(True)

config = load_system_config("config/system_config.json")


class PlayerAgent(BaseAgent):
    """
    Player Agent 工厂类

    负责创建和管理不同角色的 Agent 实例。
    每个 PlayerAgent 绑定一个 Role 实例，并生成对应的 AI 指令。

    核心决策方法：
    - decide_night_action(): 夜间行动决策
    - decide_day_speech(): 白天发言决策
    - decide_vote(): 投票决策
    """

    # 角色类映射
    ROLE_CLASSES: Dict[str, type] = {
        "werewolf": Werewolf,
        "prophet": Prophet,
        "witch": Witch,
        "hunter": Hunter,
        "villager": Villager,
    }

    # 决策风格配置
    DECISION_STYLES: Dict[str, Dict[str, str]] = {
        "aggressive": {
            "name": "激进型",
            "description": "主动出击，敢于冒险，快速暴露可疑玩家",
            "speech_tendency": "直接点名怀疑对象，措辞激烈",
            "vote_tendency": "倾向投票给高度怀疑对象，不犹豫",
            "night_tendency": "优先击杀关键神职角色",
        },
        "cautious": {
            "name": "谨慎型",
            "description": "仔细分析后再行动，不轻易暴露自己的判断",
            "speech_tendency": "引导他人发言，自己较少直接点名",
            "vote_tendency": "跟随主流票型，或投弃权票",
            "night_tendency": "优先击杀信息明确的目标",
        },
        "balanced": {
            "name": "平衡型",
            "description": "根据局势灵活调整策略，该激进时激进，该保守时保守",
            "speech_tendency": "有理有据地分析，不偏激也不保守",
            "vote_tendency": "基于自己的分析做决策",
            "night_tendency": "综合考虑收益和风险",
        },
    }

    # 角色对应的推荐决策风格
    ROLE_DEFAULT_STYLE: Dict[str, str] = {
        "werewolf": "balanced",
        "prophet": "aggressive",
        "witch": "cautious",
        "hunter": "aggressive",
        "villager": "cautious",
    }

    def __init__(self, role: Role, decision_style: Optional[str] = None):
        """初始化 PlayerAgent"""
        super().__init__()
        self.role = role
        self.decision_style = decision_style or self.ROLE_DEFAULT_STYLE.get(
            role.role_type, "balanced"
        )
        # 经验管理器（需在使用前初始化）
        self._exp_manager = get_experience_manager()
        self.instructions = self._build_instructions()

        self.agent = Agent(
            name=f"{role.role_type}_agent_{role.player_id or ''}",
            model=config.default_model,
            instructions=self.instructions,
        )

    def _get_private_context(self) -> str:
        """根据角色类型构建私有信息上下文"""
        role_type = self.role.role_type
        lines = []

        if role_type == "werewolf":
            werewolf = self.role
            lines.append(f"- 你的狼人同伴：{werewolf.fellow_werewolves if hasattr(werewolf, 'fellow_werewolves') else '暂无'}")
            lines.append("- 你知道自己是狼人，需要隐藏身份")
            lines.append("- 夜间可以与狼人同伴协调击杀目标")
        elif role_type == "prophet":
            prophet = self.role
            checked = prophet.get_check_history() if hasattr(prophet, 'get_check_history') else {}
            lines.append("- 你是预言家，可以查验玩家身份")
            lines.append("- 你的查验结果是准确的")
            if checked:
                wolf_players = [k for k, v in checked.items() if v]
                good_players = [k for k, v in checked.items() if not v]
                if wolf_players:
                    lines.append(f"- 已查验狼人：{wolf_players}")
                if good_players:
                    lines.append(f"- 已查验好人：{good_players}")
            lines.append("- 尽量在适当时机公开查验结果帮助好人")
        elif role_type == "witch":
            witch = self.role
            lines.append("- 你有一瓶解药（救活被狼人击杀的玩家）和一瓶毒药（毒死一名玩家）")
            lines.append(f"- 解药状态：{'已使用' if hasattr(witch, 'can_save') and not witch.can_save else '可用'}")
            lines.append(f"- 毒药状态：{'已使用' if hasattr(witch, 'can_poison') and not witch.can_poison else '可用'}")
            lines.append("- 谨慎决定是否用药，以及用药目标")
        elif role_type == "hunter":
            hunter = self.role
            lines.append("- 你是猎人，死亡时可以带走一名玩家")
            lines.append(f"- 开枪状态：{'可用' if hasattr(hunter, 'can_shoot') and hunter.can_shoot else '不可用'}")
            lines.append("- 如果被女巫毒药毒死则无法发动技能")
            lines.append("- 尽量在死亡时带走狼人")
        elif role_type == "villager":
            lines.append("- 你是普通村民，没有任何特殊能力")
            lines.append("- 通过观察发言和行为来判断狼人")
            lines.append("- 积极参与讨论和分析")

        return "\n".join(lines) if lines else "无特殊私有信息"

    def _get_experience_section(self) -> str:
        """获取经验提示部分"""
        experiences = self._exp_manager.get_recent_experiences(self.role.role_type, limit=3)

        if not experiences:
            return """
## 历史经验参考
- 狼人杀是一个需要逻辑推理和心理博弈的游戏
- 关键要点：
  1. 注意观察玩家的发言顺序和内容
  2. 分析投票结果，找出可能的狼人团队
  3. 注意哪些玩家在回避关键问题
  4. 合理利用角色能力，为阵营做出贡献
  5. 保持冷静，不要被情绪影响判断
"""

        lines = ["\n## 历史经验参考"]
        for i, exp in enumerate(experiences, 1):
            lines.append(f"{i}. [{self.role.role_type}] {exp.key_learning}")

        return "\n".join(lines)

    def _build_instructions(self) -> str:
        """根据角色类型构建 AI 指令"""
        camp_desc = "狼人阵营" if self.role.camp == "werewolf" else "好人阵营"
        style_info = self.DECISION_STYLES.get(self.decision_style, self.DECISION_STYLES["balanced"])
        private_context = self._get_private_context()

        return f"""你是一个狼人杀游戏中的玩家。
你的角色是：{self.role.name}
你的阵营是：{camp_desc}
你的玩家ID是：{self.role.player_id}

## 游戏规则
1. 夜晚：狼人需要协调击杀目标，预言家查验玩家，女巫决定是否用药
2. 白天：公开辩论后投票选出嫌疑人处决
3. 胜利条件：
   - 善良阵营：消灭所有狼人
   - 邪恶阵营：消灭所有神职或所有村民, 如果场上只剩狼人和一个村民，狼人也算胜利

## 我的私有信息
{private_context}

## 决策风格
你的决策风格是：{style_info['name']}
特点：{style_info['description']}
- 发言倾向：{style_info['speech_tendency']}
- 投票倾向：{style_info['vote_tendency']}
- 夜间行动倾向：{style_info['night_tendency']}

请根据你的决策风格做出符合该风格的游戏决策。
{self._get_experience_section()}

## 输出要求
你必须输出JSON格式的决策，格式如下：
- 夜晚行动：{{"action": "night_action", "target": 玩家ID或null, "reasoning": "决策理由"}}
- 白天发言：{{"action": "speech", "content": "发言内容"}}
- 投票：{{"action": "vote", "target": 玩家ID或null}}

请根据当前游戏状态做出最优决策。
"""

    # ==================== 游戏状态格式化 ====================

    def format_game_state(self, game_state: GamePhaseState) -> str:
        """
        将游戏状态格式化为详细的提示词

        Args:
            game_state: 游戏阶段状态

        Returns:
            格式化的游戏状态字符串
        """
        role_type = self.role.role_type

        lines = [
            f"【当前状态】",
            f"- 阶段：{'夜晚' if game_state.phase == 'night' else '白天'}",
            f"- 第{game_state.day_number}天",
            f"- 我的ID：{self.role.player_id}",
            f"- 我的角色：{self.role.name}",
        ]

        # 存活玩家
        lines.append(f"\n【存活玩家】({len(game_state.alive_players)}人)")
        for pid in game_state.alive_players:
            marker = " [自己]" if pid == self.role.player_id else ""
            lines.append(f"  - {pid}{marker}")

        # 死亡玩家
        if game_state.dead_players:
            lines.append(f"\n【死亡玩家】({len(game_state.dead_players)}人)")
            for pid in game_state.dead_players:
                lines.append(f"  - {pid}")

        # 昨晚死亡（夜晚阶段显示）
        if game_state.previous_kills:
            lines.append(f"\n【昨晚死亡】{game_state.previous_kills}")

        # 发言记录
        if game_state.speech_records:
            lines.append("\n【今日发言】")
            for pid, speech in game_state.speech_records.items():
                truncated = speech[:100] + "..." if len(speech) > 100 else speech
                lines.append(f"  {pid}：{truncated}")

        # 投票记录
        if game_state.vote_records:
            lines.append("\n【投票记录】")
            for voter, voted in game_state.vote_records.items():
                target_str = voted if voted else "弃票"
                lines.append(f"  {voter} → {target_str}")

        # 查验记录（预言家专有）
        if role_type == "prophet" and game_state.checked_history:
            lines.append("\n【查验历史】")
            for pid, is_werewolf in game_state.checked_history.items():
                result = "狼人" if is_werewolf else "好人"
                lines.append(f"  {pid}：{result}")

        return "\n".join(lines)

    def format_role_specific_context(self, game_state: GamePhaseState) -> str:
        """
        格式化为特定角色的决策上下文

        Args:
            game_state: 游戏阶段状态

        Returns:
            角色特定的决策提示
        """
        role_type = self.role.role_type
        candidates = [p for p in game_state.alive_players if p != self.role.player_id]

        if role_type == "werewolf":
            werewolf = self.role
            fellows = werewolf.fellow_werewolves if hasattr(werewolf, 'fellow_werewolves') else []
            lines = [
                "\n【狼人专属信息】",
                f"- 狼人同伴：{fellows if fellows else '无'}",
                f"- 可击杀目标：{candidates}",
                "\n请选择今晚击杀的目标。"
            ]
        elif role_type == "prophet":
            checked = game_state.checked_history
            unchecked = [p for p in candidates if p not in checked]
            lines = [
                "\n【预言家专属信息】",
                f"- 已查验玩家：{list(checked.keys()) if checked else '无'}",
                f"- 可查验目标：{unchecked if unchecked else '无'}",
                "\n请选择今晚查验的目标。"
            ]
        elif role_type == "witch":
            witch = self.role
            can_save = hasattr(witch, 'can_save') and witch.can_save
            can_poison = hasattr(witch, 'can_poison') and witch.can_poison
            killed = game_state.previous_kills[0] if game_state.previous_kills else None

            lines = [
                "\n【女巫专属信息】",
                f"- 解药：{'可用' if can_save else '已使用'}",
                f"- 毒药：{'可用' if can_poison else '已使用'}",
            ]
            if killed:
                lines.append(f"- 今晚狼人击杀目标：{killed}")
            lines.append(f"- 可用药目标：{candidates}")
            lines.append("\n请决定是否用药，以及用药目标。")
        elif role_type == "hunter":
            hunter = self.role
            lines = [
                "\n【猎人专属信息】",
                f"- 开枪状态：{'可用' if hasattr(hunter, 'can_shoot') and hunter.can_shoot else '不可用'}",
                f"- 可击杀目标：{candidates}",
            ]
        elif role_type == "villager":
            lines = [
                "\n【平民游戏建议】",
                "- 仔细分析每位玩家的发言内容",
                "- 注意哪些玩家在回避关键问题",
                "- 观察投票模式，找出可能的狼人团队",
            ]
        else:
            lines = []

        return "\n".join(lines)

    # ==================== LLM 决策调用 ====================

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """
        调用 LLM 获取决策

        Args:
            prompt: 输入提示词

        Returns:
            LLM 返回的决策字典
        """
        try:
            output = await Runner.run(self.agent, prompt)
            response_text = output.output_text

            # 尝试解析 JSON
            # 提取 ```json ... ``` 块或直接解析
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
            return {"action": "pass", "reasoning": "解析失败，默认跳过"}
        except Exception as e:
            return {"action": "pass", "reasoning": f"LLM调用失败: {str(e)}"}

    # ==================== 核心决策方法 ====================

    async def decide_night_action(self, game_state: GamePhaseState) -> NightActionResult:
        """
        夜间行动决策

        Args:
            game_state: 游戏阶段状态

        Returns:
            夜间行动结果
        """
        if not self.role.is_alive:
            from src.schemas.roles_schema import NoNightActionResult, ActionType
            return NoNightActionResult(action=ActionType.PASS, reason="角色已死亡")

        role_type = self.role.role_type

        # 构建决策提示
        base_state = self.format_game_state(game_state)
        role_context = self.format_role_specific_context(game_state)
        experience_section = self._get_experience_section()

        prompt = f"""{self.instructions}

{base_state}
{role_context}

{experience_section}

请根据以上信息，给出你的夜间行动决策。
返回JSON格式：{{"action": "night_action", "target": "玩家ID或null", "reasoning": "决策理由"}}
"""

        decision = await self._call_llm(prompt)

        # 根据角色类型构建结果
        target = decision.get("target")
        from src.schemas.roles_schema import ActionType

        if role_type == "werewolf":
            from src.schemas.roles_schema import WerewolfKillResult
            self.role.use_ability("kill")
            return WerewolfKillResult(
                action=ActionType.KILL,
                target=target,
                success=True
            )
        elif role_type == "prophet":
            from src.schemas.roles_schema import ProphetCheckResult
            self.role.use_ability("check")
            # 实际结果由游戏引擎填充
            return ProphetCheckResult(
                action=ActionType.CHECK,
                target=target,
                is_werewolf=False,  # 待游戏引擎填充
                role_name="",  # 待游戏引擎填充
                success=True
            )
        elif role_type == "witch":
            if target:
                witch = self.role
                if hasattr(witch, 'can_save') and witch.can_save and target in game_state.previous_kills:
                    from src.schemas.roles_schema import WitchSaveResult
                    witch.use_ability("save")
                    return WitchSaveResult(
                        action=ActionType.SAVE,
                        target=target,
                        used=True,
                        success=True
                    )
                elif hasattr(witch, 'can_poison') and witch.can_poison:
                    from src.schemas.roles_schema import WitchPoisonResult
                    witch.use_ability("poison")
                    return WitchPoisonResult(
                        action=ActionType.POISON,
                        target=target,
                        used=True,
                        success=True
                    )
            from src.schemas.roles_schema import NoNightActionResult
            return NoNightActionResult(action=ActionType.PASS, reason="不行动")
        else:
            from src.schemas.roles_schema import NoNightActionResult
            return NoNightActionResult(action=ActionType.PASS, reason="该角色夜间不行动")

    async def decide_day_speech(self, game_state: GamePhaseState) -> SpeakResult:
        """
        白天发言决策

        Args:
            game_state: 游戏阶段状态

        Returns:
            发言结果
        """
        if not self.role.is_alive:
            return SpeakResult(
                action=ActionType.SPEAK,
                content="（死亡，无发言）",
                emotion="neutral"
            )

        role_type = self.role.role_type
        style_info = self.DECISION_STYLES.get(self.decision_style, self.DECISION_STYLES["balanced"])

        # 构建决策提示
        base_state = self.format_game_state(game_state)

        prompt = f"""{self.instructions}

{base_state}

## 发言任务
你的决策风格要求：{style_info['speech_tendency']}
请根据游戏局势和你的角色，给出一段发言。

发言要求：
1. 符合你的角色身份和决策风格
2. 内容要合理，不要过度暴露或过度隐瞒
3. 可以分析局势、质疑可疑玩家、或为队友辩护

返回JSON格式：{{"action": "speech", "content": "发言内容", "emotion": "情绪标签"}}
"""

        decision = await self._call_llm(prompt)

        content = decision.get("content", "过。")
        emotion = decision.get("emotion", "neutral")

        return SpeakResult(
            action=ActionType.SPEAK,
            content=content,
            emotion=emotion
        )

    async def decide_vote(self, game_state: GamePhaseState) -> VoteResult:
        """
        投票决策

        Args:
            game_state: 游戏阶段状态

        Returns:
            投票结果
        """
        if not self.role.is_alive:
            return VoteResult(
                action=ActionType.VOTE,
                target=None,
                reasoning="角色已死亡"
            )

        role_type = self.role.role_type
        style_info = self.DECISION_STYLES.get(self.decision_style, self.DECISION_STYLES["balanced"])
        candidates = [p for p in game_state.alive_players if p != self.role.player_id]

        # 构建决策提示
        base_state = self.format_game_state(game_state)

        prompt = f"""{self.instructions}

{base_state}

## 投票任务
你的决策风格要求：{style_info['vote_tendency']}
当前可投票玩家：{candidates}

请做出你的投票决定：
- 投给你认为最可疑的玩家
- 或投弃权票（target设为null）

返回JSON格式：{{"action": "vote", "target": "玩家ID或null", "reasoning": "投票理由"}}
"""

        decision = await self._call_llm(prompt)

        target = decision.get("target")
        reasoning = decision.get("reasoning", "")

        # 验证 target 是否有效
        if target and target not in game_state.alive_players:
            target = None

        return VoteResult(
            action=ActionType.VOTE,
            target=target,
            reasoning=reasoning
        )

    async def decide_hunter_shoot(self, game_state: GamePhaseState) -> str:
        """
        猎人追刀决策

        Args:
            game_state: 游戏阶段状态

        Returns:
            被带走的目标玩家ID
        """
        if not self.role.is_alive:
            return None

        hunter = self.role
        if not (hasattr(hunter, 'can_shoot') and hunter.can_shoot):
            return None

        candidates = [p for p in game_state.alive_players if p != self.role.player_id]

        prompt = f"""{self.instructions}

你（猎人）即将死亡，需要带走一名玩家。
可带走目标：{candidates}

请选择你要带走的玩家（通常是狼人或关键嫌疑人）。
返回JSON格式：{{"action": "shoot", "target": "玩家ID", "reasoning": "理由"}}
"""

        decision = await self._call_llm(prompt)
        target = decision.get("target")

        if target and target in candidates:
            return target
        return None

    # ==================== 同步版本决策方法 ====================

    def decide_night_action_sync(self, game_state: GamePhaseState) -> NightActionResult:
        """同步版本的夜间行动决策（供游戏引擎同步调用）"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，创建一个新的
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.decide_night_action(game_state))
                    return future.result()
            else:
                return loop.run_until_complete(self.decide_night_action(game_state))
        except RuntimeError:
            return asyncio.run(self.decide_night_action(game_state))

    def decide_day_speech_sync(self, game_state: GamePhaseState) -> SpeakResult:
        """同步版本的白天发言决策"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.decide_day_speech(game_state))
                    return future.result()
            else:
                return loop.run_until_complete(self.decide_day_speech(game_state))
        except RuntimeError:
            return asyncio.run(self.decide_day_speech(game_state))

    def decide_vote_sync(self, game_state: GamePhaseState) -> VoteResult:
        """同步版本的投票决策"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.decide_vote(game_state))
                    return future.result()
            else:
                return loop.run_until_complete(self.decide_vote(game_state))
        except RuntimeError:
            return asyncio.run(self.decide_vote(game_state))
