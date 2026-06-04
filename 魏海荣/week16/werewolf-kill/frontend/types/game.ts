// Game Types for Werewolf Kill Frontend

export type Phase = 'waiting' | 'night' | 'day' | 'vote' | 'ended'
export type Camp = 'werewolf' | 'village'
export type RoleType = 'werewolf' | 'prophet' | 'witch' | 'hunter' | 'villager'
export type DeathReason = 'werewolf_kill' | 'vote' | 'hunter_shoot' | 'witch_poison'

export interface Player {
  player_id: string
  role_type: RoleType
  camp: Camp
  is_alive: boolean
  seat_number?: number
}

export interface GameInfo {
  game_id: string
  phase: Phase
  day: number
  alive_players: string[]
  dead_players: string[]
  is_game_over: boolean
  winner?: 'werewolf' | 'village'
}

export interface NightResult {
  day_number: number
  events: GameEvent[]
  deaths: DeathRecord[]
  announcement: string
}

export interface DayResult {
  day_number: number
  events: GameEvent[]
  deaths: DeathRecord[]
  final_announcement: string
}

export interface DeathRecord {
  player_id: string
  day: number
  phase: 'night' | 'day'
  reason: DeathReason
  killer: string
}

export interface GameEvent {
  event_id: string
  timestamp: string
  day: number
  phase: 'night' | 'day'
  event_type: string
  [key: string]: unknown
}

export interface SpeechEvent extends GameEvent {
  event_type: 'speech'
  speaker: string
  content: string
  speech_order: number
}

export interface VoteEvent extends GameEvent {
  event_type: 'vote'
  voter: string
  target: string | null
  vote_order: number
}

export interface WerewolfKillEvent extends GameEvent {
  event_type: 'werewolf_kill'
  actors: string[]
  target: string
  success: boolean
}

export interface ProphetCheckEvent extends GameEvent {
  event_type: 'prophet_check'
  prophet: string
  target: string
  result: boolean // true = werewolf
}

export interface GameRecord {
  game_id: string
  game_info: {
    game_id: string
    start_time: string
    end_time?: string
    mode: string
    settings: {
      mode: string
      player_count: number
    }
    player_ids: string[]
  }
  players: Player[]
  day_records: DayRecord[]
  game_result?: {
    winner: 'werewolf' | 'village'
    survival_players: string[]
    total_days: number
  }
}

export interface DayRecord {
  day_number: number
  night_result?: NightResult
  day_result?: DayResult
}

// WebSocket Message Types
export type WSMessageType =
  | 'phase_change'
  | 'speech'
  | 'vote'
  | 'death'
  | 'game_over'
  | 'player_joined'
  | 'player_left'

export interface WSMessage {
  type: WSMessageType
  game_id: string
  [key: string]: unknown
}

export interface WSPhaseChange extends WSMessage {
  type: 'phase_change'
  phase: Phase
  day: number
}

export interface WSSpeech extends WSMessage {
  type: 'speech'
  playerId: string
  content: string
  speech_order: number
}

export interface WSVote extends WSMessage {
  type: 'vote'
  voter: string
  target: string | null
  votes: Record<string, string>
}

export interface WSDeath extends WSMessage {
  type: 'death'
  playerId: string
  reason: DeathReason
}

export interface WSGameOver extends WSMessage {
  type: 'game_over'
  winner: 'werewolf' | 'village'
}

// API Response Types
export interface CreateGameResponse {
  game_id: string
  player_ids: string[]
  settings: {
    mode: string
    player_count: number
  }
}

export interface NightResultResponse {
  day_number: number
  events: GameEvent[]
  deaths: DeathRecord[]
  announcement: string
}

export interface DayResultResponse {
  day_number: number
  events: GameEvent[]
  deaths: DeathRecord[]
  final_announcement: string
}
