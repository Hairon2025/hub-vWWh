"""
女巫角色实现

阵营：好人阵营
胜利条件：消灭所有狼人

女巫特点：
- 拥有一瓶救人药水（只能使用一次）
- 拥有一瓶杀人药水（只能使用一次）
- 第一晚可以知道谁被狼人击杀
- 不能在同一晚同时使用两瓶药水
- 药水使用后无法得知当晚狼人的击杀目标（救人会暴露自己）
"""

from typing import Optional, List, Union, TYPE_CHECKING

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
    WitchSaveResult,
    WitchPoisonResult,
    NoNightActionResult,
    VoteResult,
    PublicInfo,
    PrivateInfo,
    ActionType,
    Ability,
)

from .base import Role


class Witch(Role):
    """
    女巫

    好人阵营的神职角色，拥有救人和毒人的能力。
    是好人阵营的关键保护角色。
    """

    def __init__(self, player_id: Optional[str] = None):
        super().__init__(
            role_type="witch",
            camp="village",
            player_id=player_id,
            abilities=[
                Ability(
                    name="save",
                    description="使用救人药水救活一名被狼人击杀的玩家",
                    can_use=True,
                    max_uses=1,  # 只能使用一次
                ),
                Ability(
                    name="poison",
                    description="使用毒药击杀一名玩家",
                    can_use=True,
                    max_uses=1,  # 只能使用一次
                )
            ]
        )
        self._save_used: bool = False   # 救人药水是否已使用
        self._poison_used: bool = False  # 毒药是否已使用
        self._tonight_killed_by_werewolf: Optional[str] = None  # 今晚狼人击杀的目标

    def get_public_info(self) -> PublicInfo:
        """
        获取公开信息
        女巫通常隐藏身份
        """
        return PublicInfo(
            visible_role="好人",
            is_suspicious=False,
            speech_style="normal",
            claims="平民"
        )

    def get_private_info(self, viewer: Optional[Role] = None) -> PrivateInfo:
        """
        获取私有信息
        只有女巫自己知道药水使用情况和击杀信息
        """
        # 只有女巫自己能看到药水和击杀信息
        if viewer is not None and viewer.role_type == "witch":
            return PrivateInfo(
                save_used=self._save_used,
                poison_used=self._poison_used,
                extra_data={
                    "tonight_killed_by_werewolf": self._tonight_killed_by_werewolf
                }
            )
        return PrivateInfo()

    def set_killed_by_werewolf(self, player_id: str) -> None:
        """设置今晚狼人击杀的目标（由游戏引擎调用）"""
        self._tonight_killed_by_werewolf = player_id

    def night_action(self, game_state: "GamePhaseState") -> "NightActionResult":
        """
        夜间行动：救人或毒人

        决策逻辑：
        - 第一晚通常救人（如果狼人击杀了预言家）
        - 后续根据局势决定是否使用毒药
        - 不能同时救人和毒人

        Args:
            game_state: 游戏阶段状态，包含：
                - previous_kills: 昨晚的击杀玩家列表
                - alive_players: 存活玩家列表

        Returns:
            WitchSaveResult: 救人结果
            WitchPoisonResult: 毒人结果
            NoNightActionResult: 无行动结果
        """
        if not self.is_alive:
            return NoNightActionResult(
                action=ActionType.PASS,
                reason="角色已死亡"
            )

        # 从 game_state 获取狼人击杀目标
        previous_kills = game_state.previous_kills
        alive_players = game_state.alive_players

        killed_target = previous_kills[0] if previous_kills else None
        self._tonight_killed_by_werewolf = killed_target

        # 是否可以救人
        can_save = (
            not self._save_used
            and killed_target is not None
            and killed_target in alive_players
            and killed_target != self.player_id
        )

        # 是否可以毒人
        can_poison = (
            not self._poison_used
            and len([p for p in alive_players if p != self.player_id]) > 1
        )

        # TODO: 实现女巫AI决策逻辑
        # 决策因素：
        # - 救人：保护关键神职（预言家）
        # - 毒人：确认的狼人目标
        # - 都不做：保留药水给后续回合

        # 暂时默认不行动，后续接入AI决策
        if can_save:
            # 示例：救人（实际应由AI决策）
            self.use_ability("save")
            self._save_used = True
            return WitchSaveResult(
                action=ActionType.SAVE,
                target=killed_target,
                used=True,
                success=True
            )

        if can_poison:
            # 示例：毒人（实际应由AI决策）
            poison_target = [p for p in alive_players if p != self.player_id][0]
            # 暂时不执行毒人，等待AI决策
            return NoNightActionResult(
                action=ActionType.PASS,
                reason="等待AI决策毒人目标"
            )

        return NoNightActionResult(
            action=ActionType.PASS,
            reason="无可用行动"
        )

    def day_action(self, game_state: "GamePhaseState") -> "DayActionResult":
        """
        白天行动：发言和投票

        女巫白天需要决定是否公开信息。

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

        # TODO: 实现女巫白天AI逻辑

        return VoteResult(
            action=ActionType.VOTE,
            target=None,
            speech=None,
            reasoning=None
        )

    def use_save(self, target: str) -> bool:
        """使用救人药水"""
        if self._save_used:
            return False
        self._save_used = True
        self.use_ability("save")
        return True

    def use_poison(self, target: str) -> bool:
        """使用毒药"""
        if self._poison_used:
            return False
        self._poison_used = True
        self.use_ability("poison")
        return True

    @property
    def can_save(self) -> bool:
        """是否还可以救人"""
        return not self._save_used

    @property
    def can_poison(self) -> bool:
        """是否还可以毒人"""
        return not self._poison_used
