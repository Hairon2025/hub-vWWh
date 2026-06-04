"""
角色模块

导出所有角色类和角色类型枚举
"""

from .base import Role
from .werewolf import Werewolf
from .prophet import Prophet
from .witch import Witch
from .hunter import Hunter
from .villager import Villager

__all__ = [
    "Role",
    "Werewolf",
    "Prophet",
    "Witch",
    "Hunter",
    "Villager",
]
