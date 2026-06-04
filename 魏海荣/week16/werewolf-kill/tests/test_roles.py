"""
角色模块单元测试

测试所有角色的创建、方法和行为是否正常工作
"""

import pytest
import sys
import os

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.roles import Werewolf, Prophet, Witch, Hunter, Villager, Role
from src.schemas.roles_schema import (
    GamePhaseState,
    PublicInfo,
    PrivateInfo,
    ActionType,
    WerewolfKillResult,
    ProphetCheckResult,
    WitchSaveResult,
    NoNightActionResult,
    VoteResult,
)


class TestRoleCreation:
    """测试角色创建"""

    def test_werewolf_creation(self):
        """测试狼人角色创建"""
        werewolf = Werewolf(player_id="player_1")
        assert werewolf.role_type == "werewolf"
        assert werewolf.camp == "werewolf"
        assert werewolf.player_id == "player_1"
        assert werewolf.is_alive is True
        assert len(werewolf.abilities) == 1
        assert werewolf.abilities[0].name == "kill"

    def test_prophet_creation(self):
        """测试预言家角色创建"""
        prophet = Prophet(player_id="player_2")
        assert prophet.role_type == "prophet"
        assert prophet.camp == "village"
        assert prophet.player_id == "player_2"
        assert prophet.is_alive is True
        assert len(prophet.abilities) == 1
        assert prophet.abilities[0].name == "check"

    def test_witch_creation(self):
        """测试女巫角色创建"""
        witch = Witch(player_id="player_3")
        assert witch.role_type == "witch"
        assert witch.camp == "village"
        assert witch.player_id == "player_3"
        assert witch.is_alive is True
        assert len(witch.abilities) == 2
        assert witch.can_save is True
        assert witch.can_poison is True

    def test_hunter_creation(self):
        """测试猎人角色创建"""
        hunter = Hunter(player_id="player_4")
        assert hunter.role_type == "hunter"
        assert hunter.camp == "village"
        assert hunter.player_id == "player_4"
        assert hunter.is_alive is True
        assert hunter.can_shoot is True

    def test_villager_creation(self):
        """测试平民角色创建"""
        villager = Villager(player_id="player_5")
        assert villager.role_type == "villager"
        assert villager.camp == "village"
        assert villager.player_id == "player_5"
        assert villager.is_alive is True
        assert len(villager.abilities) == 0


class TestWerewolfMethods:
    """测试狼人角色方法"""

    def setup_method(self):
        """每个测试方法前的初始化"""
        self.werewolf = Werewolf(player_id="wolf_1")
        self.werewolf2 = Werewolf(player_id="wolf_2")

    def test_add_fellow_werewolf(self):
        """测试添加狼人同伴"""
        self.werewolf.add_fellow_werewolf("wolf_2")
        assert "wolf_2" in self.werewolf.fellow_werewolves
        assert "wolf_1" not in self.werewolf.fellow_werewolves

    def test_get_public_info(self):
        """测试获取公开信息"""
        public_info = self.werewolf.get_public_info()
        assert public_info.visible_role == "好人"
        assert public_info.is_suspicious is False
        assert hasattr(public_info, 'visible_role')
        assert hasattr(public_info, 'claims')

    def test_get_private_info_as_werewolf(self):
        """测试狼人之间获取私有信息"""
        self.werewolf.add_fellow_werewolf("wolf_2")
        private_info = self.werewolf.get_private_info(viewer=self.werewolf2)
        assert private_info.actual_role == "werewolf"
        assert "wolf_2" in private_info.fellow_werewolves

    def test_get_private_info_as_non_werewolf(self):
        """测试非狼人获取私有信息"""
        prophet = Prophet(player_id="prophet_1")
        private_info = self.werewolf.get_private_info(viewer=prophet)
        assert private_info.actual_role is None

    def test_night_action_alive(self):
        """测试狼人夜间行动（存活状态）"""
        game_state = GamePhaseState(
            phase="night",
            day_number=1,
            alive_players=["wolf_1", "wolf_2", "villager_1", "prophet_1"],
            dead_players=[],
            previous_kills=[],
            vote_records={},
            speech_records={},
            checked_history={}
        )
        result = self.werewolf.night_action(game_state)
        assert hasattr(result, 'action')
        assert hasattr(result, 'target')
        assert result.action == ActionType.KILL
        assert result.target in ["wolf_2", "villager_1", "prophet_1"]

    def test_night_action_dead(self):
        """测试狼人夜间行动（死亡状态）"""
        self.werewolf.die()
        game_state = GamePhaseState(
            phase="night",
            day_number=1,
            alive_players=["wolf_2", "villager_1"],
            dead_players=["wolf_1"],
            previous_kills=[],
            vote_records={},
            speech_records={},
            checked_history={}
        )
        result = self.werewolf.night_action(game_state)
        assert result.action == ActionType.PASS

    def test_day_action(self):
        """测试狼人白天行动"""
        game_state = GamePhaseState(
            phase="day",
            day_number=1,
            alive_players=["wolf_1", "wolf_2", "villager_1"],
            dead_players=[],
            previous_kills=[],
            vote_records={},
            speech_records={},
            checked_history={}
        )
        result = self.werewolf.day_action(game_state)
        assert hasattr(result, 'action')
        assert result.action == ActionType.VOTE

    def test_get_fake_role(self):
        """测试获取伪装身份"""
        fake_role = self.werewolf.get_fake_role()
        assert fake_role in ["平民", "预言家", "女巫", "猎人"]


