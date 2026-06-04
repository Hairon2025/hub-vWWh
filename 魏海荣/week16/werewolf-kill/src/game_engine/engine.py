"""
游戏引擎核心模块

负责管理游戏流程、状态转换、胜负判定。
支持5人对局：1预言家、2狼人、1女巫、1平民。

核心方法：
- start_game(): 初始化游戏
- run_night(): 执行夜间阶段
- run_day(): 执行白天阶段
- check_win_condition(): 检查胜负条件
- get_game_record(): 获取游戏记录
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from src.schemas.game_logger_schema import (
    GameSettings,
    GameMode,
    GameInfo,
    PlayerInfo,
    DeathRecord,
    DeathReason as SchemaDeathReason,
    NightResult,
    NightEventType,
    WerewolfKillEvent,
    ProphetCheckEvent,
    WitchSaveEvent,
    WitchPoisonEvent,
    NoDeathEvent,
    DayResult,
    DayEventType,
    SpeechEvent,
    VoteEvent,
    ExileEvent,
    AnnouncementEvent,
    DayRecord,
    Winner,
    PlayerResult,
    GameResult,
    GameRecord,
)
from src.schemas.roles_schema import (
    GamePhaseState,
    RoleType,
    CampType,
    ActionType,
    NightActionResult,
    WerewolfKillResult,
    ProphetCheckResult,
    WitchSaveResult,
    WitchPoisonResult,
    NoNightActionResult,
    VoteResult,
    SpeakResult,
)
from src.roles.base import Role
from src.roles.werewolf import Werewolf
from src.roles.prophet import Prophet
from src.roles.witch import Witch
from src.roles.hunter import Hunter
from src.roles.villager import Villager
from src.agent.player_agent import PlayerAgent

from .logger import GameLogger, get_game_logger, create_game_logger


class GameEngine:
    """
    狼人杀游戏引擎

    管理游戏流程、状态转换、角色行动。
    支持5人对局：1预言家、2狼人、1女巫、1平民。
    """

    def __init__(self, logger: Optional[GameLogger] = None):
        self.logger = logger or get_game_logger()

        # 游戏状态
        self.game_id: Optional[str] = None
        self.players: Dict[str, Role] = {}  # player_id -> Role
        self.player_agents: Dict[str, PlayerAgent] = {}  # player_id -> PlayerAgent
        self.player_ids: List[str] = []
        self.alive_players: List[str] = []
        self.dead_players: List[str] = []

        # 当前阶段状态
        self.current_day: int = 0
        self.current_phase: str = "waiting"  # waiting, night, day
        self.is_game_over: bool = False
        self.winner: Optional[Winner] = None

        # 夜间行动记录
        self.night_kill_target: Optional[str] = None
        self.werewolf_votes: Dict[str, str] = {}  # werewolf_id -> target_id
        self.prophet_check_target: Optional[str] = None
        self.witch_save_target: Optional[str] = None
        self.witch_poison_target: Optional[str] = None

        # 每日记录
        self.day_records: List[DayRecord] = []
        self.speech_records: Dict[int, Dict[str, str]] = {}  # day -> {player_id -> speech}
        self.vote_records: Dict[int, Dict[str, str]] = {}  # day -> {voter -> voted}

        # 死亡记录
        self.death_records: List[DeathRecord] = []

    def start_game(
        self,
        player_ids: Optional[List[str]] = None,
        game_id: Optional[str] = None,
    ) -> GameInfo:
        """
        开始新游戏

        Args:
            player_ids: 玩家ID列表，默认生成5个
            game_id: 游戏ID，默认自动生成

        Returns:
            GameInfo 游戏信息
        """
        self.game_id = game_id or f"game_{uuid.uuid4().hex[:8]}"
        self.player_ids = player_ids or [f"player_{i}" for i in range(1, 6)]

        # 打乱顺序
        import random
        random.shuffle(self.player_ids)

        # 创建角色
        self._setup_roles()

        # 初始化状态
        self.alive_players = self.player_ids.copy()
        self.dead_players = []
        self.current_day = 0
        self.current_phase = "waiting"
        self.is_game_over = False
        self.winner = None
        self.day_records = []
        self.speech_records = {}
        self.vote_records = {}
        self.death_records = []

        # 创建游戏设置
        settings = GameSettings(
            mode=GameMode.SIMPLE,
            player_count=5,
            werewolf_count=2,
            god_count=2,  # prophet + witch
            villager_count=1,
            night_order=["werewolf", "prophet", "witch"],
        )

        # 初始化日志
        game_info = GameInfo(
            game_id=self.game_id,
            start_time=datetime.now(),
            mode=GameMode.SIMPLE,
            settings=settings,
            player_ids=self.player_ids,
        )

        self.logger.start_game(self.game_id, settings, self.player_ids)

        return game_info

    def _setup_roles(self) -> None:
        """设置角色分配"""
        self.players = {}

        # 分配角色：2狼人、1预言家、1女巫、1平民
        role_assignments = [
            Werewolf,
            Werewolf,
            Prophet,
            Witch,
            Villager,
        ]

        for i, player_id in enumerate(self.player_ids):
            role_class = role_assignments[i]
            role = role_class(player_id=player_id)
            self.players[player_id] = role

        # 狼人同伴互知
        werewolves = [pid for pid, r in self.players.items() if r.role_type == "werewolf"]
        for pid in werewolves:
            for fellow in werewolves:
                if fellow != pid:
                    self.players[pid].add_fellow_werewolf(fellow)

    def create_agents(self, decision_styles: Optional[Dict[str, str]] = None) -> None:
        """
        创建玩家代理

        Args:
            decision_styles: 角色决策风格映射 {role_type: style}
        """
        self.player_agents = {}
        styles = decision_styles or {}

        for player_id, role in self.players.items():
            style = styles.get(role.role_type)
            agent = PlayerAgent(role=role, decision_style=style)
            self.player_agents[player_id] = agent

    def _build_game_phase_state(self) -> GamePhaseState:
        """构建当前游戏阶段状态"""
        return GamePhaseState(
            phase=self.current_phase,
            day_number=self.current_day,
            alive_players=self.alive_players.copy(),
            dead_players=self.dead_players.copy(),
            previous_kills=[self.night_kill_target] if self.night_kill_target else [],
            vote_records={k: v for k, v in self.vote_records.get(self.current_day, {}).items() if v is not None},
            speech_records=self.speech_records.get(self.current_day, {}),
            checked_history=self._get_prophet_check_history(),
        )

    def _get_prophet_check_history(self) -> Dict[str, bool]:
        """获取预言家查验历史"""
        for role in self.players.values():
            if role.role_type == "prophet":
                return role.get_check_history()
        return {}

    def run_night(self) -> NightResult:
        """
        执行夜间阶段

        流程：狼人击杀 -> 预言家查验 -> 女巫用药

        Returns:
            NightResult 夜间阶段结果
        """
        self.current_day += 1
        self.current_phase = "night"
        self.werewolf_votes = {}
        self.night_kill_target = None
        self.prophet_check_target = None
        self.witch_save_target = None
        self.witch_poison_target = None

        events = []

        # 公告：夜幕降临
        self.logger.log_announcement(
            self.current_day, "night",
            f"第{self.current_day}夜，天黑请闭眼。",
            "phase"
        )

        # ===== 狼人阶段 =====
        werewolf_event = self._run_werewolf_night()
        if werewolf_event:
            events.append(werewolf_event)

        # ===== 预言家查验阶段 =====
        prophet_event = self._run_prophet_night()
        if prophet_event:
            events.append(prophet_event)

        # ===== 女巫阶段 =====
        witch_events = self._run_witch_night()
        events.extend(witch_events)

        # ===== 结算死亡 =====
        deaths = self._resolve_night_deaths()
        events.extend([d for d in deaths if hasattr(d, 'model_dump')])

        # 公告死亡结果
        if deaths:
            death_announcement = "昨夜，" + "、".join([f"玩家{p.player_id}" for p in deaths])
            if self.night_kill_target and self.witch_save_target == self.night_kill_target:
                death_announcement += "。但是女巫使用解药救活了此人！"
        else:
            death_announcement = "昨晚是平安夜，无人死亡。"

        self.logger.log_announcement(
            self.current_day, "night",
            death_announcement,
            "death"
        )

        result = NightResult(
            night_number=self.current_day,
            events=events,
            deaths=deaths,
            announcement=death_announcement,
        )

        # 记录到日记录
        day_record = DayRecord(day_number=self.current_day, night_result=result)
        self.day_records.append(day_record)

        return result

    def _run_werewolf_night(self) -> Optional[WerewolfKillEvent]:
        """执行狼人夜间击杀"""
        werewolf_players = [
            pid for pid in self.alive_players
            if self.players[pid].role_type == "werewolf"
        ]

        if not werewolf_players:
            return None

        # 获取狼人决策
        candidates = [p for p in self.alive_players if p not in werewolf_players]
        game_state = self._build_game_phase_state()

        # 使用第一个狼人的决策（简化：多狼人共享决策）
        for werewolf_id in werewolf_players:
            agent = self.player_agents.get(werewolf_id)
            if agent:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        result = agent.decide_night_action_sync(game_state)
                    else:
                        result = loop.run_until_complete(agent.decide_night_action(game_state))
                except Exception:
                    # 默认决策
                    result = self.players[werewolf_id].night_action(game_state)

                if isinstance(result, WerewolfKillResult) and result.target:
                    self.werewolf_votes[werewolf_id] = result.target

        # 统计击杀票数
        vote_count: Dict[str, int] = {}
        for target in self.werewolf_votes.values():
            vote_count[target] = vote_count.get(target, 0) + 1

        if vote_count:
            self.night_kill_target = max(vote_count, key=vote_count.get)
        elif candidates:
            # 默认击杀第一个候选人
            self.night_kill_target = candidates[0]

        self.logger.log_night_phase(
            self.current_day,
            [WerewolfKillEvent(
                event_id=str(uuid.uuid4()),
                day=self.current_day,
                phase="night",
                event_type=NightEventType.WEREWOLF_KILL,
                actors=werewolf_players,
                target=self.night_kill_target,
                success=True,
            )] if self.night_kill_target else [],
            [],
        )

        if self.night_kill_target:
            return WerewolfKillEvent(
                event_id=str(uuid.uuid4()),
                day=self.current_day,
                phase="night",
                event_type=NightEventType.WEREWOLF_KILL,
                actors=werewolf_players,
                target=self.night_kill_target,
                success=True,
            )

        return None

    def _run_prophet_night(self) -> Optional[ProphetCheckEvent]:
        """执行预言家查验"""
        prophet_id = next(
            (pid for pid, r in self.players.items() if r.role_type == "prophet" and r.is_alive),
            None
        )

        if not prophet_id:
            return None

        candidates = [p for p in self.alive_players if p != prophet_id]
        checked_history = self._get_prophet_check_history()
        candidates = [p for p in candidates if p not in checked_history]

        if not candidates:
            return None

        game_state = self._build_game_phase_state()
        agent = self.player_agents.get(prophet_id)

        try:
            if agent:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    result = agent.decide_night_action_sync(game_state)
                else:
                    result = loop.run_until_complete(agent.decide_night_action(game_state))
            else:
                result = self.players[prophet_id].night_action(game_state)
        except Exception:
            result = self.players[prophet_id].night_action(game_state)

        if isinstance(result, ProphetCheckResult) and result.target:
            self.prophet_check_target = result.target
            is_werewolf = self.players[result.target].role_type == "werewolf"
            role_name = self.players[result.target].role_type

            # 记录查验结果
            self.players[prophet_id].add_check_result(result.target, is_werewolf, role_name)

            event = ProphetCheckEvent(
                event_id=str(uuid.uuid4()),
                day=self.current_day,
                phase="night",
                event_type=NightEventType.PROPHET_CHECK,
                actor=prophet_id,
                target=result.target,
                is_werewolf=is_werewolf,
                target_role=self.players[result.target].role_type,
            )

            self.logger.log_night_phase(self.current_day, [event], [])

            return event

        return None

    def _run_witch_night(self) -> List[Any]:
        """执行女巫夜间行动"""
        witch_id = next(
            (pid for pid, r in self.players.items() if r.role_type == "witch" and r.is_alive),
            None
        )

        events = []
        if not witch_id:
            return events

        witch = self.players[witch_id]
        game_state = self._build_game_phase_state()

        # 设置狼人击杀目标供女巫参考
        if self.night_kill_target:
            witch.set_killed_by_werewolf(self.night_kill_target)

        agent = self.player_agents.get(witch_id)

        try:
            if agent:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    result = agent.decide_night_action_sync(game_state)
                else:
                    result = loop.run_until_complete(agent.decide_night_action(game_state))
            else:
                result = witch.night_action(game_state)
        except Exception:
            result = witch.night_action(game_state)

        if isinstance(result, WitchSaveResult) and result.used and result.target:
            self.witch_save_target = result.target
            witch.use_save(result.target)
            events.append(WitchSaveEvent(
                event_id=str(uuid.uuid4()),
                day=self.current_day,
                phase="night",
                event_type=NightEventType.WITCH_SAVE,
                actor=witch_id,
                target=result.target,
                used=True,
            ))

        if isinstance(result, WitchPoisonResult) and result.used and result.target:
            self.witch_poison_target = result.target
            witch.use_poison(result.target)
            events.append(WitchPoisonEvent(
                event_id=str(uuid.uuid4()),
                day=self.current_day,
                phase="night",
                event_type=NightEventType.WITCH_POISON,
                actor=witch_id,
                target=result.target,
                used=True,
            ))

        if events:
            self.logger.log_night_phase(self.current_day, events, [])

        return events

    def _resolve_night_deaths(self) -> List[DeathRecord]:
        """结算夜间死亡"""
        deaths = []

        # 狼人击杀（可能被女巫救）
        if self.night_kill_target:
            # 检查是否被女巫救
            if self.witch_save_target != self.night_kill_target:
                death = DeathRecord(
                    player_id=self.night_kill_target,
                    day=self.current_day,
                    phase="night",
                    reason=SchemaDeathReason.WEREWOLF_KILL,
                    killer="werewolf",
                )
                deaths.append(death)
                self._kill_player(self.night_kill_target, SchemaDeathReason.WEREWOLF_KILL)

        # 女巫毒杀
        if self.witch_poison_target:
            death = DeathRecord(
                player_id=self.witch_poison_target,
                day=self.current_day,
                phase="night",
                reason=SchemaDeathReason.WITCH_POISON,
                killer="witch",
            )
            deaths.append(death)
            self._kill_player(self.witch_poison_target, SchemaDeathReason.WITCH_POISON)

        # 猎人追刀（在死亡时触发）
        for death in deaths:
            player = self.players.get(death.player_id)
            if player and player.role_type == "hunter":
                hunter_shoot_target = self._resolve_hunter_shoot(death.player_id)
                if hunter_shoot_target:
                    hunter_death = DeathRecord(
                        player_id=hunter_shoot_target,
                        day=self.current_day,
                        phase="night",
                        reason=SchemaDeathReason.HUNTER_SHOOT,
                        killer=death.player_id,
                    )
                    deaths.append(hunter_death)
                    self._kill_player(hunter_shoot_target, SchemaDeathReason.HUNTER_SHOOT)

        for death in deaths:
            self.logger.log_death(death)
            self.death_records.append(death)

        return deaths

    def _resolve_hunter_shoot(self, hunter_id: str) -> Optional[str]:
        """处理猎人追刀"""
        hunter = self.players.get(hunter_id)
        if not hunter or hunter.role_type != "hunter":
            return None

        # 检查猎人是否可以开枪（被毒死不能开枪）
        hunter_can_shoot = getattr(hunter, 'can_shoot', True)

        if not hunter_can_shoot:
            return None

        candidates = [p for p in self.alive_players if p != hunter_id]
        if not candidates:
            return None

        agent = self.player_agents.get(hunter_id)
        game_state = self._build_game_phase_state()

        try:
            if agent:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    target = agent.decide_hunter_shoot_sync(game_state)
                else:
                    target = loop.run_until_complete(agent.decide_hunter_shoot(game_state))
            else:
                target = candidates[0]  # 默认第一个
        except Exception:
            target = candidates[0]

        return target if target in candidates else None

    def _kill_player(self, player_id: str, reason: SchemaDeathReason) -> None:
        """标记玩家死亡"""
        if player_id in self.alive_players:
            self.alive_players.remove(player_id)
            self.dead_players.append(player_id)
            if player_id in self.players:
                self.players[player_id].die(reason=reason.value)

    def run_day(self) -> DayResult:
        """
        执行白天阶段

        流程：公告死亡 -> 遗言 -> 发言 -> 投票 -> 表决

        Returns:
            DayResult 白天阶段结果
        """
        self.current_phase = "day"
        events = []
        self.speech_records[self.current_day] = {}
        self.vote_records[self.current_day] = {}

        # 公告天亮
        self.logger.log_announcement(
            self.current_day, "day",
            f"第{self.current_day}天，昨晚无死亡玩家。" if not self.death_records else f"第{self.current_day}天到来。",
            "phase"
        )

        # ===== 死亡宣告 =====
        if self.death_records:
            recent_deaths = [d for d in self.death_records if d.day == self.current_day and d.phase == "night"]
            for death in recent_deaths:
                player = self.players.get(death.player_id)
                if player:
                    self.logger.log_announcement(
                        self.current_day, "day",
                        f"玩家{death.player_id}死亡（{death.reason.value}）。",
                        "death"
                    )

        # ===== 发言阶段 =====
        speech_events = self._run_speeches()
        events.extend(speech_events)

        # ===== 投票阶段 =====
        vote_events = self._run_votes()
        events.extend(vote_events)

        # ===== 结算死亡 =====
        deaths = self._resolve_day_deaths()

        result = DayResult(
            day_number=self.current_day,
            events=events,
            deaths=deaths,
            final_announcement=f"第{self.current_day}天投票结束。" if not deaths else f"玩家{deaths[0].player_id}被投票出局。",
        )

        # 更新日记录
        if self.day_records and self.day_records[-1].day_number == self.current_day:
            self.day_records[-1].day_result = result
        else:
            day_record = DayRecord(day_number=self.current_day, day_result=result)
            self.day_records.append(day_record)

        return result

    def _run_speeches(self) -> List[SpeechEvent]:
        """执行发言阶段"""
        events = []
        alive = [p for p in self.alive_players]

        for order, player_id in enumerate(alive):
            agent = self.player_agents.get(player_id)
            game_state = self._build_game_phase_state()

            try:
                if agent:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        result = agent.decide_day_speech_sync(game_state)
                    else:
                        result = loop.run_until_complete(agent.decide_day_speech(game_state))
                else:
                    result = SpeakResult(action=ActionType.SPEAK, content="过。")
            except Exception:
                result = SpeakResult(action=ActionType.SPEAK, content="过。")

            content = result.content if isinstance(result, SpeakResult) else "过。"
            self.speech_records[self.current_day][player_id] = content

            event = SpeechEvent(
                event_id=str(uuid.uuid4()),
                day=self.current_day,
                phase="day",
                event_type=DayEventType.SPEECH,
                speaker=player_id,
                content=content,
                speech_order=order,
            )
            events.append(event)
            self.logger.log_speech(self.current_day, player_id, content, order)

        return events

    def _run_votes(self) -> List[VoteEvent]:
        """执行投票阶段"""
        events = []
        alive = [p for p in self.alive_players]

        for order, voter_id in enumerate(alive):
            agent = self.player_agents.get(voter_id)
            game_state = self._build_game_phase_state()

            try:
                if agent:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        result = agent.decide_vote_sync(game_state)
                    else:
                        result = loop.run_until_complete(agent.decide_vote(game_state))
                else:
                    result = VoteResult(action=ActionType.VOTE, target=None)
            except Exception:
                result = VoteResult(action=ActionType.VOTE, target=None)

            target = result.target if isinstance(result, VoteResult) else None
            self.vote_records[self.current_day][voter_id] = target

            event = VoteEvent(
                event_id=str(uuid.uuid4()),
                day=self.current_day,
                phase="day",
                event_type=DayEventType.VOTE,
                voter=voter_id,
                target=target,
                vote_order=order,
            )
            events.append(event)
            self.logger.log_vote(self.current_day, voter_id, target, order)

        return events

    def _resolve_day_deaths(self) -> List[DeathRecord]:
        """结算白天投票死亡"""
        if self.current_day not in self.vote_records:
            return []

        votes: Dict[str, int] = {}
        for voter, voted in self.vote_records[self.current_day].items():
            if voted:
                votes[voted] = votes.get(voted, 0) + 1

        if not votes:
            return []

        max_votes = max(votes.values())
        candidates = [p for p, count in votes.items() if count == max_votes]

        # 如果有最高票者且票数超过半数，则出局
        if len(candidates) == 1 and max_votes > len(self.alive_players) // 2:
            exiled = candidates[0]
            death = DeathRecord(
                player_id=exiled,
                day=self.current_day,
                phase="day",
                reason=SchemaDeathReason.VOTE_EXILE,
                killer="vote",
            )

            self._kill_player(exiled, SchemaDeathReason.VOTE_EXILE)

            self.logger.log_exile(
                self.current_day,
                exiled,
                max_votes,
                sum(votes.values()),
            )
            self.logger.log_announcement(
                self.current_day, "day",
                f"玩家{exiled}被投票出局（{max_votes}票）。",
                "exile"
            )
            self.logger.log_death(death)
            self.death_records.append(death)

            # 猎人追刀
            player = self.players.get(exiled)
            if player and player.role_type == "hunter":
                hunter_shoot_target = self._resolve_hunter_shoot(exiled)
                if hunter_shoot_target:
                    hunter_death = DeathRecord(
                        player_id=hunter_shoot_target,
                        day=self.current_day,
                        phase="day",
                        reason=SchemaDeathReason.HUNTER_SHOOT,
                        killer=exiled,
                    )
                    self._kill_player(hunter_shoot_target, SchemaDeathReason.HUNTER_SHOOT)
                    self.logger.log_death(hunter_death)
                    self.death_records.append(hunter_death)
                    return [death, hunter_death]

            return [death]

        return []

    def check_win_condition(self) -> Tuple[bool, Optional[Winner]]:
        """
        检查胜负条件

        Returns:
            (is_game_over, winner)
        """
        werewolf_alive = [p for p in self.alive_players if self.players[p].role_type == "werewolf"]
        village_alive = [p for p in self.alive_players if self.players[p].camp == "village"]

        # 狼人胜利条件：好人数量 <= 狼人数量
        if len(village_alive) <= len(werewolf_alive):
            self.is_game_over = True
            self.winner = Winner.WEREWOLF
            return True, Winner.WEREWOLF

        # 好人胜利条件：狼人全部死亡
        if not werewolf_alive:
            self.is_game_over = True
            self.winner = Winner.VILLAGE
            return True, Winner.VILLAGE

        return False, None

    def get_game_record(self) -> GameRecord:
        """获取完整游戏记录"""
        # 构建玩家信息
        player_infos = []
        for player_id in self.player_ids:
            role = self.players.get(player_id)
            if role:
                player_infos.append(PlayerInfo(
                    player_id=player_id,
                    role_type=RoleType(role.role_type),
                    camp=CampType(role.camp),
                ))

        # 构建玩家结果
        player_results = []
        for player_id in self.player_ids:
            role = self.players.get(player_id)
            if role:
                death_day = None
                death_reason = None
                for death in self.death_records:
                    if death.player_id == player_id:
                        death_day = death.day
                        death_reason = death.reason
                        break

                player_results.append(PlayerResult(
                    player_id=player_id,
                    role_type=RoleType(role.role_type),
                    camp=CampType(role.camp),
                    is_alive=role.is_alive,
                    survived_until_day=death_day,
                    death_reason=death_reason,
                ))

        game_result = GameResult(
            winner=self.winner or Winner.DRAW,
            survival_players=self.alive_players.copy(),
            player_results=player_results,
            total_days=self.current_day,
        ) if self.is_game_over else None

        return GameRecord(
            game_info=GameInfo(
                game_id=self.game_id or "",
                start_time=datetime.now(),
                mode=GameMode.SIMPLE,
                settings=GameSettings(
                    mode=GameMode.SIMPLE,
                    player_count=5,
                    werewolf_count=2,
                    god_count=2,
                    villager_count=1,
                ),
                player_ids=self.player_ids,
            ),
            players=player_infos,
            day_records=self.day_records.copy(),
            game_result=game_result,
        )

    def end_game(self) -> GameResult:
        """结束游戏，保存记录"""
        game_record = self.get_game_record()

        result = GameResult(
            winner=self.winner or Winner.DRAW,
            survival_players=self.alive_players.copy(),
            player_results=game_record.game_result.player_results if game_record.game_result else [],
            total_days=self.current_day,
        )

        self.logger.end_game(game_record, result)

        return result

    def run_full_game(self) -> GameResult:
        """
        运行完整游戏流程

        Returns:
            GameResult 游戏结果
        """
        # 开始游戏
        self.start_game()
        self.create_agents()

        while not self.is_game_over:
            # 夜间阶段
            self.run_night()

            # 检查胜负
            is_over, winner = self.check_win_condition()
            if is_over:
                break

            # 白天阶段
            self.run_day()

            # 检查胜负
            is_over, winner = self.check_win_condition()
            if is_over:
                break

        return self.end_game()