"""
经验模块

管理角色经验的存储和读取。
对局结束后由 Summary Agent 生成的经验会保存到对应角色的 JSON 文件中。
下次对局开始时，从 JSON 文件读取最近的经验注入到提示词中。
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from src.schemas.roles_schema import RoleType


class ExperienceEntry(BaseModel):
    """单条经验"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    game_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    situation: str
    available_actions: List[str]
    chosen_action: str
    outcome: str  # success / failed / neutral
    result_reason: str
    key_learning: str


class ExperienceStore(BaseModel):
    """经验仓库"""
    role_type: str
    experiences: List[ExperienceEntry] = Field(default_factory=list)


class ExperienceManager:
    """
    经验管理器

    负责读写角色经验 JSON 文件。
    文件路径: src/memory/experience/{role_type}.json
    """

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = Path(__file__).parent
        self.base_dir = base_dir
        self.experience_dir = self.base_dir / "experience"
        self.experience_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, role_type: str) -> Path:
        """获取指定角色经验文件的路径"""
        return self.experience_dir / f"{role_type}.json"

    def _load_store(self, role_type: str) -> ExperienceStore:
        """加载角色的经验仓库"""
        file_path = self._get_file_path(role_type)
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 反序列化 datetime
                for exp in data.get("experiences", []):
                    if isinstance(exp.get("timestamp"), str):
                        exp["timestamp"] = datetime.fromisoformat(exp["timestamp"])
                return ExperienceStore(**data)
        return ExperienceStore(role_type=role_type)

    def _save_store(self, store: ExperienceStore) -> None:
        """保存经验仓库到文件"""
        file_path = self._get_file_path(store.role_type)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(store.model_dump(), f, ensure_ascii=False, indent=2, default=str)

    def add_experience(
        self,
        role_type: str,
        game_id: str,
        situation: str,
        available_actions: List[str],
        chosen_action: str,
        outcome: str,
        result_reason: str,
        key_learning: str,
    ) -> ExperienceEntry:
        """
        添加一条经验

        Args:
            role_type: 角色类型
            game_id: 对局ID
            situation: 情境描述
            available_actions: 可选行动列表
            chosen_action: 最终选择的行动
            outcome: 结果 (success/failed/neutral)
            result_reason: 成败原因
            key_learning: 关键教训

        Returns:
            创建的经验条目
        """
        entry = ExperienceEntry(
            game_id=game_id,
            situation=situation,
            available_actions=available_actions,
            chosen_action=chosen_action,
            outcome=outcome,
            result_reason=result_reason,
            key_learning=key_learning,
        )

        store = self._load_store(role_type)
        store.experiences.append(entry)
        self._save_store(store)

        return entry

    def get_recent_experiences(
        self, role_type: str, limit: int = 3
    ) -> List[ExperienceEntry]:
        """
        获取最近的经验

        Args:
            role_type: 角色类型
            limit: 返回条数，默认3条

        Returns:
            最近的经验列表（按时间倒序）
        """
        store = self._load_store(role_type)
        # 按时间倒序，返回最近 limit 条
        sorted_experiences = sorted(
            store.experiences, key=lambda x: x.timestamp, reverse=True
        )
        return sorted_experiences[:limit]

    def format_for_prompt(self, role_type: str, limit: int = 3) -> str:
        """
        格式化成提示词片段

        Args:
            role_type: 角色类型
            limit: 返回条数，默认3条

        Returns:
            格式化的提示词字符串
        """
        experiences = self.get_recent_experiences(role_type, limit)

        if not experiences:
            return ""

        lines = ["\n## 历史经验参考"]
        for i, exp in enumerate(experiences, 1):
            lines.append(f"{i}. [{exp.role_type}] {exp.key_learning}")

        return "\n".join(lines)

    def get_experience_count(self, role_type: str) -> int:
        """获取某角色当前的经验条数"""
        store = self._load_store(role_type)
        return len(store.experiences)

    def clear_experiences(self, role_type: str) -> None:
        """清空某角色的所有经验（用于测试）"""
        store = ExperienceStore(role_type=role_type)
        self._save_store(store)


# 全局单例
_experience_manager: Optional[ExperienceManager] = None


def get_experience_manager() -> ExperienceManager:
    """获取全局经验管理器实例"""
    global _experience_manager
    if _experience_manager is None:
        _experience_manager = ExperienceManager()
    return _experience_manager