class TestProphetMethods:
    """测试预言家角色方法"""

    def setup_method(self):
        """每个测试方法前的初始化"""
        self.prophet = Prophet(player_id="prophet_1")

    def test_get_public_info(self):
        """测试获取公开信息"""
        public_info = self.prophet.get_public_info()
        assert public_info.visible_role == "好人"
        assert hasattr(public_info, 'visible_role')

    def test_get_private_info_as_prophet(self):
        """测试预言家获取自己的私有信息"""
        private_info = self.prophet.get_private_info(viewer=self.prophet)
        assert hasattr(private_info, 'checked_players')
        assert private_info.checked_players == {}

    def test_add_check_result(self):
        """测试记录查验结果"""
        self.prophet.add_check_result("player_x", True, "werewolf")
        assert self.prophet.get_check_history() == {"player_x": True}

    def test_night_action(self):
        """测试预言家夜间查验"""
        game_state = GamePhaseState(
            phase="night",
            day_number=1,
            alive_players=["prophet_1", "wolf_1", "villager_1"],
            dead_players=[],
            previous_kills=[],
            vote_records={},
            speech_records={},
            checked_history={}
        )
        result = self.prophet.night_action(game_state)
        assert hasattr(result, 'action')
        assert hasattr(result, 'target')
        assert result.action == ActionType.CHECK
        assert result.target in ["wolf_1", "villager_1"]

    def test_night_action_no_candidates(self):
        """测试预言家夜间查验（无可查验目标）"""
        game_state = GamePhaseState(
            phase="night",
            day_number=1,
            alive_players=["prophet_1"],
            dead_players=["wolf_1", "villager_1"],
            previous_kills=[],
            vote_records={},
            speech_records={},
            checked_history={"wolf_1": True, "villager_1": False}
        )
        result = self.prophet.night_action(game_state)
        assert result.action == ActionType.PASS

    def test_day_action(self):
        """测试预言家白天行动"""
        game_state = GamePhaseState(
            phase="day",
            day_number=1,
            alive_players=["prophet_1", "wolf_1", "villager_1"],
            dead_players=[],
            previous_kills=[],
            vote_records={},
            speech_records={},
            checked_history={}
        )
        result = self.prophet.day_action(game_state)
        assert hasattr(result, 'action')
        assert result.action == ActionType.VOTE


