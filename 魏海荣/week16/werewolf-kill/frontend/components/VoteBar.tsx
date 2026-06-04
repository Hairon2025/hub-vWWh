'use client'

import { motion } from 'framer-motion'
import type { Player } from '@/types/game'
import { VoteIcon } from './Icons'

interface VoteBarProps {
  players: Player[]
  alivePlayerIds: string[]
  votes: Record<string, string> // voter -> target
  onVote: (targetId: string) => void
  currentPlayerId?: string
  disabled?: boolean
}

export function VoteBar({
  players,
  alivePlayerIds,
  votes,
  onVote,
  currentPlayerId,
  disabled = false,
}: VoteBarProps) {
  const alivePlayers = players.filter(p => alivePlayerIds.includes(p.player_id))

  // Count votes for each player
  const voteCounts: Record<string, number> = {}
  for (const target of Object.values(votes)) {
    if (target) {
      voteCounts[target] = (voteCounts[target] || 0) + 1
    }
  }

  // Find player with most votes
  const maxVotes = Math.max(...Object.values(voteCounts), 0)

  return (
    <div className="bg-surface/80 backdrop-blur-sm rounded-xl p-4 border border-primary/20">
      <div className="flex items-center gap-2 mb-4">
        <VoteIcon className="w-5 h-5 text-secondary" />
        <h3 className="font-cinzel text-text-primary">投票阶段</h3>
      </div>

      <div className="grid grid-cols-5 gap-3">
        {alivePlayers.map((player, index) => {
          const count = voteCounts[player.player_id] || 0
          const isMax = count === maxVotes && maxVotes > 0

          return (
            <motion.div
              key={player.player_id}
              className={`
                relative flex flex-col items-center gap-2 p-3 rounded-lg
                bg-surface-light/50 border border-transparent
                ${!disabled ? 'cursor-pointer hover:border-primary/50' : ''}
                ${isMax ? 'ring-2 ring-secondary' : ''}
              `}
              whileHover={!disabled ? { scale: 1.05 } : {}}
              whileTap={!disabled ? { scale: 0.95 } : {}}
              onClick={() => !disabled && onVote(player.player_id)}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              {/* Avatar */}
              <motion.div
                className={`
                  w-12 h-12 rounded-full
                  bg-gradient-to-br from-surface to-surface-light
                  border-2
                  ${player.camp === 'werewolf' ? 'border-werewolf-camp' : 'border-village-camp'}
                  flex items-center justify-center
                `}
                animate={isMax ? {
                  boxShadow: ['0 0 0 0 rgba(220, 38, 38, 0)', '0 0 20px 5px rgba(220, 38, 38, 0.4)'],
                } : {}}
                transition={{ duration: 0.8, repeat: Infinity }}
              >
                <span className="text-xl">
                  {player.role_type === 'werewolf' ? '🐺' :
                   player.role_type === 'prophet' ? '🔮' :
                   player.role_type === 'witch' ? '🧪' :
                   player.role_type === 'hunter' ? '🎯' : '🧑‍🌾'}
                </span>
              </motion.div>

              {/* Name */}
              <span className="text-xs text-text-muted">
                {player.player_id.replace('player_', 'P')}
              </span>

              {/* Vote count */}
              {count > 0 && (
                <motion.div
                  className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-secondary text-white text-xs font-bold flex items-center justify-center"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  key={count}
                >
                  {count}
                </motion.div>
              )}

              {/* Vote line indicator */}
              {votes[currentPlayerId || ''] === player.player_id && (
                <div className="absolute inset-0 rounded-lg border-2 border-primary animate-pulse" />
              )}
            </motion.div>
          )
        })}
      </div>

      {/* Vote instructions */}
      <div className="mt-4 text-center text-sm text-text-muted">
        {disabled ? '等待其他玩家投票...' : '点击玩家头像进行投票'}
      </div>
    </div>
  )
}
