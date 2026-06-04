'use client'

import { motion } from 'framer-motion'
import type { Player, Camp } from '@/types/game'
import { roleIcons, campIcons } from './Icons'

interface PlayerCardProps {
  player: Player
  isAlive: boolean
  isSpeaking?: boolean
  isVoting?: boolean
  voteCount?: number
  isTargeted?: boolean
  currentPlayerId?: string
  onClick?: () => void
  showCamp?: boolean
  showRole?: boolean
  myPlayerId?: string
}

export function PlayerCard({
  player,
  isAlive,
  isSpeaking = false,
  isVoting = false,
  voteCount = 0,
  isTargeted = false,
  showCamp = false,
  showRole = false,
  myPlayerId,
  onClick,
}: PlayerCardProps) {
  const isMe = player.player_id === myPlayerId
  const camp: Camp = player.camp

  const borderColor = !isAlive
    ? 'border-dead-color/50'
    : camp === 'werewolf'
    ? 'border-werewolf-camp'
    : 'border-village-camp'

  const glowColor = !isAlive
    ? 'shadow-dead-color/20'
    : camp === 'werewolf'
    ? 'shadow-werewolf-camp/50'
    : 'shadow-village-camp/50'

  return (
    <motion.div
      className={`
        relative flex flex-col items-center gap-2 p-3 rounded-xl
        bg-surface/80 backdrop-blur-sm
        border-2 ${borderColor}
        ${!isAlive ? 'opacity-50 grayscale' : ''}
        ${isTargeted ? 'ring-2 ring-secondary ring-offset-2 ring-offset-background' : ''}
        ${isSpeaking ? 'ring-2 ring-accent ring-offset-2 ring-offset-background' : ''}
        ${isVoting ? 'cursor-pointer hover:bg-surface-light' : ''}
        transition-all duration-300
      `}
      whileHover={isAlive && isVoting ? { scale: 1.05 } : {}}
      whileTap={isAlive && isVoting ? { scale: 0.95 } : {}}
      onClick={isAlive && isVoting ? onClick : undefined}
      initial={{ opacity: 0, y: 20 }}
      animate={{
        opacity: isAlive ? 1 : 0.5,
        y: 0,
        boxShadow: isSpeaking
          ? ['0 0 0 0 rgba(245, 158, 11, 0)', `0 0 30px 5px rgba(245, 158, 11, 0.3)`]
          : ['0 0 0 0 rgba(0, 0, 0, 0)', `0 4px 20px 0 ${glowColor}`],
      }}
      transition={{
        duration: isSpeaking ? 1.5 : 0.5,
        repeat: isSpeaking ? Infinity : 0,
        repeatType: 'reverse',
      }}
    >
      {/* Vote count badge */}
      {voteCount > 0 && (
        <motion.div
          className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-secondary text-white text-xs font-bold flex items-center justify-center"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          key={voteCount}
        >
          {voteCount}
        </motion.div>
      )}

      {/* Speaking indicator */}
      {isSpeaking && (
        <motion.div
          className="absolute -top-1 left-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-accent"
          animate={{ scale: [1, 1.3, 1], opacity: [1, 0.7, 1] }}
          transition={{ duration: 1, repeat: Infinity }}
        />
      )}

      {/* Avatar */}
      <motion.div
        className={`
          relative w-16 h-16 rounded-full
          bg-gradient-to-br from-surface-light to-surface
          border-2 ${borderColor}
          flex items-center justify-center overflow-hidden
        `}
        animate={isTargeted ? { x: [0, -3, 3, -3, 0] } : {}}
        transition={{ duration: 0.4 }}
      >
        {/* Camp icon */}
        {showCamp && (
          <div className={`
            absolute inset-0 flex items-center justify-center
            ${camp === 'werewolf' ? 'text-werewolf-camp' : 'text-village-camp'}
          `}>
            {campIcons[camp]}
          </div>
        )}

        {/* Role icon (only visible to self) */}
        {showRole && isMe && (
          <div className="absolute inset-0 flex items-center justify-center text-primary">
            {roleIcons[player.role_type]}
          </div>
        )}

        {/* Default avatar */}
        {!showCamp && !showRole && (
          <span className="text-2xl">
            {player.role_type === 'werewolf' ? '🐺' :
             player.role_type === 'prophet' ? '🔮' :
             player.role_type === 'witch' ? '🧪' :
             player.role_type === 'hunter' ? '🎯' : '🧑‍🌾'}
          </span>
        )}

        {/* Dead overlay */}
        {!isAlive && (
          <motion.div
            className="absolute inset-0 bg-dead-color/60 flex items-center justify-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <span className="text-2xl opacity-50">💀</span>
          </motion.div>
        )}
      </motion.div>

      {/* Player name */}
      <div className="text-center">
        <div className={`text-sm font-medium ${isAlive ? 'text-text-primary' : 'text-text-muted'}`}>
          {player.player_id.replace('player_', '玩家')}
        </div>
        {isMe && <div className="text-xs text-primary">你</div>}
      </div>

      {/* Status indicator */}
      <div className={`
        px-2 py-0.5 rounded text-xs
        ${!isAlive ? 'bg-dead-color/20 text-dead-color' :
          camp === 'werewolf' ? 'bg-werewolf-camp/20 text-werewolf-camp' : 'bg-village-camp/20 text-village-camp'}
      `}>
        {!isAlive ? '死亡' : camp === 'werewolf' ? '狼人' : '好人'}
      </div>
    </motion.div>
  )
}