class TestWitchMethods:
    """测试女巫角色方法"""

    def setup_method(self):
        """每个测试方法前的初始化"""
        self.witch = Witch(player_id="witch_1")

    def test_get_public_info(self):
        """测试获取公开信息"""
        public_info = self.witch.get_public_info()
        assert public_info.visible_role == "好人"
        assert hasattr(public_info, 'visible_role')

    def test_get_private_info(self):
        """测试获取私有信息"""
        private_info = self.witch.get_private_info(viewer=self.witch)
        assert hasattr(private_info, 'save_used')
        assert private_info.save_used is False
        assert private_info.poison_used is False

    def test_set_killed_by_werewolf(self):
        """测试设置狼人击杀目标"""
        self.witch.set_killed_by_werewolf("prophet_1")
        private_info = self.witch.get_private_info(viewer=self.witch)
        assert private_info.extra_data.get("tonight_killed_by_werewolf") == "prophet_1"

    def test_night_action_save(self):
        """测试女巫夜间救人"""
        game_state = GamePhaseState(
            phase="night",
            day_number=2,
            alive_players=["witch_1", "prophet_1", "wolf_1"],
            dead_players=["villager_1"],
            previous_kills=["prophet_1"],  # 狼人击杀了预言家
            vote_records={},
            speech_records={},
            checked_history={}
        )
        result = self.witch.night_action(game_state)
        assert hasattr(result, 'action')
        # 女巫可以选择救人或什么都不做
        assert result.action in [ActionType.SAVE, ActionType.PASS]

    def test_night_action_dead(self):
        """测试女巫夜间行动（死亡状态）"""
        self.witch.die()
        game_state = GamePhaseState(
            phase="night",
            day_number=1,
            alive_players=["wolf_1", "villager_1"],
            dead_players=["witch_1"],
            previous_kills=[],
            vote_records={},
            speech_records={},
            checked_history={}
        )
        result = self.witch.night_action(game_state)
        assert result.action == ActionType.PASS

    def test_use_save(self):
        """测试使用救人药水"""
        result = self.witch.use_save("prophet_1")
        assert result is True
        assert self.witch.can_save is False

    def test_use_poison(self):
        """测试使用毒药"""
        result = self.witch.use_poison("wolf_1")
        assert result is True
        assert self.witch.can_poison is False

    def test_use_save_already_used(self):
        """测试重复使用救人药水"""
        self.witch.use_save("prophet_1")
        result = self.witch.use_save("wolf_1")
        assert result is False


class TestHunterMethods:
    """测试猎人角色方法"""

    def setup_method(self):
        """每个测试方法前的初始化"""
        self.hunter = Hunter(player_id="hunter_1")

    def test_get_public_info(self):
        """测试获取公开信息"""
        public_info = self.hunter.get_public_info()
        assert public_info.visible_role == "好人"
        assert hasattr(public_info, 'visible_role')

    def test_get_private_info(self):
        """测试获取私有信息"""
        private_info = self.hunter.get_private_info(viewer=self.hunter)
        assert hasattr(private_info, 'can_shoot')
        assert private_info.can_shoot is True

    def test_night_action(self):
        """测试猎人夜间行动（无行动）"""
        game_state = GamePhaseState(
            phase="night",
            day_number=1,
            alive_players=["hunter_1", "wolf_1"],
            dead_players=[],
            previous_kills=[],
            vote_records={},
            speech_records={},
            checked_history={}
        )
        result = self.hunter.night_action(game_state)
        assert result.action == ActionType.PASS
        assert "猎人" in result.reason

    def test_day_action_alive(self):
        """测试猎人白天行动（存活状态）"""
        game_state = GamePhaseState(
            phase="day",
            day_number=1,
            alive_players=["hunter_1", "wolf_1", "villager_1"],
            dead_players=[],
            previous_kills=[],
            vote_records={},
            speech_records={},
            checked_history={}
        )
        result = self.hunter.day_action(game_state)
        assert hasattr(result, 'action')
        assert result.action == ActionType.VOTE

    def test_day_action_dead_with_target(self):
        """测试猎人死亡后追刀"""
        self.hunter.die(reason="vote")
        self.hunter.set_shoot_target("wolf_1")
        game_state = GamePhaseState(
            phase="day",
            day_number=1,
            alive_players=["wolf_1", "villager_1"],
            dead_players=["hunter_1"],
            previous_kills=[],
            vote_records={},
            speech_records={},
            checked_history={}
        )
        result = self.hunter.day_action(game_state)
        assert hasattr(result, 'action')

    def test_die_by_werewolf_can_shoot(self):
        """测试狼人击杀后可以开枪"""
        self.hunter.die(reason="werewolf_kill")
        assert self.hunter.can_shoot is True
        assert self.hunter.is_alive is False

    def test_die_by_witch_cannot_shoot(self):
        """测试女巫毒杀后不能开枪"""
        self.hunter.die(reason="witch_poison")
        assert self.hunter.can_shoot is False

    def test_get_available_targets(self):
        """测试获取可击杀目标列表"""
        targets = self.hunter.get_available_targets(["hunter_1", "wolf_1", "villager_1"])
        assert "wolf_1" in targets
        assert "villager_1" in targets
        assert "hunter_1" not in targets


