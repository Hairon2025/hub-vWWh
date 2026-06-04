"""
游戏日志模块

负责保存游戏记录到文件，支持：
- JSONL 格式的事件流式记录
- 完整的 GameRecord JSON 文件
- 自动创建 logs 目录
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any, Dict

from src.schemas.game_logger_schema import (
    GameRecord,
    GameInfo,
    GameSettings,
    GameMode,
    PlayerInfo,
    DayRecord,
    NightResult,
    DayResult,
    GameResult,
    PlayerResult,
    Winner,
    DeathRecord,
    EventLogEntry,
)


class GameLogger:
    """
    游戏日志记录器

    负责将游戏事件写入文件，支持：
    - 实时写入 JSONL 格式的事件流
    - 游戏结束后生成完整的 GameRecord JSON
    """

    def __init__(self, logs_dir: Optional[Path] = None):
        if logs_dir is None:
            logs_dir = Path(__file__).parent.parent.parent / "logs"
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.game_id: Optional[str] = None
        self.jsonl_path: Optional[Path] = None
        self._events: List[Dict[str, Any]] = []

    def start_game(self, game_id: str, settings: GameSettings, player_ids: List[str]) -> GameInfo:
        """
        开始新游戏，创建日志文件

        Args:
            game_id: 游戏ID
            settings: 游戏设置
            player_ids: 玩家ID列表

        Returns:
            GameInfo 对象
        """
        self.game_id = game_id
        self._events = []

        # 创建 JSONL 文件
        self.jsonl_path = self.logs_dir / f"{game_id}.jsonl"
        self.jsonl_path.touch(exist_ok=True)

        game_info = GameInfo(
            game_id=game_id,
            start_time=datetime.now(),
            mode=GameMode.SIMPLE,  # 简化局
            settings=settings,
            player_ids=player_ids,
        )

        self._write_event({
            "event": "game_start",
            "game_id": game_id,
            "data": game_info.model_dump(),
            "timestamp": datetime.now().isoformat(),
        })

        return game_info

    def _write_event(self, event: Dict[str, Any]) -> None:
        """写入单个事件到 JSONL 文件"""
        if self.jsonl_path:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        self._events.append(event)

    def log_night_phase(self, night_number: int, events: List[Any], deaths: List[DeathRecord]) -> None:
        """记录夜间阶段"""
        self._write_event({
            "event": "night_phase",
            "game_id": self.game_id,
            "night_number": night_number,
            "data": {
                "events": [e.model_dump() if hasattr(e, 'model_dump') else str(e) for e in events],
                "deaths": [d.model_dump() for d in deaths],
            },
            "timestamp": datetime.now().isoformat(),
        })

    def log_day_phase(self, day_number: int, events: List[Any], deaths: List[DeathRecord]) -> None:
        """记录白天阶段"""
        self._write_event({
            "event": "day_phase",
            "game_id": self.game_id,
            "day_number": day_number,
            "data": {
                "events": [e.model_dump() if hasattr(e, 'model_dump') else str(e) for e in events],
                "deaths": [d.model_dump() for d in deaths],
            },
            "timestamp": datetime.now().isoformat(),
        })

    def log_speech(self, day: int, speaker: str, content: str, speech_order: int) -> None:
        """记录发言"""
        self._write_event({
            "event": "speech",
            "game_id": self.game_id,
            "day": day,
            "data": {
                "speaker": speaker,
                "content": content,
                "speech_order": speech_order,
            },
            "timestamp": datetime.now().isoformat(),
        })

    def log_vote(self, day: int, voter: str, target: Optional[str], vote_order: int) -> None:
        """记录投票"""
        self._write_event({
            "event": "vote",
            "game_id": self.game_id,
            "day": day,
            "data": {
                "voter": voter,
                "target": target,
                "vote_order": vote_order,
            },
            "timestamp": datetime.now().isoformat(),
        })

    def log_exile(self, day: int, target: str, votes_received: int, total_votes: int) -> None:
        """记录投票出局"""
        self._write_event({
            "event": "exile",
            "game_id": self.game_id,
            "day": day,
            "data": {
                "target": target,
                "votes_received": votes_received,
                "total_votes": total_votes,
            },
            "timestamp": datetime.now().isoformat(),
        })

    def log_death(self, death: DeathRecord) -> None:
        """记录死亡"""
        self._write_event({
            "event": "death",
            "game_id": self.game_id,
            "data": death.model_dump(),
            "timestamp": datetime.now().isoformat(),
        })

    def log_announcement(self, day: int, phase: str, content: str, announcement_type: str = "system") -> None:
        """记录公告"""
        self._write_event({
            "event": "announcement",
            "game_id": self.game_id,
            "day": day,
            "phase": phase,
            "data": {
                "content": content,
                "type": announcement_type,
            },
            "timestamp": datetime.now().isoformat(),
        })

    def end_game(
        self,
        game_record: GameRecord,
        result: GameResult,
    ) -> Path:
        """
        结束游戏，写入完整记录

        Args:
            game_record: 完整游戏记录
            result: 游戏结果

        Returns:
            记录文件路径
        """
        # 更新结束时间
        game_record.game_info.end_time = datetime.now()
        game_record.game_result = result

        # 写入完整 JSON 记录
        record_path = self.logs_dir / f"{self.game_id}_record.json"
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(game_record.model_dump(), f, ensure_ascii=False, indent=2, default=str)

        # 写入结束事件
        self._write_event({
            "event": "game_end",
            "game_id": self.game_id,
            "data": {
                "winner": result.winner.value,
                "survival_players": result.survival_players,
                "total_days": result.total_days,
            },
            "timestamp": datetime.now().isoformat(),
        })

        return record_path

    def get_game_record(self) -> GameRecord:
        """获取当前的游戏记录（用于构建最终记录）"""
        return GameRecord(
            game_info=GameInfo(
                game_id=self.game_id or str(uuid.uuid4()),
                start_time=datetime.now(),
                mode=GameMode.SIMPLE,
                settings=GameSettings(
                    mode=GameMode.SIMPLE,
                    player_count=5,
                    werewolf_count=2,
                    god_count=2,
                    villager_count=1,
                ),
                player_ids=[],
            ),
            players=[],
            day_records=[],
        )


# 全局日志器实例
_game_logger: Optional[GameLogger] = None


def get_game_logger() -> GameLogger:
    """获取全局日志器实例"""
    global _game_logger
    if _game_logger is None:
        _game_logger = GameLogger()
    return _game_logger


def create_game_logger(logs_dir: Optional[Path] = None) -> GameLogger:
    """创建新的日志器实例"""
    global _game_logger
    _game_logger = GameLogger(logs_dir)
    return _game_logger
