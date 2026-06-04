"""
Game Engine 模块

狼人杀游戏引擎，负责管理游戏流程、状态转换、胜负判定。

主要类：
- GameEngine: 游戏引擎核心类
- GameLogger: 游戏日志记录器
- GameManager: 游戏管理器（管理多个游戏实例）
"""

from .engine import GameEngine
from .logger import GameLogger, get_game_logger, create_game_logger
from .manager import GameManager, GameInstance, get_game_manager

__all__ = [
    "GameEngine",
    "GameLogger",
    "get_game_logger",
    "create_game_logger",
    "GameManager",
    "GameInstance",
    "get_game_manager",
]
