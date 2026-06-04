"""
API 路由定义
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status

from src.game_engine.manager import get_game_manager
from src.schemas.api_schema import (
    CreateGameRequest,
    CreateGameResponse,
    CreateAgentsRequest,
    GameInfoResponse,
    NightResultResponse,
    DayResultResponse,
    GameRecordResponse,
    ErrorResponse,
)


router = APIRouter(prefix="/api/games", tags=["games"])


def _model_to_dict(obj) -> dict:
    """将模型对象转换为字典，处理datetime等类型"""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    elif hasattr(obj, "dict"):
        return obj.dict()
    return obj


@router.post("", response_model=CreateGameResponse)
async def create_game(request: Optional[CreateGameRequest] = None):
    """
    创建并开始新游戏

    - **player_ids**: 自定义玩家ID列表（可选），默认5人
    - **game_id**: 自定义游戏ID（可选）
    """
    manager = get_game_manager()

    player_ids = request.player_ids if request else None
    game_id = request.game_id if request else None

    instance = manager.create_game(player_ids=player_ids, game_id=game_id)
    engine = instance.engine

    return CreateGameResponse(
        game_id=instance.game_id,
        player_ids=engine.player_ids,
        settings={
            "mode": "SIMPLE",
            "player_count": len(engine.player_ids),
            "werewolf_count": sum(
                1 for p in engine.players.values() if p.role_type == "werewolf"
            ),
        },
    )


@router.get("", response_model=list)
async def list_games():
    """列出所有游戏"""
    manager = get_game_manager()
    return manager.list_games()


@router.get("/{game_id}", response_model=GameInfoResponse)
async def get_game(game_id: str):
    """获取游戏当前状态"""
    manager = get_game_manager()
    instance = manager.get_game(game_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    engine = instance.engine
    winner = None
    if engine.winner:
        winner = engine.winner.value if hasattr(engine.winner, "value") else str(engine.winner)

    return GameInfoResponse(
        game_id=game_id,
        phase=engine.current_phase,
        day=engine.current_day,
        alive_players=engine.alive_players,
        dead_players=engine.dead_players,
        is_game_over=engine.is_game_over,
        winner=winner,
    )


@router.post("/{game_id}/agents", response_model=GameInfoResponse)
async def create_agents(game_id: str, request: Optional[CreateAgentsRequest] = None):
    """
    为游戏创建AI代理

    - **decision_styles**: 角色决策风格映射 {role_type: style}
      - aggressive: 激进策略
      - cautious: 保守策略
      - balanced: 平衡策略
    """
    manager = get_game_manager()
    instance = manager.get_game(game_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    decision_styles = request.decision_styles if request else None
    instance.engine.create_agents(decision_styles=decision_styles)

    return GameInfoResponse(
        game_id=game_id,
        phase=instance.engine.current_phase,
        day=instance.engine.current_day,
        alive_players=instance.engine.alive_players,
        dead_players=instance.engine.dead_players,
        is_game_over=instance.engine.is_game_over,
        winner=instance.engine.winner.value if instance.engine.winner else None,
    )


@router.post("/{game_id}/night", response_model=NightResultResponse)
async def run_night(game_id: str):
    """
    执行夜间阶段

    流程：狼人击杀 -> 预言家查验 -> 女巫用药
    """
    manager = get_game_manager()
    instance = manager.get_game(game_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    engine = instance.engine

    if engine.is_game_over:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game is already over",
        )

    result = engine.run_night()

    # 构建公告
    deaths = result.deaths if hasattr(result, "deaths") else []
    if deaths:
        death_names = [d.player_id for d in deaths]
        announcement = f"昨晚死亡：{', '.join(death_names)}"
    else:
        announcement = "昨晚是平安夜"

    return NightResultResponse(
        day_number=result.day_number if hasattr(result, "day_number") else engine.current_day,
        events=[_model_to_dict(e) for e in (result.events if hasattr(result, "events") else [])],
        deaths=[_model_to_dict(d) for d in deaths],
        announcement=announcement,
    )


@router.post("/{game_id}/day", response_model=DayResultResponse)
async def run_day(game_id: str):
    """
    执行白天阶段

    流程：公告死亡 -> 遗言 -> 发言 -> 投票 -> 表决
    """
    manager = get_game_manager()
    instance = manager.get_game(game_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    engine = instance.engine

    if engine.is_game_over:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game is already over",
        )

    if engine.current_phase == "day":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already in day phase",
        )

    result = engine.run_day()

    return DayResultResponse(
        day_number=result.day_number,
        events=[_model_to_dict(e) for e in result.events],
        deaths=[_model_to_dict(d) for d in result.deaths],
        final_announcement=result.final_announcement or "",
    )


@router.post("/{game_id}/next", response_model=GameInfoResponse)
async def run_next_phase(game_id: str):
    """
    执行下一个阶段（自动判断是夜晚还是白天）
    """
    manager = get_game_manager()
    instance = manager.get_game(game_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    engine = instance.engine

    if engine.is_game_over:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game is already over",
        )

    if engine.current_phase == "night":
        engine.run_night()
    else:
        engine.run_day()

    # 检查胜负
    is_over, winner = engine.check_win_condition()

    return GameInfoResponse(
        game_id=game_id,
        phase=engine.current_phase,
        day=engine.current_day,
        alive_players=engine.alive_players,
        dead_players=engine.dead_players,
        is_game_over=engine.is_game_over,
        winner=winner.value if winner else None,
    )


@router.post("/{game_id}/auto", response_model=GameRecordResponse)
async def auto_run(game_id: str):
    """
    自动执行游戏直到结束

    自动运行所有剩余回合，返回最终游戏记录
    """
    manager = get_game_manager()
    instance = manager.get_game(game_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    engine = instance.engine

    if engine.is_game_over:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game is already over",
        )

    # 确保代理已创建
    if not engine.player_agents:
        engine.create_agents()

    # 自动运行直到游戏结束
    while not engine.is_game_over:
        if engine.current_phase == "night":
            engine.run_night()
        else:
            engine.run_day()

        is_over, winner = engine.check_win_condition()

    # 获取游戏记录
    record = engine.get_game_record()

    return GameRecordResponse(
        game_id=game_id,
        game_info=_model_to_dict(record.game_info),
        players=[_model_to_dict(p) for p in record.players],
        day_records=[
            {
                "day_number": dr.day_number,
                "night_result": _model_to_dict(dr.night_result) if dr.night_result else None,
                "day_result": _model_to_dict(dr.day_result) if dr.day_result else None,
            }
            for dr in record.day_records
        ],
        game_result=_model_to_dict(record.game_result) if record.game_result else None,
    )


@router.get("/{game_id}/record", response_model=GameRecordResponse)
async def get_game_record(game_id: str):
    """获取完整游戏记录"""
    manager = get_game_manager()
    instance = manager.get_game(game_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    record = instance.engine.get_game_record()

    return GameRecordResponse(
        game_id=game_id,
        game_info=_model_to_dict(record.game_info),
        players=[_model_to_dict(p) for p in record.players],
        day_records=[
            {
                "day_number": dr.day_number,
                "night_result": _model_to_dict(dr.night_result) if dr.night_result else None,
                "day_result": _model_to_dict(dr.day_result) if dr.day_result else None,
            }
            for dr in record.day_records
        ],
        game_result=_model_to_dict(record.game_result) if record.game_result else None,
    )


@router.delete("/{game_id}", response_model=dict)
async def delete_game(game_id: str):
    """删除游戏"""
    manager = get_game_manager()
    success = manager.delete_game(game_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    return {"message": f"Game {game_id} deleted"}
