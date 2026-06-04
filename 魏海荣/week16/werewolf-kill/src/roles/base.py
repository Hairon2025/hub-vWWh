"""
角色模块 - 狼人杀游戏中的所有角色定义

角色设计遵循以下原则：
- 每个角色有独立的胜利条件和行为策略
- 角色之间存在信息不对称
- 角色行为分为：夜间行动、白天发言、投票
"""

from abc import ABC, abstractmethod
from typing import Optional, List, TYPE_CHECKING

# 导入 Schema 类型
if TYPE_CHECKING:
    from schemas.roles_schema import (
        NightActionResult,
        DayActionResult,
        PublicInfo,
        PrivateInfo,
        GamePhaseState,
        Ability,
    )

from schemas.roles_schema import Ability


class Role(ABC):
    """
    角色基类

    所有具体角色都继承此类。每个角色拥有：
    - role_type: 角色类型
    - camp: 所属阵营
    - abilities: 角色能力列表
    - is_alive: 是否存活
    - player_id: 绑定的玩家ID
    """

    def __init__(
        self,
        role_type: str,
        camp: str,
        abilities: Optional[List[Ability]] = None,
        is_alive: bool = True,
        player_id: Optional[str] = None,
    ):
        self.role_type = role_type
        self.camp = camp
        self.abilities: List[Ability] = abilities or []
        self.is_alive = is_alive
        self.player_id = player_id

    @property
    def name(self) -> str:
        """获取角色显示名称"""
        return self.role_type

    @property
    def win_condition(self) -> str:
        """获取胜利条件描述"""
        if self.camp == "werewolf":
            return "消灭所有好人阵营玩家"
        return "消灭所有狼人"

    @abstractmethod
    def get_public_info(self) -> "PublicInfo":
        """
        获取公开信息
        其他玩家能看到的信息（不暴露真实身份）
        """
        pass

    @abstractmethod
    def get_private_info(self, viewer: Optional["Role"] = None) -> "PrivateInfo":
        """
        获取私有信息
        只有特定角色能看到的信息
        """
        pass

    @abstractmethod
    def night_action(self, game_state: "GamePhaseState") -> "NightActionResult":
        """
        夜间行动
        返回行动结果，如无行动则返回 NoNightActionResult
        """
        pass

    @abstractmethod
    def day_action(self, game_state: "GamePhaseState") -> "DayActionResult":
        """
        白天行动（发言、投票等）
        返回行动结果
        """
        pass

    def die(self, reason: str = "") -> None:
        """角色死亡"""
        self.is_alive = False

    def revive(self) -> None:
        """角色复活（用于猎人等情况）"""
        self.is_alive = True

    def use_ability(self, ability_name: str) -> bool:
        """
        使用能力

        Returns:
            True: 使用成功
            False: 能力不存在或无法使用
        """
        for ability in self.abilities:
            if ability.name == ability_name:
                return ability.use()
        return False

    def get_ability(self, ability_name: str) -> Optional[Ability]:
        """获取指定名称的能力"""
        for ability in self.abilities:
            if ability.name == ability_name:
                return ability
        return None

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "role_type": self.role_type,
            "camp": self.camp,
            "is_alive": self.is_alive,
            "player_id": self.player_id,
            "abilities": [a.model_dump() for a in self.abilities]
        }
