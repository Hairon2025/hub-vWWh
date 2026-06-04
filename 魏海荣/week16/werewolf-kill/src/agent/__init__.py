"""
Agent 模块 - 多代理框架核心

提供 Agent 基础类和 Agent 工厂。
"""

from .base import BaseAgent
from .player_agent import PlayerAgent
from .summary_agent import SummaryAgent, summarize_game

__all__ = ["BaseAgent", "PlayerAgent", "SummaryAgent", "summarize_game"]
