"""
游戏管理器 - 管理所有游戏实例
"""

from typing import Dict, Optional, List
import threading

from src.game_engine.engine import GameEngine
from src.game_engine.logger import GameLogger


class GameInstance:
    """单个游戏实例"""

    def __init__(self, game_id: str, engine: GameEngine, logger: GameLogger):
        self.game_id = game_id
        self.engine = engine
        self.logger = logger
        self.created_at = None  # 可以后续扩展


class GameManager:
    """
    游戏管理器 - 线程安全的单例模式

    管理所有活跃游戏实例，提供游戏创建、查询、控制接口
    """

    _instance: Optional["GameManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._games: Dict[str, GameInstance] = {}
        self._games_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "GameManager":
        """获取单例实例"""
        if cls._instance is None:
            with threading.Lock():
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def create_game(
        self,
        player_ids: Optional[List[str]] = None,
        game_id: Optional[str] = None,
    ) -> GameInstance:
        """
        创建新游戏

        Args:
            player_ids: 自定义玩家ID列表，默认5人
            game_id: 自定义游戏ID，默认自动生成

        Returns:
            GameInstance 游戏实例
        """
        logger = GameLogger()
        engine = GameEngine(logger=logger)

        game_info = engine.start_game(player_ids=player_ids, game_id=game_id)
        actual_game_id = game_info.game_id

        instance = GameInstance(
            game_id=actual_game_id,
            engine=engine,
            logger=logger,
        )

        with self._games_lock:
            self._games[actual_game_id] = instance

        return instance

    def get_game(self, game_id: str) -> Optional[GameInstance]:
        """获取游戏实例"""
        with self._games_lock:
            return self._games.get(game_id)

    def list_games(self) -> List[Dict]:
        """列出所有游戏"""
        with self._games_lock:
            return [
                {
                    "game_id": game_id,
                    "phase": instance.engine.current_phase,
                    "day": instance.engine.current_day,
                    "alive_players": instance.engine.alive_players,
                    "is_game_over": instance.engine.is_game_over,
                }
                for game_id, instance in self._games.items()
            ]

    def delete_game(self, game_id: str) -> bool:
        """删除游戏"""
        with self._games_lock:
            if game_id in self._games:
                del self._games[game_id]
                return True
            return False


def get_game_manager() -> GameManager:
    """获取游戏管理器实例"""
    return GameManager.get_instance()
