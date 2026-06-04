'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ReplayControls } from '@/components/ReplayControls'
import { PlayerCard } from '@/components/PlayerCard'
import { GameHeader } from '@/components/GameHeader'
import type { GameRecord, DayRecord, Player } from '@/types/game'

export default function ReplayPage() {
  const params = useParams()
  const router = useRouter()
  const gameId = params.gameId as string

  const [record, setRecord] = useState<GameRecord | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [currentDayRecordIndex, setCurrentDayRecordIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)

  // Load record
  useEffect(() => {
    async function loadRecord() {
      try {
        const response = await fetch(`http://localhost:8000/api/games/${gameId}/record`)
        const data = await response.json()
        setRecord(data)
      } catch (error) {
        console.error('Failed to load record:', error)
      } finally {
        setIsLoading(false)
      }
    }

    if (gameId) {
      loadRecord()
    }
  }, [gameId])

  // Auto play
  useEffect(() => {
    if (!isPlaying || !record) return

    const interval = setInterval(() => {
      setCurrentDayRecordIndex(prev => {
        if (prev >= (record.day_records?.length || 0) - 1) {
          setIsPlaying(false)
          return prev
        }
        return prev + 1
      })
    }, 3000 / speed)

    return () => clearInterval(interval)
  }, [isPlaying, speed, record])

  const handleSeek = useCallback((index: number) => {
    setCurrentDayRecordIndex(index)
  }, [])

  const handlePlay = useCallback(() => {
    setIsPlaying(true)
  }, [])

  const handlePause = useCallback(() => {
    setIsPlaying(false)
  }, [])

  const handleSpeedChange = useCallback((newSpeed: number) => {
    setSpeed(newSpeed)
  }, [])

  if (isLoading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-background">
        <motion.div
          className="text-center"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div className="text-4xl mb-4">📜</div>
          <div className="text-text-primary font-cinzel">加载回放中...</div>
        </motion.div>
      </main>
    )
  }

  if (!record) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="text-4xl mb-4">❌</div>
          <div className="text-text-primary font-cinzel mb-4">回放加载失败</div>
          <button
            onClick={() => router.push('/')}
            className="px-6 py-3 rounded-xl bg-primary text-white"
          >
            返回主页
          </button>
        </div>
      </main>
    )
  }

  const currentDayRecord = record.day_records?.[currentDayRecordIndex]
  const day = currentDayRecord?.day_number || 1
  const alivePlayers = record.game_result?.survival_players || []
  const allDead = record.game_info.player_ids.filter(
    (id: string) => !alivePlayers.includes(id)
  )

  return (
    <main className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <GameHeader
        day={record.game_result?.total_days || day}
        phase="ended"
        isGameOver={true}
        winner={record.game_result?.winner}
      />

      {/* Player Grid */}
      <section className="p-6">
        <div className="max-w-6xl mx-auto">
          <h2 className="font-cinzel text-text-primary mb-4">游戏回放</h2>
          <div className="grid grid-cols-5 gap-4">
            {record.players.map((player: Player, index: number) => {
              const isAlive = alivePlayers.includes(player.player_id)

              return (
                <motion.div
                  key={player.player_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <PlayerCard
                    player={player}
                    isAlive={isAlive}
                    showCamp={true}
                  />
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Day Info */}
      <section className="flex-1 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="bg-surface/80 rounded-xl p-6 border border-primary/20">
            <h3 className="font-cinzel text-xl text-text-primary mb-4">
              第 {day} 天
            </h3>

            {/* Night results */}
            {currentDayRecord?.night_result && (
              <div className="mb-6">
                <h4 className="text-sm text-primary mb-2">🌙 夜间事件</h4>
                <div className="space-y-2">
                  {currentDayRecord.night_result.events.map((event: any, i: number) => (
                    <div key={i} className="text-text-muted text-sm">
                      {event.event_type === 'werewolf_kill' && (
                        <>狼人击杀: {event.target}</>
                      )}
                      {event.event_type === 'prophet_check' && (
                        <>预言家查验: {event.target} 是 {event.result ? '狼人' : '好人'}</>
                      )}
                      {event.event_type === 'witch_save' && (
                        <>女巫救人</>
                      )}
                      {event.event_type === 'witch_poison' && (
                        <>女巫毒杀: {event.target}</>
                      )}
                    </div>
                  ))}
                  {currentDayRecord.night_result.deaths?.length > 0 && (
                    <div className="text-secondary text-sm">
                      死亡: {currentDayRecord.night_result.deaths.map((d: any) => d.player_id).join(', ')}
                    </div>
                  )}
                  {currentDayRecord.night_result.deaths?.length === 0 && (
                    <div className="text-text-muted text-sm">平安夜</div>
                  )}
                </div>
              </div>
            )}

            {/* Day results */}
            {currentDayRecord?.day_result && (
              <div>
                <h4 className="text-sm text-accent mb-2">☀️ 白天事件</h4>
                <div className="space-y-2">
                  {currentDayRecord.day_result.events
                    .filter((e: any) => e.event_type === 'speech')
                    .map((event: any, i: number) => (
                      <div key={i} className="text-text-muted text-sm">
                        <span className="text-text-primary">{event.speaker}:</span> {event.content}
                      </div>
                    ))}
                  {currentDayRecord.day_result.deaths?.length > 0 && (
                    <div className="text-secondary text-sm">
                      投票出局: {currentDayRecord.day_result.deaths.map((d: any) => d.player_id).join(', ')}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Replay Controls */}
      <section className="p-6 border-t border-primary/20">
        <div className="max-w-4xl mx-auto">
          <ReplayControls
            record={record}
            onSeek={handleSeek}
            onPlay={handlePlay}
            onPause={handlePause}
            onSpeedChange={handleSpeedChange}
            isPlaying={isPlaying}
            currentDayRecordIndex={currentDayRecordIndex}
            speed={speed}
          />
        </div>
      </section>

      {/* Back button */}
      <div className="fixed bottom-4 left-4">
        <button
          onClick={() => router.push('/')}
          className="px-4 py-2 rounded-lg bg-surface-light text-text-muted hover:text-text-primary transition-colors"
        >
          ← 返回
        </button>
      </div>
    </main>
  )
}