class TestVillagerMethods:
    """测试平民角色方法"""

    def setup_method(self):
        """每个测试方法前的初始化"""
        self.villager = Villager(player_id="villager_1")

    def test_get_public_info(self):
        """测试获取公开信息"""
        public_info = self.villager.get_public_info()
        assert public_info.visible_role == "平民"
        assert public_info.claims == "平民"
        assert hasattr(public_info, 'visible_role')

    def test_get_private_info(self):
        """测试获取私有信息"""
        private_info = self.villager.get_private_info()
        assert hasattr(private_info, 'actual_role')

    def test_night_action(self):
        """测试平民夜间行动（无行动）"""
        game_state = GamePhaseState(
            phase="night",
            day_number=1,
            alive_players=["villager_1", "wolf_1"],
            dead_players=[],
            previous_kills=[],
            vote_records={},
            speech_records={},
            checked_history={}
        )
        result = self.villager.night_action(game_state)
        assert result.action == ActionType.PASS
        assert "平民" in result.reason

    def test_day_action_alive(self):
        """测试平民白天行动"""
        game_state = GamePhaseState(
            phase="day",
            day_number=1,
            alive_players=["villager_1", "wolf_1", "prophet_1"],
            dead_players=[],
            previous_kills=[],
            vote_records={},
            speech_records={},
            checked_history={}
        )
        result = self.villager.day_action(game_state)
        assert hasattr(result, 'action')
        assert result.action == ActionType.VOTE

    def test_day_action_dead(self):
        """测试平民死亡后白天行动"""
        self.villager.die()
        game_state = GamePhaseState(
            phase="day",
            day_number=1,
            alive_players=["wolf_1", "prophet_1"],
            dead_players=["villager_1"],
            previous_kills=[],
            vote_records={},
            speech_records={},
            checked_history={}
        )
        result = self.villager.day_action(game_state)
        assert hasattr(result, 'action')
        assert result.target is None


class TestRoleCommonMethods:
    """测试角色通用方法"""

    def setup_method(self):
        """每个测试方法前的初始化"""
        self.werewolf = Werewolf(player_id="wolf_1")

    def test_die(self):
        """测试角色死亡"""
        assert self.werewolf.is_alive is True
        self.werewolf.die(reason="vote")
        assert self.werewolf.is_alive is False

    def test_revoke(self):
        """测试角色复活"""
        self.werewolf.die()
        assert self.werewolf.is_alive is False
        self.werewolf.revive()
        assert self.werewolf.is_alive is True

    def test_use_ability(self):
        """测试使用能力"""
        result = self.werewolf.use_ability("kill")
        assert result is True

    def test_use_ability_invalid(self):
        """测试使用无效能力"""
        result = self.werewolf.use_ability("invalid_ability")
        assert result is False

    def test_to_dict(self):
        """测试序列化为字典"""
        data = self.werewolf.to_dict()
        assert data["role_type"] == "werewolf"
        assert data["camp"] == "werewolf"
        assert data["player_id"] == "wolf_1"
        assert data["is_alive"] is True


class TestWinConditions:
    """测试角色胜利条件"""

    def test_werewolf_win_condition(self):
        """测试狼人胜利条件"""
        werewolf = Werewolf(player_id="wolf_1")
        assert "狼人" in werewolf.win_condition or "好人" in werewolf.win_condition

    def test_prophet_win_condition(self):
        """测试预言家胜利条件"""
        prophet = Prophet(player_id="prophet_1")
        assert "狼人" in prophet.win_condition

    def test_witch_win_condition(self):
        """测试女巫胜利条件"""
        witch = Witch(player_id="witch_1")
        assert "狼人" in witch.win_condition

    def test_hunter_win_condition(self):
        """测试猎人胜利条件"""
        hunter = Hunter(player_id="hunter_1")
        assert "狼人" in hunter.win_condition

    def test_villager_win_condition(self):
        """测试平民胜利条件"""
        villager = Villager(player_id="villager_1")
        assert "狼人" in villager.win_condition


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
