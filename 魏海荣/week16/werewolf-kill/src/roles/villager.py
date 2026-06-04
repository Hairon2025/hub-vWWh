"""
平民角色实现

阵营：好人阵营
胜利条件：消灭所有狼人

平民特点：
- 没有任何特殊能力
- 只能通过白天发言和投票来参与游戏
- 需要依靠预言家、女巫等神职提供的信息
- 容易被狼人误导
- 是狼人主要猎杀的目标之一
"""

from typing import Optional, List, TYPE_CHECKING

# Schema 类型
if TYPE_CHECKING:
    from schemas.roles_schema import (
        NightActionResult,
        DayActionResult,
        PublicInfo,
        PrivateInfo,
        GamePhaseState,
        ActionType,
    )

# 导入 Schema 类
from schemas.roles_schema import (
    NoNightActionResult,
    VoteResult,
    PublicInfo,
    PrivateInfo,
    ActionType,
)

from .base import Role


class Villager(Role):
    """
    平民

    好人阵营的基础角色，没有特殊能力。
    只能通过发言和投票来影响游戏进程。
    """

    def __init__(self, player_id: Optional[str] = None):
        super().__init__(
            role_type="villager",
            camp="village",
            player_id=player_id,
            abilities=[]  # 平民没有特殊能力
        )

    def get_public_info(self) -> PublicInfo:
        """
        获取公开信息
        平民就是平民，无需隐藏身份
        """
        return PublicInfo(
            visible_role="平民",
            is_suspicious=False,
            speech_style="normal",
            claims="平民"
        )

    def get_private_info(self, viewer: Optional[Role] = None) -> PrivateInfo:
        """
        获取私有信息
        平民没有任何私有信息
        """
        return PrivateInfo()

    def night_action(self, game_state: "GamePhaseState") -> "NightActionResult":
        """
        夜间行动：平民夜间没有行动

        平民在夜间只能等待，无法进行任何行动

        Returns:
            NoNightActionResult: 无行动结果
        """
        return NoNightActionResult(
            action=ActionType.PASS,
            reason="平民夜间不行动"
        )

    def day_action(self, game_state: "GamePhaseState") -> "DayActionResult":
        """
        白天行动：发言和投票

        平民的主要游戏方式：
        - 通过发言分析其他玩家的行为
        - 观察哪些人行为可疑
        - 投票淘汰疑似狼人的玩家

        Args:
            game_state: 游戏阶段状态

        Returns:
            VoteResult: 投票结果
        """
        if not self.is_alive:
            return VoteResult(
                action=ActionType.VOTE,
                target=None,
                speech=None,
                reasoning="角色已死亡"
            )

        # TODO: 实现平民白天AI逻辑
        # 平民AI策略建议：
        # 1. 分析死亡玩家的遗言和死因
        # 2. 观察可疑玩家的发言
        # 3. 跟随可信的神职玩家投票
        # 4. 避免被狼人误导

        return VoteResult(
            action=ActionType.VOTE,
            target=None,   # 待AI决策
            speech=None,   # 待AI生成
            reasoning=None
        )

    def analyze_suspicion(
        self,
        player_id: str,
        speech_history: List[str],
        vote_history: dict,
        death_history: List[dict]
    ) -> float:
        """
        分析某个玩家的可疑程度

        Args:
            player_id: 要分析的玩家ID
            speech_history: 该玩家的发言历史
            vote_history: 投票历史
            death_history: 死亡历史

        Returns:
            float: 0.0-1.0 的可疑度分数
            1.0 = 非常可疑（可能是狼人）
            0.0 = 完全可信
        """
        suspicion_score = 0.0

        # TODO: 分析该玩家的发言是否可疑
        # - 是否在回避关键问题
        # - 是否在转移话题
        # - 是否在误导其他人

        # TODO: 分析该玩家的投票是否可疑
        # - 是否投给了好人
        # - 是否在狼人阵营时投对了人（反向分析）

        # TODO: 分析死亡历史中该玩家的行为
        # - 该玩家是否在狼人阵营存活时死亡
        # - 该玩家的遗言是否可信

        return suspicion_score
