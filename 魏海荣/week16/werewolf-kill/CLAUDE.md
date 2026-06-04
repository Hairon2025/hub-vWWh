# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Werewolf (狼人杀) — A multi-agent collaboration and adversarial game where AI agents play the social deduction game Werewolf with information asymmetry. Each agent reasons and makes decisions based on their role objectives.

## Architecture

### Key Design Pattern: Information Asymmetry

The core architectural principle is strict information isolation:
- **Role classes** (`src/roles/*.py`) — Data models holding private role information (actual role, abilities, check history)
- **PlayerAgent** (`src/agent/player_agent.py`) — LLM-driven decision maker that receives only what each role is permitted to know
- **PublicInfo vs PrivateInfo** — Roles expose `visible_role` (what others see) vs `actual_role` (what only certain roles see)

### Core Components

| Component | File(s) | Responsibility |
|-----------|---------|----------------|
| Role Classes | `src/roles/*.py` | Data models with abilities, death/reveal logic |
| PlayerAgent | `src/agent/player_agent.py` | LLM-driven decisions (night action, speech, vote) |
| SummaryAgent | `src/agent/summary_agent.py` | Post-game experience summarization and learning |
| JudgeAgent | `src/agent/judge_agent.py` | Game flow, rule enforcement, win condition checking |
| Schemas | `src/schemas/roles_schema.py` | Pydantic models for all action results and game state |
| ExperienceManager | `src/memory/experience.py` | Persistent learning from past games per role |

### Agent Roles

| Role | Camp | Night Action | Day Action |
|------|------|--------------|------------|
| Werewolf | Werewolf | Kill a player | Vote, blend in |
| Prophet | Village | Check player role | Vote, reveal info |
| Witch | Village | Save OR poison | Vote |
| Hunter | Village | None | Vote, shoot on death |
| Villager | Village | None | Vote |

### Win Conditions

- **Werewolf wins**: Eliminate all village OR werewolf_count >= village_count
- **Village wins**: Eliminate all werewolves

## Commands

```bash
# Run the game
python src/main.py

# Run all tests
pytest tests/

# Run a specific test file
pytest tests/test_roles.py

# Run a specific test
pytest tests/test_roles.py::TestWerewolfMethods::test_night_action_alive -v
```

## Key Implementation Details

### Two-Layer Agent Architecture

1. **`BaseAgent`** (`src/agent/base.py`) — Thin wrapper around the `agents` library (Anthropic's multi-agent framework)
2. **`PlayerAgent`** (`src/agent/player_agent.py`) — Main implementation with:
   - Role-specific instruction building via `_build_instructions()`
   - Private context formatting via `_get_private_context()` (information asymmetry)
   - Game state formatting via `format_game_state()` and `format_role_specific_context()`
   - Three decision methods: `decide_night_action()`, `decide_day_speech()`, `decide_vote()`
   - Async versions for LLM calls and sync versions for game engine

### Decision Styles

PlayerAgent supports configurable decision styles per role (`aggressive`, `cautious`, `balanced`) that influence LLM prompt phrasing.

### Experience System

`ExperienceManager` persists learning to `src/memory/experience/{role_type}.json` between games. Retrieved via `get_recent_experiences()` and injected into LLM prompts.

### SummaryAgent

`SummaryAgent` (`src/agent/summary_agent.py`) generates post-game experience summaries:
- Factory pattern: `SummaryAgent.create(role_type)` creates role-specific agents
- Role-specific prompts: Each role has tailored reflection questions (e.g., werewolves analyze hiding strategy, prophets analyze check timing)
- Input: `game_record` dict containing actions, speeches, votes, outcome
- Output: `ExperienceEntry` saved automatically via `ExperienceManager`
- Usage: `await summarize_game(game_record, role_type)`

### Note

- `src/game_engine/` folder is referenced but not yet implemented — the `JudgeAgent` handles flow control for now
- Configuration is loaded from `config/system_config.json` (not yet present)
