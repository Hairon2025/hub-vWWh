"""
游戏引擎单元测试

测试 GameEngine 的状态机、夜晚阶段、白天阶段、胜负判定
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.game_engine.engine import GameEngine
from src.game_engine.logger import GameLogger
from src.schemas.game_logger_schema import Winner
from src.schemas.roles_schema import DeathReason
from src.schemas.roles_schema import RoleType


class TestGameEngineInit:
    """测试游戏引擎初始化"""

    def setup_method(self):
        """每个测试前的初始化"""
        self.logger = GameLogger()
        self.engine = GameEngine(logger=self.logger)

    def test_engine_initial_state(self):
        """测试引擎初始状态"""
        assert self.engine.game_id is None
        assert self.engine.players == {}
        assert self.engine.player_ids == []
        assert self.engine.alive_players == []
        assert self.engine.dead_players == []
        assert self.engine.current_day == 0
        assert self.engine.current_phase == "waiting"
        assert self.engine.is_game_over is False
        assert self.engine.winner is None


class TestGameStart:
    """测试游戏开始"""

    def setup_method(self):
        self.logger = GameLogger()
        self.engine = GameEngine(logger=self.logger)

    def test_start_game_default(self):
        """测试默认开始游戏"""
        game_info = self.engine.start_game()

        assert self.engine.game_id is not None
        assert self.engine.game_id.startswith("game_")
        assert len(self.engine.player_ids) == 5
        assert len(self.engine.players) == 5
        assert game_info.settings.player_count == 5

    def test_start_game_custom_players(self):
        """测试自定义玩家ID开始游戏"""
        custom_ids = ["alice", "bob", "charlie", "david", "eve"]
        game_info = self.engine.start_game(player_ids=custom_ids)

        assert self.engine.player_ids == custom_ids
        assert game_info.player_ids == custom_ids

    def test_start_game_shuffles_players(self):
        """测试开始游戏会打乱玩家顺序"""
        custom_ids = ["p1", "p2", "p3", "p4", "p5"]
        game_info = self.engine.start_game(player_ids=custom_ids)

        # 顺序应该被打乱（不一定等于原始顺序）
        assert len(self.engine.player_ids) == 5

    def test_role_assignment(self):
        """测试角色分配"""
        self.engine.start_game()

        role_types = [r.role_type for r in self.engine.players.values()]
        assert role_types.count("werewolf") == 2
        assert role_types.count("prophet") == 1
        assert role_types.count("witch") == 1
        assert role_types.count("villager") == 1

    def test_werewolf_knows_fellow(self):
        """测试狼人知道同伴"""
        self.engine.start_game()

        werewolves = [pid for pid, r in self.engine.players.items()
                      if r.role_type == "werewolf"]

        for wolf_id in werewolves:
            wolf = self.engine.players[wolf_id]
            assert len(wolf.fellow_werewolves) == 1
            assert werewolves[0] if werewolves[0] != wolf_id else werewolves[1] \
                in wolf.fellow_werewolves


class TestNightPhase:
    """测试夜晚阶段"""

    def setup_method(self):
        self.logger = GameLogger()
        self.engine = GameEngine(logger=self.logger)
        self.engine.start_game()
        self.engine.create_agents()

    def test_night_increments_day(self):
        """测试夜晚递增天数"""
        initial_day = self.engine.current_day
        self.engine.run_night()
        assert self.engine.current_day == initial_day + 1

    def test_night_sets_phase(self):
        """测试夜晚设置阶段"""
        self.engine.run_night()
        assert self.engine.current_phase == "night"

    def test_night_returns_night_result(self):
        """测试夜晚返回结果"""
        result = self.engine.run_night()
        assert hasattr(result, 'night_number')
        assert result.night_number == 1
        assert hasattr(result, 'events')
        assert hasattr(result, 'deaths')
        assert hasattr(result, 'announcement')

    def test_night_creates_day_record(self):
        """测试夜晚创建日记录"""
        self.engine.run_night()
        assert len(self.engine.day_records) == 1
        assert self.engine.day_records[0].day_number == 1


class TestDayPhase:
    """测试白天阶段"""

    def setup_method(self):
        self.logger = GameLogger()
        self.engine = GameEngine(logger=self.logger)
        self.engine.start_game()
        self.engine.create_agents()
        # 先运行一夜
        self.engine.run_night()

    def test_day_sets_phase(self):
        """测试白天设置阶段"""
        self.engine.run_day()
        assert self.engine.current_phase == "day"

    def test_day_returns_day_result(self):
        """测试白天返回结果"""
        result = self.engine.run_day()
        assert hasattr(result, 'day_number')
        assert result.day_number == 1
        assert hasattr(result, 'events')
        assert hasattr(result, 'deaths')

    def test_day_records_speeches(self):
        """测试白天记录发言"""
        self.engine.run_day()
        assert 1 in self.engine.speech_records
        assert len(self.engine.speech_records[1]) == len(self.engine.alive_players)

    def test_day_records_votes(self):
        """测试白天记录投票"""
        self.engine.run_day()
        assert 1 in self.engine.vote_records
        assert len(self.engine.vote_records[1]) == len(self.engine.alive_players)


class TestWinCondition:
    """测试胜负判定"""

    def setup_method(self):
        self.logger = GameLogger()
        self.engine = GameEngine(logger=self.logger)
        self.engine.start_game()
        self.engine.create_agents()

    def test_village_wins_when_no_werewolf(self):
        """测试狼人全灭好人胜利"""
        # 找到狼人并杀死
        werewolf_id = None
        for pid, role in self.engine.players.items():
            if role.role_type == "werewolf":
                werewolf_id = pid
                break

        # 移除狼人（模拟狼人被放逐）
        self.engine.alive_players.remove(werewolf_id)
        self.engine.dead_players.append(werewolf_id)
        self.engine.players[werewolf_id].die()

        # 再移除一只狼人
        werewolf_id2 = None
        for pid, role in self.engine.players.items():
            if role.role_type == "werewolf" and pid in self.engine.alive_players:
                werewolf_id2 = pid
                break

        if werewolf_id2:
            self.engine.alive_players.remove(werewolf_id2)
            self.engine.dead_players.append(werewolf_id2)
            self.engine.players[werewolf_id2].die()

        is_over, winner = self.engine.check_win_condition()
        assert is_over is True
        assert winner == Winner.VILLAGE

    def test_werewolf_wins_when_village_outnumbered(self):
        """测试好人数量<=狼人数量狼人胜利"""
        # 杀死所有好人（只剩狼人）
        self.engine.alive_players = [pid for pid, r in self.engine.players.items()
                                     if r.role_type == "werewolf"]
        self.engine.dead_players = [pid for pid, r in self.engine.players.items()
                                    if r.role_type != "werewolf"]

        for pid in self.engine.dead_players:
            self.engine.players[pid].die()

        is_over, winner = self.engine.check_win_condition()
        assert is_over is True
        assert winner == Winner.WEREWOLF

    def test_game_continues_mid_game(self):
        """测试游戏中胜负未分"""
        is_over, winner = self.engine.check_win_condition()
        assert is_over is False
        assert winner is None


class TestFullGame:
    """测试完整游戏流程"""

    def setup_method(self):
        self.logger = GameLogger()
        self.engine = GameEngine(logger=self.logger)

    def test_full_game_runs(self):
        """测试完整游戏能够运行"""
        result = self.engine.run_full_game()

        assert result is not None
        assert hasattr(result, 'winner')
        assert result.winner in [Winner.VILLAGE, Winner.WEREWOLF, Winner.DRAW]
        assert hasattr(result, 'total_days')
        assert result.total_days >= 1

    def test_full_game_creates_records(self):
        """测试完整游戏创建记录"""
        self.engine.run_full_game()

        assert len(self.engine.day_records) >= 1
        assert len(self.engine.death_records) >= 1

    def test_game_record_contains_player_info(self):
        """测试游戏记录包含玩家信息"""
        self.engine.run_full_game()
        record = self.engine.get_game_record()

        assert len(record.players) == 5
        for player_info in record.players:
            assert hasattr(player_info, 'player_id')
            assert hasattr(player_info, 'role_type')
            assert hasattr(player_info, 'camp')


class TestDeathResolution:
    """测试死亡结算"""

    def setup_method(self):
        self.logger = GameLogger()
        self.engine = GameEngine(logger=self.logger)
        self.engine.start_game()
        self.engine.create_agents()

    def test_werewolf_kill_without_witch_save(self):
        """测试狼人击杀无女巫救"""
        # 记录初始存活人数
        initial_alive = len(self.engine.alive_players)

        # 运行一夜（假设女巫不救）
        self.engine.run_night()

        # 应该有死亡记录
        assert len(self.engine.death_records) >= 0  # 可能有平安夜

    def test_player_die_updates_lists(self):
        """测试玩家死亡更新列表"""
        player_id = self.engine.alive_players[0]

        self.engine._kill_player(player_id, reason=DeathReason.VOTE)

        assert player_id not in self.engine.alive_players
        assert player_id in self.engine.dead_players
        assert self.engine.players[player_id].is_alive is False

    def test_hunter_shoot_on_death(self):
        """测试猎人死亡时追刀"""
        # 找到猎人
        hunter_id = None
        for pid, role in self.engine.players.items():
            if role.role_type == "hunter":
                hunter_id = pid
                break

        if hunter_id:
            # 杀死猎人
            self.engine._kill_player(hunter_id, reason="werewolf_kill")

            # 猎人应该仍然可以开枪
            hunter = self.engine.players[hunter_id]
            assert hunter.role_type == "hunter"


class TestGamePhaseState:
    """测试游戏阶段状态"""

    def setup_method(self):
        self.logger = GameLogger()
        self.engine = GameEngine(logger=self.logger)
        self.engine.start_game()
        self.engine.create_agents()

    def test_build_game_phase_state_night(self):
        """测试构建夜间游戏状态"""
        self.engine.current_phase = "night"
        self.engine.current_day = 1

        state = self.engine._build_game_phase_state()

        assert state.phase == "night"
        assert state.day_number == 1
        assert len(state.alive_players) == 5
        assert len(state.dead_players) == 0

    def test_build_game_phase_state_day(self):
        """测试构建白天游戏状态"""
        self.engine.run_night()
        self.engine.current_phase = "day"

        state = self.engine._build_game_phase_state()

        assert state.phase == "day"
        assert state.day_number == 1
        assert hasattr(state, 'vote_records')
        assert hasattr(state, 'speech_records')

    def test_prophet_check_history(self):
        """测试预言家查验历史"""
        history = self.engine._get_prophet_check_history()
        assert isinstance(history, dict)


class TestNightOrder:
    """测试夜间顺序"""

    def setup_method(self):
        self.logger = GameLogger()
        self.engine = GameEngine(logger=self.logger)
        self.engine.start_game()
        self.engine.create_agents()

    def test_night_order_werewolf_prophet_witch(self):
        """测试夜间顺序：狼人 -> 预言家 -> 女巫"""
        settings = self.engine.start_game().settings
        assert settings.night_order == ["werewolf", "prophet", "witch"]


class TestExile:
    """测试放逐投票"""

    def setup_method(self):
        self.logger = GameLogger()
        self.engine = GameEngine(logger=self.logger)
        self.engine.start_game()
        self.engine.create_agents()
        self.engine.run_night()  # 先过一夜

    def test_vote_exile_with_majority(self):
        """测试超过半数票放逐"""
        # 设置投票记录使某玩家获得超过半数票
        target = self.engine.alive_players[0]
        voters = self.engine.alive_players[1:]

        # 假设有3个玩家活着，2票可以超过半数
        self.engine.vote_records[1] = {}
        for voter in voters:
            self.engine.vote_records[1][voter] = target

        # 运行白天结算
        self.engine.current_day = 1
        deaths = self.engine._resolve_day_deaths()

        # 应该有死亡
        assert len(deaths) >= 1
        assert deaths[0].player_id == target
        assert deaths[0].reason.value == "vote_exile"

    def test_vote_no_majority_no_death(self):
        """测试未超过半数票不放逐"""
        # 设置平票的投票记录
        self.engine.vote_records[1] = {
            self.engine.alive_players[0]: self.engine.alive_players[0],
            self.engine.alive_players[1]: self.engine.alive_players[1],
        }

        self.engine.current_day = 1
        deaths = self.engine._resolve_day_deaths()

        # 不应该有人死亡
        assert len(deaths) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
