"""
预言家角色实现

阵营：好人阵营
胜利条件：消灭所有狼人

预言家特点：
- 夜间行动：可以查验一名玩家的身份
- 可以知道玩家的真实角色（狼人/好人）
- 查验结果只有预言家自己知道
- 白天需要引导好人投票正确的目标
- 容易被狼人针对
"""

from typing import Optional, List, Dict, TYPE_CHECKING

# Schema 类型
if TYPE_CHECKING:
    from schemas.roles_schema import (
        NightActionResult,
        ProphetCheckResult,
        NoNightActionResult,
        DayActionResult,
        VoteResult,
        PublicInfo,
        PrivateInfo,
        GamePhaseState,
        ActionType,
    )

# 导入 Schema 类
from schemas.roles_schema import (
    ProphetCheckResult,
    NoNightActionResult,
    VoteResult,
    PublicInfo,
    PrivateInfo,
    ActionType,
    Ability,
)

from .base import Role


class Prophet(Role):
    """
    预言家

    好人阵营的神职角色，拥有查验能力。
    是好人阵营追查狼人的主要信息来源。
    """

    def __init__(self, player_id: Optional[str] = None):
        super().__init__(
            role_type="prophet",
            camp="village",
            player_id=player_id,
            abilities=[
                Ability(
                    name="check",
                    description="夜间查验一名玩家的身份",
                    can_use=True,
                    max_uses=None,  # 每晚都可以使用
                )
            ]
        )
        self._checked_players: Dict[str, bool] = {}  # player_id -> 是否为狼人
        self._checked_roles: Dict[str, str] = {}  # player_id -> 真实角色名称

    def get_public_info(self) -> PublicInfo:
        """
        获取公开信息
        预言家公开身份可以增强可信度，但也容易被狼人针对
        """
        return PublicInfo(
            visible_role="好人",
            is_suspicious=False,
            speech_style="normal",
            claims="平民"  # 预言家通常隐藏身份
        )

    def get_private_info(self, viewer: Optional[Role] = None) -> PrivateInfo:
        """
        获取私有信息
        查验记录只有预言家自己知道
        """
        # 只有预言家自己能看到查验记录
        if viewer is not None and viewer.role_type == "prophet":
            return PrivateInfo(
                checked_players=self._checked_players.copy(),
                checked_roles=self._checked_roles.copy()
            )
        return PrivateInfo()

    def night_action(self, game_state: "GamePhaseState") -> "NightActionResult":
        """
        夜间行动：查验一名玩家

        Args:
            game_state: 游戏阶段状态，包含：
                - alive_players: 存活玩家列表
                - checked_history: 已查验过的玩家 {player_id: is_werewolf}

        Returns:
            ProphetCheckResult: 查验结果
            NoNightActionResult: 无行动结果
        """
        if not self.is_alive:
            return NoNightActionResult(
                action=ActionType.PASS,
                reason="角色已死亡"
            )

        alive_players = game_state.alive_players
        checked_history = game_state.checked_history

        # 排除自己，排除已查验过的玩家
        candidates = [
            p for p in alive_players
            if p != self.player_id and p not in checked_history
        ]

        if not candidates:
            return NoNightActionResult(
                action=ActionType.PASS,
                reason="没有可查验的目标"
            )

        # TODO: 实现预言家AI决策逻辑，选择查验目标
        # 策略建议：
        # - 优先查验疑似狼人的玩家
        # - 查验声称是好人但行为可疑的玩家
        selected_target = candidates[0]

        self.use_ability("check")

        # 实际结果由游戏引擎填充，这里返回占位
        return ProphetCheckResult(
            action=ActionType.CHECK,
            target=selected_target,
            is_werewolf=False,  # 待游戏引擎填充
            role_name="",  # 待游戏引擎填充
            success=True
        )

    def day_action(self, game_state: "GamePhaseState") -> "DayActionResult":
        """
        白天行动：发言和投票

        预言家需要：
        - 决定是否公开身份
        - 分享查验信息（如果选择公开）
        - 引导好人投票狼人

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

        # TODO: 实现预言家白天AI逻辑
        # - 考虑是否公开身份（通常需要保留）
        # - 分享已查验的玩家信息
        # - 投票给可疑玩家

        return VoteResult(
            action=ActionType.VOTE,
            target=None,
            speech=None,
            reasoning=None
        )

    def add_check_result(self, player_id: str, is_werewolf: bool, role_name: str) -> None:
        """记录查验结果（由游戏引擎调用）"""
        self._checked_players[player_id] = is_werewolf
        self._checked_roles[player_id] = role_name

    def get_check_history(self) -> Dict[str, bool]:
        """获取查验历史"""
        return self._checked_players.copy()
