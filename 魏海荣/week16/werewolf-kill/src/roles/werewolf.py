"""
狼人角色实现

阵营：狼人阵营
胜利条件：消灭所有好人阵营玩家

狼人特点：
- 夜间行动：可以击杀一名玩家
- 可以看到其他狼人同伴
- 需要隐藏身份，白天假装好人
- 可以通过投票消灭好人
"""

from typing import Optional, List, TYPE_CHECKING

# Schema 类型
if TYPE_CHECKING:
    from schemas.roles_schema import (
        NightActionResult,
        WerewolfKillResult,
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
    WerewolfKillResult,
    NoNightActionResult,
    VoteResult,
    PublicInfo,
    PrivateInfo,
    ActionType,
    RoleType,
    Ability,
)

from .base import Role


class Werewolf(Role):
    """
    狼人

    狼人阵营的核心角色，可以夜间击杀玩家。
    狼人之间可以互相识别。
    """

    def __init__(self, player_id: Optional[str] = None):
        super().__init__(
            role_type="werewolf",
            camp="werewolf",
            player_id=player_id,
            abilities=[
                Ability(
                    name="kill",
                    description="夜间击杀一名玩家",
                    can_use=True,
                    max_uses=None,  # 每晚都可以使用
                )
            ]
        )
        self._fellow_werewolves: List[str] = []  # 狼人同伴ID列表

    def add_fellow_werewolf(self, player_id: str) -> None:
        """添加狼人同伴"""
        if player_id not in self._fellow_werewolves:
            self._fellow_werewolves.append(player_id)

    @property
    def fellow_werewolves(self) -> List[str]:
        """获取狼人同伴列表"""
        return self._fellow_werewolves.copy()

    def get_public_info(self) -> PublicInfo:
        """
        获取公开信息
        狼人在公开场合被视为好人，直到被揭穿
        """
        return PublicInfo(
            visible_role="好人",      # 隐藏真实身份
            is_suspicious=False,
            speech_style="normal",
            claims="平民"
        )

    def get_private_info(self, viewer: Optional[Role] = None) -> PrivateInfo:
        """
        获取私有信息
        只有狼人能看到其他狼人的真实身份
        """
        # 只有狼人同伴能看到真实身份
        if viewer is not None and viewer.role_type == "werewolf":
            return PrivateInfo(
                actual_role="werewolf",
                fellow_werewolves=self._fellow_werewolves
            )
        return PrivateInfo()

    def night_action(self, game_state: "GamePhaseState") -> "NightActionResult":
        """
        夜间行动：击杀一名玩家

        Args:
            game_state: 游戏阶段状态，包含：
                - alive_players: 存活玩家列表
                - previous_kills: 昨晚被击杀的玩家（女巫用）

        Returns:
            WerewolfKillResult: 狼人击杀结果
            NoNightActionResult: 无行动结果
        """
        if not self.is_alive:
            return NoNightActionResult(
                action=ActionType.PASS,
                reason="角色已死亡"
            )

        alive_players = game_state.alive_players
        # 排除自己
        candidates = [p for p in alive_players if p != self.player_id]

        if not candidates:
            return NoNightActionResult(
                action=ActionType.PASS,
                reason="没有可击杀的目标"
            )

        # TODO: 实现狼人AI决策逻辑，选择击杀目标
        # 目前返回随机选择，后续接入AI决策
        selected_target = candidates[0]

        self.use_ability("kill")

        return WerewolfKillResult(
            action=ActionType.KILL,
            target=selected_target,
            success=True
        )

    def day_action(self, game_state: "GamePhaseState") -> "DayActionResult":
        """
        白天行动：发言和投票

        狼人白天需要伪装成好人进行发言和投票。

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

        # TODO: 实现狼人的白天AI发言和投票逻辑
        # 需要考虑：
        # - 伪装策略：假装是某种好人角色
        # - 煽动投票：引导票型指向好人
        # - 自保策略：避免被怀疑

        return VoteResult(
            action=ActionType.VOTE,
            target=None,   # 待AI决策
            speech=None,   # 待AI生成
            reasoning=None
        )

    def get_fake_role(self) -> str:
        """
        获取伪装身份
        狼人白天可以假装成某种好人角色
        """
        # TODO: 根据局势选择最有利的伪装身份
        return "平民"
