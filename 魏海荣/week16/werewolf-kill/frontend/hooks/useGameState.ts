'use client'

import { useState, useCallback } from 'react'
import type {
  GameInfo,
  NightResult,
  DayResult,
  DeathRecord,
  SpeechEvent,
  VoteEvent,
  Player,
  GameRecord
} from '@/types/game'
import * as api from '@/lib/api'

interface UseGameStateReturn {
  gameInfo: GameInfo | null
  players: Player[]
  speeches: SpeechEvent[]
  votes: VoteEvent[]
  deaths: DeathRecord[]
  nightResult: NightResult | null
  dayResult: DayResult | null
  isLoading: boolean
  error: string | null

  // Actions
  createGame: (playerIds?: string[]) => Promise<string>
  joinGame: (gameId: string) => Promise<void>
  createAgents: (decisionStyles?: Record<string, string>) => Promise<void>
  runNight: () => Promise<void>
  runDay: () => Promise<void>
  runNextPhase: () => Promise<void>
  autoRun: () => Promise<void>
  refreshState: () => Promise<void>
  reset: () => void
}

export function useGameState(): UseGameStateReturn {
  const [gameInfo, setGameInfo] = useState<GameInfo | null>(null)
  const [players, setPlayers] = useState<Player[]>([])
  const [speeches, setSpeeches] = useState<SpeechEvent[]>([])
  const [votes, setVotes] = useState<VoteEvent[]>([])
  const [deaths, setDeaths] = useState<DeathRecord[]>([])
  const [nightResult, setNightResult] = useState<NightResult | null>(null)
  const [dayResult, setDayResult] = useState<DayResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createGame = useCallback(async (playerIds?: string[]) => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await api.createGame(playerIds)
      setGameInfo({
        game_id: result.game_id,
        phase: 'waiting',
        day: 0,
        alive_players: result.player_ids,
        dead_players: [],
        is_game_over: false,
      })
      return result.game_id
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to create game'
      setError(msg)
      throw e
    } finally {
      setIsLoading(false)
    }
  }, [])

  const joinGame = useCallback(async (gameId: string) => {
    setIsLoading(true)
    setError(null)
    try {
      const info = await api.getGame(gameId) as GameInfo
      setGameInfo(info)

      // Load players from record
      const record = await api.getGameRecord(gameId) as GameRecord
      if (record.players) {
        setPlayers(record.players)
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to join game'
      setError(msg)
      throw e
    } finally {
      setIsLoading(false)
    }
  }, [])

  const createAgents = useCallback(async (decisionStyles?: Record<string, string>) => {
    if (!gameInfo?.game_id) return
    setIsLoading(true)
    setError(null)
    try {
      await api.createAgents(gameInfo.game_id, decisionStyles)
      const info = await api.getGame(gameInfo.game_id) as GameInfo
      setGameInfo(info)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to create agents'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }, [gameInfo?.game_id])

  const runNight = useCallback(async () => {
    if (!gameInfo?.game_id) return
    setIsLoading(true)
    setError(null)
    try {
      const result = await api.runNight(gameInfo.game_id) as NightResult
      setNightResult(result)

      // Update deaths
      if (result.deaths) {
        setDeaths(prev => [...prev, ...result.deaths])
      }

      // Update game info
      const info = await api.getGame(gameInfo.game_id) as GameInfo
      setGameInfo(info)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to run night'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }, [gameInfo?.game_id])

  const runDay = useCallback(async () => {
    if (!gameInfo?.game_id) return
    setIsLoading(true)
    setError(null)
    try {
      const result = await api.runDay(gameInfo.game_id) as DayResult
      setDayResult(result)

      // Extract speeches and votes from events
      const newSpeeches = result.events.filter(
        (e): e is SpeechEvent => e.event_type === 'speech'
      )
      const newVotes = result.events.filter(
        (e): e is VoteEvent => e.event_type === 'vote'
      )

      setSpeeches(prev => [...prev, ...newSpeeches])
      setVotes(prev => [...prev, ...newVotes])

      // Update deaths
      if (result.deaths) {
        setDeaths(prev => [...prev, ...result.deaths])
      }

      // Update game info
      const info = await api.getGame(gameInfo.game_id) as GameInfo
      setGameInfo(info)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to run day'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }, [gameInfo?.game_id])

  const runNextPhase = useCallback(async () => {
    if (!gameInfo?.game_id) return
    setIsLoading(true)
    setError(null)
    try {
      await api.runNextPhase(gameInfo.game_id)
      const info = await api.getGame(gameInfo.game_id) as GameInfo
      setGameInfo(info)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to run phase'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }, [gameInfo?.game_id])

  const autoRun = useCallback(async () => {
    if (!gameInfo?.game_id) return
    setIsLoading(true)
    setError(null)
    try {
      const record = await api.autoRun(gameInfo.game_id) as GameRecord
      setPlayers(record.players || [])
      setGameInfo({
        game_id: record.game_id,
        phase: 'ended',
        day: record.game_result?.total_days || 0,
        alive_players: record.game_result?.survival_players || [],
        dead_players: (record.game_info.player_ids || [])
          .filter((id: string) => !(record.game_result?.survival_players || []).includes(id)),
        is_game_over: true,
        winner: record.game_result?.winner,
      })
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to auto run'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }, [gameInfo?.game_id])

  const refreshState = useCallback(async () => {
    if (!gameInfo?.game_id) return
    try {
      const info = await api.getGame(gameInfo.game_id) as GameInfo
      setGameInfo(info)
    } catch (e) {
      console.error('Failed to refresh state:', e)
    }
  }, [gameInfo?.game_id])

  const reset = useCallback(() => {
    setGameInfo(null)
    setPlayers([])
    setSpeeches([])
    setVotes([])
    setDeaths([])
    setNightResult(null)
    setDayResult(null)
    setError(null)
  }, [])

  return {
    gameInfo,
    players,
    speeches,
    votes,
    deaths,
    nightResult,
    dayResult,
    isLoading,
    error,
    createGame,
    joinGame,
    createAgents,
    runNight,
    runDay,
    runNextPhase,
    autoRun,
    refreshState,
    reset,
  }
}
