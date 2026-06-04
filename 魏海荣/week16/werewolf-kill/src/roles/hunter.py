"""
猎人角色实现

阵营：好人阵营
胜利条件：消灭所有狼人

猎人特点：
- 被狼人击杀或投票出局时可以带走一名玩家
- 如果被女巫毒死则不能开枪
- 死亡时必须立即发动技能，不能放弃
- 白天死亡也可以发动技能
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
    HunterShootResult,
    NoNightActionResult,
    VoteResult,
    PublicInfo,
    PrivateInfo,
    ActionType,
    Ability,
)

from .base import Role


class Hunter(Role):
    """
    猎人

    好人阵营的神职角色，拥有追刀能力。
    是好人阵营的强力输出角色。
    """

    def __init__(self, player_id: Optional[str] = None):
        super().__init__(
            role_type="hunter",
            camp="village",
            player_id=player_id,
            abilities=[
                Ability(
                    name="shoot",
                    description="死亡时带走一名玩家",
                    can_use=True,
                    max_uses=1,  # 只能使用一次
                )
            ]
        )
        self._can_shoot: bool = True    # 是否可以开枪
        self._death_cause: Optional[str] = None  # 死亡原因
        self._target_to_kill: Optional[str] = None  # 要带走的目标

    def get_public_info(self) -> PublicInfo:
        """
        获取公开信息
        猎人在发动技能前通常隐藏身份
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
        只有猎人自己知道是否可以开枪
        """
        # 只有猎人自己能看到开枪状态
        if viewer is not None and viewer.role_type == "hunter":
            return PrivateInfo(
                can_shoot=self._can_shoot,
                extra_data={
                    "death_cause": self._death_cause
                }
            )
        return PrivateInfo()

    def die(self, reason: str = "") -> None:
        """
        猎人死亡

        猎人在不同死因下有不同的行为：
        - 被狼人击杀：可以开枪带走一人
        - 被投票出局：可以开枪带走一人
        - 被女巫毒死：不能开枪
        """
        self.is_alive = False
        self._death_cause = reason

        # 女巫毒死不能开枪
        if reason == "witch_poison":
            self._can_shoot = False

    def set_shoot_target(self, target: str) -> bool:
        """
        设置开枪目标
        必须在死亡时立即选择目标
        """
        if not self._can_shoot:
            return False
        if not self.is_alive:
            return False

        self._target_to_kill = target
        return True

    def night_action(self, game_state: "GamePhaseState") -> "NightActionResult":
        """
        夜间行动：猎人夜间不会主动行动

        猎人的追刀发生在死亡时，不是夜间阶段

        Returns:
            NoNightActionResult: 无行动结果
        """
        return NoNightActionResult(
            action=ActionType.PASS,
            reason="猎人夜间不行动"
        )

    def day_action(self, game_state: "GamePhaseState") -> "DayActionResult":
        """
        白天行动：发言和投票

        猎人白天可以正常发言和投票。
        如果已经死亡但还未追刀，需要在白天完成追刀。

        Args:
            game_state: 游戏阶段状态

        Returns:
            HunterShootResult: 追刀结果（如果需要追刀）
            VoteResult: 投票结果（正常白天行动）
        """
        # 如果已经死亡但还没有追刀
        if not self.is_alive and self._can_shoot and self._target_to_kill:
            return HunterShootResult(
                action=ActionType.SHOOT,
                target=self._target_to_kill,
                must_act=True,
                success=True
            )

        # 正常白天行动
        return VoteResult(
            action=ActionType.VOTE,
            target=None,
            speech=None,
            reasoning=None
        )

    def execute_shoot(self) -> Optional[str]:
        """
        执行开枪
        返回被带走的目标ID，如果没有目标则返回None
        """
        if not self._can_shoot:
            return None

        target = self._target_to_kill
        self.use_ability("shoot")
        self._can_shoot = False
        return target

    @property
    def can_shoot(self) -> bool:
        """是否还可以开枪"""
        return self._can_shoot and self._death_cause != "witch_poison"

    def get_available_targets(self, alive_players: List[str]) -> List[str]:
        """获取可击杀目标列表"""
        return [p for p in alive_players if p != self.player_id]
