'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { useGameState } from '@/hooks/useGameState'
import { GameHeader } from '@/components/GameHeader'
import { PlayerCard } from '@/components/PlayerCard'
import { SpeechBubble } from '@/components/SpeechBubble'
import { VoteBar } from '@/components/VoteBar'
import { DeathAnimation } from '@/components/DeathAnimation'
import { PhaseTransition } from '@/components/PhaseTransition'
import type { Player, SpeechEvent, DeathRecord, VoteEvent, NightResult, DayResult, GameRecord } from '@/types/game'

export default function GamePage() {
  const params = useParams()
  const router = useRouter()
  const gameId = params.gameId as string

  const {
    gameInfo,
    players,
    speeches,
    votes,
    deaths,
    nightResult,
    dayResult,
    isLoading,
    error,
    joinGame,
    createAgents,
    runNight,
    runDay,
    runNextPhase,
    autoRun,
    refreshState,
  } = useGameState()

  const [myPlayerId] = useState<string>('')
  const [showPhaseTransition, setShowPhaseTransition] = useState(false)
  const [pendingDeath, setPendingDeath] = useState<{ playerId: string; reason: string } | null>(null)
  const [showDeathAnimation, setShowDeathAnimation] = useState(false)

  // Join game on mount
  useEffect(() => {
    if (gameId) {
      joinGame(gameId)
    }
  }, [gameId, joinGame])

  // Auto-refresh state
  useEffect(() => {
    if (!gameInfo?.is_game_over && gameId) {
      const interval = setInterval(refreshState, 5000)
      return () => clearInterval(interval)
    }
  }, [gameInfo?.is_game_over, gameId, refreshState])

  // Handle phase transition
  const handlePhaseChange = useCallback((newPhase: string) => {
    setShowPhaseTransition(true)
  }, [])

  // Handle night action
  const handleNightAction = async () => {
    handlePhaseChange('night')
    await runNight()
  }

  // Handle day action
  const handleDayAction = async () => {
    handlePhaseChange('day')
    await runDay()
  }

  // Handle vote
  const handleVote = async (targetId: string) => {
    // For now, just show the vote - backend handles actual voting
    console.log('Vote for:', targetId)
  }

  // Handle auto run
  const handleAutoRun = async () => {
    await autoRun()
  }

  // If not connected, show loading
  if (!gameInfo) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-background">
        <motion.div
          className="text-center"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div className="text-4xl mb-4">🌙</div>
          <div className="text-text-primary font-cinzel">加载中...</div>
        </motion.div>
      </main>
    )
  }

  // If game over, show result
  if (gameInfo.is_game_over) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center bg-background p-8">
        <motion.div
          className="text-center"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <div className={`
            text-6xl mb-6
            ${gameInfo.winner === 'werewolf' ? 'text-werewolf-camp' : 'text-village-camp'}
          `}>
            {gameInfo.winner === 'werewolf' ? '🐺' : '🧑‍🌾'}
          </div>
          <h1 className="font-cinzel text-4xl text-text-primary mb-4">
            {gameInfo.winner === 'werewolf' ? '狼人胜利' : '好人胜利'}
          </h1>
          <p className="text-text-muted mb-8">
            游戏共进行了 {gameInfo.day} 天
          </p>
          <div className="flex gap-4">
            <motion.button
              onClick={() => router.push('/')}
              className="px-6 py-3 rounded-xl bg-surface-light text-text-primary hover:bg-primary/20 transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              返回主页
            </motion.button>
            <motion.button
              onClick={() => router.push(`/replay/${gameId}`)}
              className="px-6 py-3 rounded-xl bg-primary text-white hover:bg-primary/80 transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              观看回放
            </motion.button>
          </div>
        </motion.div>
      </main>
    )
  }

  // Get current speaking player (last speech)
  const currentSpeaker = speeches.length > 0 ? speeches[speeches.length - 1].speaker : null

  return (
    <main className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <GameHeader
        day={gameInfo.day}
        phase={gameInfo.phase}
        isGameOver={gameInfo.is_game_over}
        winner={gameInfo.winner}
      />

      {/* Player Grid */}
      <section className="flex-1 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-5 gap-4">
            {players.map((player, index) => {
              const isAlive = gameInfo.alive_players.includes(player.player_id)
              const voteCount = votes.filter(v => v.target === player.player_id).length

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
                    isSpeaking={currentSpeaker === player.player_id}
                    isVoting={gameInfo.phase === 'vote' && isAlive}
                    voteCount={voteCount}
                    showCamp={true}
                    showRole={player.player_id === myPlayerId}
                    myPlayerId={myPlayerId}
                    onClick={() => handleVote(player.player_id)}
                  />
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Speech Area */}
      <section className="flex-1 p-6 border-t border-primary/10">
        <div className="max-w-4xl mx-auto h-full overflow-y-auto space-y-4">
          <AnimatePresence mode="popLayout">
            {speeches.map((speech, index) => {
              const player = players.find(p => p.player_id === speech.speaker)
              const isAlive = player ? gameInfo.alive_players.includes(player.player_id) : false

              return (
                <SpeechBubble
                  key={`${speech.event_id}-${index}`}
                  speech={speech}
                  speakerName={player?.player_id.replace('player_', '玩家') || '未知'}
                  speakerCamp={player?.camp || 'village'}
                  isAlive={isAlive}
                  isCurrent={index === speeches.length - 1 && gameInfo.phase === 'day'}
                  index={index}
                />
              )
            })}
          </AnimatePresence>

          {speeches.length === 0 && (
            <div className="text-center text-text-muted py-8">
              {gameInfo.phase === 'night' ? '夜幕降临，寂静无声...' : '等待发言...'}
            </div>
          )}
        </div>
      </section>

      {/* Action Bar */}
      <section className="p-6 border-t border-primary/20 bg-surface/50">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          {/* Left: Phase info */}
          <div className="text-text-muted">
            {gameInfo.phase === 'waiting' && '等待游戏开始...'}
            {gameInfo.phase === 'night' && '夜间阶段 - 狼人请睁眼'}
            {gameInfo.phase === 'day' && '白天阶段 - 轮流发言'}
            {gameInfo.phase === 'vote' && '投票阶段'}
          </div>

          {/* Center: Action buttons */}
          <div className="flex gap-3">
            {!gameInfo.phase || gameInfo.phase === 'waiting' ? (
              <motion.button
                onClick={() => createAgents()}
                disabled={isLoading}
                className="px-6 py-3 rounded-xl bg-primary text-white font-medium hover:bg-primary/80 disabled:opacity-50 transition-colors"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {isLoading ? '创建中...' : '开始游戏'}
              </motion.button>
            ) : gameInfo.phase === 'night' ? (
              <motion.button
                onClick={handleNightAction}
                disabled={isLoading}
                className="px-6 py-3 rounded-xl bg-primary text-white font-medium hover:bg-primary/80 disabled:opacity-50 transition-colors"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {isLoading ? '处理中...' : '结束夜晚'}
              </motion.button>
            ) : gameInfo.phase === 'day' ? (
              <motion.button
                onClick={handleDayAction}
                disabled={isLoading}
                className="px-6 py-3 rounded-xl bg-accent text-background font-medium hover:bg-accent/80 disabled:opacity-50 transition-colors"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {isLoading ? '处理中...' : '结束白天'}
              </motion.button>
            ) : null}

            {/* Auto run button */}
            {(gameInfo.phase === 'night' || gameInfo.phase === 'day') && (
              <motion.button
                onClick={handleAutoRun}
                disabled={isLoading}
                className="px-6 py-3 rounded-xl bg-surface-light text-text-primary border border-primary/30 hover:border-primary disabled:opacity-50 transition-colors"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                自动进行
              </motion.button>
            )}
          </div>

          {/* Right: Game ID */}
          <div className="text-text-muted text-sm font-mono">
            {gameId}
          </div>
        </div>
      </section>

      {/* Vote Bar Overlay */}
      <AnimatePresence>
        {gameInfo.phase === 'vote' && (
          <motion.div
            className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm flex items-center justify-center p-8"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <VoteBar
              players={players}
              alivePlayerIds={gameInfo.alive_players}
              votes={votes.reduce((acc, v) => ({ ...acc, [v.voter]: v.target }), {})}
              onVote={handleVote}
              currentPlayerId={myPlayerId}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Phase Transition */}
      <PhaseTransition
        phase={gameInfo.phase}
        day={gameInfo.day}
        isPlaying={showPhaseTransition}
        onComplete={() => setShowPhaseTransition(false)}
      />

      {/* Death Animation */}
      {pendingDeath && (
        <DeathAnimation
          playerId={pendingDeath.playerId}
          reason={pendingDeath.reason as any}
          isPlaying={showDeathAnimation}
          onComplete={() => {
            setShowDeathAnimation(false)
            setPendingDeath(null)
          }}
        />
      )}

      {/* Error display */}
      {error && (
        <motion.div
          className="fixed bottom-4 right-4 px-4 py-2 rounded-lg bg-secondary/20 border border-secondary text-secondary"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
        >
          {error}
        </motion.div>
      )}
    </main>
  )
}
