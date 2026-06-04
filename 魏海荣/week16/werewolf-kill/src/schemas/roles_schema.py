"""
角色相关的数据结构定义

统一管理所有角色的输入输出格式，提供类型安全的接口定义。
"""

from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field
from enum import Enum


class ActionType(str, Enum):
    """行动类型枚举"""
    # 夜间行动
    KILL = "kill"              # 狼人击杀
    CHECK = "check"            # 预言家查验
    SAVE = "save"              # 女巫救人
    POISON = "poison"          # 女巫毒人
    GUARD = "guard"            # 守卫守护
    SHOOT = "shoot"            # 猎人追刀

    # 白天行动
    VOTE = "vote"              # 投票
    SPEAK = "speak"            # 发言
    REVEAL = "reveal"          # 揭示身份
    PASS = "pass"              # 跳过（不行动）


class CampType(str, Enum):
    """阵营类型"""
    WEREWOLF = "werewolf"
    VILLAGE = "village"


class RoleType(str, Enum):
    """角色类型"""
    WEREWOLF = "werewolf"
    PROPHET = "prophet"
    WITCH = "witch"
    HUNTER = "hunter"
    VILLAGER = "villager"
    GUARD = "guard"
    IDIOT = "idiot"


# ============ 夜间行动结果 ============

class NightActionBase(BaseModel):
    """夜间行动基类"""
    action: ActionType
    success: bool = True
    message: Optional[str] = None


class WerewolfKillResult(NightActionBase):
    """
    狼人击杀结果

    Attributes:
        action: 固定为 ActionType.KILL
        target: 被击杀的玩家ID
        success: 是否成功（可能因保护而失败）
    """
    action: Literal[ActionType.KILL] = ActionType.KILL
    target: str


class ProphetCheckResult(NightActionBase):
    """
    预言家查验结果

    Attributes:
        action: 固定为 ActionType.CHECK
        target: 被查验的玩家ID
        is_werewolf: 该玩家是否为狼人
        role_name: 该玩家的真实角色名称
    """
    action: Literal[ActionType.CHECK] = ActionType.CHECK
    target: str
    is_werewolf: bool
    role_name: str


class WitchSaveResult(NightActionBase):
    """
    女巫救人结果

    Attributes:
        action: 固定为 ActionType.SAVE
        target: 被救的玩家ID
        used: 是否成功使用药水
    """
    action: Literal[ActionType.SAVE] = ActionType.SAVE
    target: str
    used: bool


class WitchPoisonResult(NightActionBase):
    """
    女巫毒人结果

    Attributes:
        action: 固定为 ActionType.POISON
        target: 被毒的玩家ID
        used: 是否成功使用毒药
    """
    action: Literal[ActionType.POISON] = ActionType.POISON
    target: str
    used: bool


class HunterShootResult(NightActionBase):
    """
    猎人追刀结果

    Attributes:
        action: 固定为 ActionType.SHOOT
        target: 被带走的玩家ID
        must_act: 是否必须行动（死亡时必须追刀）
    """
    action: Literal[ActionType.SHOOT] = ActionType.SHOOT
    target: str
    must_act: bool = True


class GuardResult(NightActionBase):
    """
    守卫守护结果

    Attributes:
        action: 固定为 ActionType.GUARD
        target: 被守护的玩家ID
    """
    action: Literal[ActionType.GUARD] = ActionType.GUARD
    target: str


class NoNightActionResult(BaseModel):
    """
    无夜间行动结果

    当角色选择不进行任何夜间行动时返回
    """
    action: Literal[ActionType.PASS] = ActionType.PASS
    reason: Optional[str] = None


# 夜间行动联合类型
NightActionResult = Union[
    WerewolfKillResult,
    ProphetCheckResult,
    WitchSaveResult,
    WitchPoisonResult,
    HunterShootResult,
    GuardResult,
    NoNightActionResult,
]


# ============ 白天行动结果 ============

class DayActionBase(BaseModel):
    """白天行动基类"""
    action: ActionType


class VoteResult(DayActionBase):
    """
    投票结果

    Attributes:
        action: 固定为 ActionType.VOTE
        target: 被投票的玩家ID，None表示弃票
        speech: 发言内容
        reasoning: 投票理由（可选，用于日志）
    """
    action: Literal[ActionType.VOTE] = ActionType.VOTE
    target: Optional[str] = None
    speech: Optional[str] = None
    reasoning: Optional[str] = None


class SpeakResult(DayActionBase):
    """
    发言结果

    Attributes:
        action: 固定为 ActionType.SPEAK
        content: 发言内容
        emotion: 发言情绪（可选）
        fake_role: 伪装身份（狼人专用）
    """
    action: Literal[ActionType.SPEAK] = ActionType.SPEAK
    content: str
    emotion: Optional[str] = None
    fake_role: Optional[str] = None


