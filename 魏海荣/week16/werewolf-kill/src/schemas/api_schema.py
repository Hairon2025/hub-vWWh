"""
API 请求/响应模型
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============ 请求模型 ============

class CreateGameRequest(BaseModel):
    """创建游戏请求"""
    player_ids: Optional[List[str]] = Field(
        default=None,
        description="自定义玩家ID列表，默认5人"
    )
    game_id: Optional[str] = Field(
        default=None,
        description="自定义游戏ID，默认自动生成"
    )


class CreateAgentsRequest(BaseModel):
    """创建代理请求"""
    decision_styles: Optional[Dict[str, str]] = Field(
        default=None,
        description="角色决策风格映射 {role_type: style}，可选值: aggressive, cautious, balanced"
    )


class NightActionRequest(BaseModel):
    """夜间行动请求（可选，用于自定义行为）"""
    werewolf_target: Optional[str] = Field(
        default=None,
        description="狼人击杀目标玩家ID"
    )
    prophet_target: Optional[str] = Field(
        default=None,
        description="预言家查验目标玩家ID"
    )
    witch_save: bool = Field(
        default=False,
        description="女巫是否救人"
    )
    witch_poison_target: Optional[str] = Field(
        default=None,
        description="女巫毒杀目标玩家ID"
    )


class DayActionRequest(BaseModel):
    """白天行动请求（可选）"""
    hunter_shoot_target: Optional[str] = Field(
        default=None,
        description="猎人追刀目标玩家ID"
    )


# ============ 响应模型 ============

class GameInfoResponse(BaseModel):
    """游戏基本信息响应"""
    game_id: str
    phase: str
    day: int
    alive_players: List[str]
    dead_players: List[str]
    is_game_over: bool
    winner: Optional[str] = None


class CreateGameResponse(BaseModel):
    """创建游戏响应"""
    game_id: str
    player_ids: List[str]
    settings: Dict[str, Any]


class NightResultResponse(BaseModel):
    """夜间阶段响应"""
    day_number: int
    events: List[Dict[str, Any]]
    deaths: List[Dict[str, Any]]
    announcement: str


class DayResultResponse(BaseModel):
    """白天阶段响应"""
    day_number: int
    events: List[Dict[str, Any]]
    deaths: List[Dict[str, Any]]
    final_announcement: str


class GameRecordResponse(BaseModel):
    """游戏记录响应"""
    game_id: str
    game_info: Dict[str, Any]
    players: List[Dict[str, Any]]
    day_records: List[Dict[str, Any]]
    game_result: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None
