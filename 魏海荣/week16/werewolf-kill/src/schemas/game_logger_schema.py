"""
游戏运行日志 Schema

记录每次比赛的完整运行过程，支持：
- 游戏事件流式记录（JSONL格式）
- 完整游戏回放
- 后续经验提取
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from src.schemas.roles_schema import RoleType, CampType, ActionType


# ============ 游戏配置 ============

class GameMode(str, Enum):
    """游戏模式"""
    STANDARD = "standard"      # 标准局（4狼人+4神+8村民）
    SIMPLE = "simple"         # 简化局


class GameSettings(BaseModel):
    """游戏设置"""
    mode: GameMode = GameMode.STANDARD
    player_count: int = 12
    werewolf_count: int = 4
    god_count: int = 4
    villager_count: int = 4
    night_order: List[str] = Field(
        default=["werewolf", "prophet", "witch", "hunter"],
        description="夜间行动顺序"
    )


# ============ 游戏元信息 ============

class GameInfo(BaseModel):
    """游戏元信息"""
    game_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    mode: GameMode = GameMode.STANDARD
    settings: GameSettings
    player_ids: List[str] = Field(default_factory=list)


# ============ 玩家信息 ============

class PlayerInfo(BaseModel):
    """玩家初始信息"""
    player_id: str
    role_type: RoleType
    camp: CampType
    seat_number: Optional[int] = None


# ============ 死亡记录 ============

class DeathReason(str, Enum):
    """死亡原因"""
    WEREWOLF_KILL = "werewolf_kill"
    VOTE_EXILE = "vote_exile"
    HUNTER_SHOOT = "hunter_shoot"
    WITCH_POISON = "witch_poison"
    OVERFLOW = "overflow"  # 狼人自爆


class DeathRecord(BaseModel):
    """死亡记录"""
    player_id: str
    day: int
    phase: Literal["night", "day"] = "night"
    reason: DeathReason
    killer: Optional[str] = None  # 谁造成的死亡（狼人/猎人/投票）
    last_words: Optional[str] = None  # 遗言


# ============ 事件基类 ============

class BaseEvent(BaseModel):
    """事件基类"""
    event_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    day: int
    phase: Literal["night", "day"]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============ 夜间事件 ============

class NightEventType(str, Enum):
    """夜间事件类型"""
    WEREWOLF_KILL = "werewolf_kill"
    PROPHET_CHECK = "prophet_check"
    WITCH_SAVE = "witch_save"
    WITCH_POISON = "witch_poison"
    GUARD_GUARD = "guard_guard"
    HUNTER_SHOOT = "hunter_shoot"
    NO_DEATH = "no_death"  # 平安夜


class WerewolfKillEvent(BaseEvent):
    """狼人击杀事件"""
    event_type: Literal[NightEventType.WEREWOLF_KILL] = NightEventType.WEREWOLF_KILL
    actors: List[str] = Field(description="参与击杀的狼人ID列表")
    target: str
    success: bool = True
    protected_by_guard: bool = False
    saved_by_witch: bool = False


class ProphetCheckEvent(BaseEvent):
    """预言家查验事件"""
    event_type: Literal[NightEventType.PROPHET_CHECK] = NightEventType.PROPHET_CHECK
    actor: str  # 预言家ID
    target: str
    is_werewolf: bool
    target_role: Optional[RoleType] = None


class WitchSaveEvent(BaseEvent):
    """女巫救人事件"""
    event_type: Literal[NightEventType.WITCH_SAVE] = NightEventType.WITCH_SAVE
    actor: str
    target: str
    used: bool = True


class WitchPoisonEvent(BaseEvent):
    """女巫毒人事件"""
    event_type: Literal[NightEventType.WITCH_POISON] = NightEventType.WITCH_POISON
    actor: str
    target: str
    used: bool = True


class GuardGuardEvent(BaseEvent):
    """守卫守护事件"""
    event_type: Literal[NightEventType.GUARD_GUARD] = NightEventType.GUARD_GUARD
    actor: str
    target: str
    same_target_night: int = Field(default=0, description="连续守护同目标的夜晚数")


class HunterShootEvent(BaseEvent):
    """猎人追刀事件"""
    event_type: Literal[NightEventType.HUNTER_SHOOT] = NightEventType.HUNTER_SHOOT
    actor: str
    target: str
    used: bool = True


class NoDeathEvent(BaseEvent):
    """平安夜事件"""
    event_type: Literal[NightEventType.NO_DEATH] = NightEventType.NO_DEATH
    reason: str = "no_death"


class NightResult(BaseModel):
    """夜间阶段结果"""
    night_number: int
    events: List[Any] = Field(default_factory=list)
    deaths: List[DeathRecord] = Field(default_factory=list)
    announcement: Optional[str] = None  # 白天公告内容


# ============ 白天事件 ============

class DayEventType(str, Enum):
    """白天事件类型"""
    SPEECH = "speech"
    VOTE = "vote"
    REVEAL = "reveal"
    EXILE = "exile"
    ANNOUNCEMENT = "announcement"
    PHASE_TRANSITION = "phase_transition"


class SpeechEvent(BaseEvent):
    """发言事件"""
    event_type: Literal[DayEventType.SPEECH] = DayEventType.SPEECH
    speaker: str
    content: str
    speech_order: int = Field(description="发言顺序")
    # 压缩字段：是否包含关键信息
    is_key_speech: bool = False
    key_info_summary: Optional[str] = Field(
        default=None,
        description="关键信息摘要（如：'声称是预言家，声称查验了X是狼人'）"
    )


class VoteEvent(BaseEvent):
    """投票事件"""
    event_type: Literal[DayEventType.VOTE] = DayEventType.VOTE
    voter: str
    target: Optional[str] = None  # None表示弃票
    vote_order: int = Field(description="投票顺序")


class ExileEvent(BaseEvent):
    """投票出局事件"""
    event_type: Literal[DayEventType.EXILE] = DayEventType.EXILE
    target: str
    votes_received: int
    total_votes: int
    is_revoted: bool = False  # 是否需要重投


class RevealEvent(BaseEvent):
    """身份揭示事件"""
    event_type: Literal[DayEventType.REVEAL] = DayEventType.REVEAL
    actor: str
    role: RoleType
    reason: str = "death_reveal"  # death_reveal / voluntary_reveal


class AnnouncementEvent(BaseEvent):
    """公告事件"""
    event_type: Literal[DayEventType.ANNOUNCEMENT] = DayEventType.ANNOUNCEMENT
    content: str
    announcement_type: Literal["death", "phase", "system", "result"] = "system"


class DayResult(BaseModel):
    """白天阶段结果"""
    day_number: int
    events: List[Any] = Field(default_factory=list)
    deaths: List[DeathRecord] = Field(default_factory=list)
    final_announcement: Optional[str] = None


# ============ 游戏记录 ============

class DayRecord(BaseModel):
    """每天的记录"""
    day_number: int
    night_result: Optional[NightResult] = None
    day_result: Optional[DayResult] = None


# ============ 游戏结果 ============

class Winner(str, Enum):
    """胜利方"""
    WEREWOLF = "werewolf"
    VILLAGE = "village"
    DRAW = "draw"


class PlayerResult(BaseModel):
    """玩家个人结果"""
    player_id: str
    role_type: RoleType
    camp: CampType
    is_alive: bool
    survived_until_day: Optional[int] = None
    death_reason: Optional[DeathReason] = None
    final_speech: Optional[str] = None


class GameResult(BaseModel):
    """游戏结果"""
    winner: Winner
    survival_players: List[str]
    player_results: List[PlayerResult]
    total_days: int
    end_time: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============ 完整游戏记录 ============

class GameRecord(BaseModel):
    """完整游戏记录"""
    game_info: GameInfo
    players: List[PlayerInfo]
    day_records: List[DayRecord] = Field(default_factory=list)
    game_result: Optional[GameResult] = None

    # 便捷方法
    def get_all_events(self) -> List[Any]:
        """获取所有事件（按时间顺序）"""
        events = []
        for day_record in self.day_records:
            if day_record.night_result:
                events.extend(day_record.night_result.events)
            if day_record.day_result:
                events.extend(day_record.day_result.events)
        return events

    def get_player_death_day(self, player_id: str) -> Optional[int]:
        """获取某玩家死亡的日期"""
        for day_record in self.day_records:
            for death in day_record.night_result.deaths if day_record.night_result else []:
                if death.player_id == player_id:
                    return day_record.day_number
            for death in day_record.day_result.deaths if day_record.day_result else []:
                if death.player_id == player_id:
                    return day_record.day_number
        return None


# ============ 事件日志格式（用于JSONL流式写入）===========

class EventLogEntry(BaseModel):
    """
    事件日志条目（用于JSONL格式存储）

    每行一个事件，便于流式追加和读取
    """
    event_type: str
    game_id: str
    day: int
    phase: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @classmethod
    def from_event(cls, game_id: str, day: int, phase: str, event: BaseEvent) -> "EventLogEntry":
        """从事件对象创建日志条目"""
        return cls(
            event_type=event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
            game_id=game_id,
            day=day,
            phase=phase,
            data=event.model_dump()
        )