class RevealResult(DayActionBase):
    """
    揭示身份结果

    Attributes:
        action: 固定为 ActionType.REVEAL
        revealed: 是否揭示了真实身份
        role: 揭示的角色类型
        target_players: 指向的目标玩家（如预言家查验了谁）
    """
    action: Literal[ActionType.REVEAL] = ActionType.REVEAL
    revealed: bool
    role: Optional[RoleType] = None
    target_players: List[str] = Field(default_factory=list)


class NoDayActionResult(BaseModel):
    """
    无白天行动结果

    当角色死亡或选择跳过时返回
    """
    action: Literal[ActionType.PASS] = ActionType.PASS
    reason: Optional[str] = None


# 白天行动联合类型
DayActionResult = Union[
    VoteResult,
    SpeakResult,
    RevealResult,
    NoDayActionResult,
]


# ============ 信息共享结构 ============

class PublicInfo(BaseModel):
    """
    公开信息

    所有玩家都能看到的信息
    """
    visible_role: str = "好人"      # 对外显示的角色（狼人隐藏真实身份）
    is_suspicious: bool = False     # 是否可疑
    speech_style: str = "normal"    # 发言风格
    claims: str = "平民"            # 声称的身份


class PrivateInfo(BaseModel):
    """
    私有信息

    只有特定角色能看到的信息
    """
    actual_role: Optional[str] = None
    fellow_werewolves: List[str] = Field(default_factory=list)  # 狼人同伴
    checked_players: Dict[str, bool] = Field(default_factory=dict)  # 查验记录 {player_id: is_werewolf}
    checked_roles: Dict[str, str] = Field(default_factory=dict)  # 查验角色记录 {player_id: role_name}
    save_used: bool = False
    poison_used: bool = False
    can_shoot: bool = True
    extra_data: Dict[str, Optional[str]] = Field(default_factory=dict)  # 额外数据


# ============ 角色状态 ============

class RoleStatus(BaseModel):
    """
    角色状态

    描述一个角色在某个时刻的完整状态
    """
    player_id: str
    role_type: RoleType
    camp: CampType
    is_alive: bool = True
    public_info: PublicInfo
    private_info: Optional[PrivateInfo] = None
    abilities_status: Dict[str, bool] = Field(default_factory=dict)  # 能力是否可用


# ============ 游戏状态相关 ============

class PlayerState(BaseModel):
    """
    玩家状态

    用于在游戏引擎和角色之间传递玩家信息
    """
    player_id: str
    role: Optional[RoleType] = None
    is_alive: bool = True
    is_suspicious: float = 0.0  # 可疑度 0.0-1.0


class GamePhaseState(BaseModel):
    """
    游戏阶段状态

    传递给角色用于决策的上下文信息
    """
    phase: str  # "night" / "day"
    day_number: int
    alive_players: List[str]
    dead_players: List[str]
    previous_kills: List[str] = Field(default_factory=list)  # 昨晚的击杀
    current_speaker: Optional[str] = None
    vote_records: Dict[str, str] = Field(default_factory=dict)  # player_id -> voted_for
    speech_records: Dict[str, str] = Field(default_factory=dict)  # player_id -> speech
    checked_history: Dict[str, bool] = Field(default_factory=dict)  # player_id -> is_werewolf


# ============ 死亡原因 ============

class DeathReason(str, Enum):
    """死亡原因枚举"""
    WEREWOLF_KILL = "werewolf_kill"    # 狼人击杀
    VOTE = "vote"                       # 投票出局
    HUNTER_SHOOT = "hunter_shoot"      # 猎人追刀
    WITCH_POISON = "witch_poison"      # 女巫毒杀
    DEVIL = "devil"                    # 恶魔（进阶角色）
    OVERFLOW = "overflow"              # 狼人自爆（进阶角色）


# ============ 角色能力 ============

class Ability(BaseModel):
    """
    角色能力定义

    描述一个角色的具体能力，包含使用限制和当前使用次数。
    """
    name: str                          # 能力名称，如 "kill", "check", "save"
    description: str = ""              # 能力描述
    can_use: bool = True               # 能力是否可用
    max_uses: Optional[int] = None     # 最大使用次数，None 表示无限制
    used_count: int = 0                # 已使用次数

    def is_available(self) -> bool:
        """检查能力是否还可以使用"""
        if not self.can_use:
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        return True

    def use(self) -> bool:
        """
        使用一次能力

        Returns:
            True: 使用成功
            False: 无法使用（已达上限或不可用）
        """
        if not self.is_available():
            return False
        self.used_count += 1
        return True

    def reset(self) -> None:
        """重置能力使用次数"""
        self.used_count = 0
        self.can_use = True
