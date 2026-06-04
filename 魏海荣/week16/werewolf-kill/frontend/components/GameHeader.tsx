'use client'

import { motion } from 'framer-motion'
import type { Phase } from '@/types/game'
import { MoonIcon, SunIcon, SkullIcon } from './Icons'

interface GameHeaderProps {
  day: number
  phase: Phase
  isGameOver: boolean
  winner?: 'werewolf' | 'village'
}

const phaseLabels: Record<Phase, string> = {
  waiting: '等待开始',
  night: '夜幕降临',
  day: '天亮了',
  vote: '投票阶段',
  ended: '游戏结束',
}

const phaseIcons: Record<Phase, React.ReactNode> = {
  waiting: null,
  night: <MoonIcon className="w-6 h-6" />,
  day: <SunIcon className="w-6 h-6" />,
  vote: <SkullIcon className="w-6 h-6" />,
  ended: null,
}

export function GameHeader({ day, phase, isGameOver, winner }: GameHeaderProps) {
  const isNight = phase === 'night'
  const isEnded = phase === 'ended'

  return (
    <motion.header
      className={`
        relative px-6 py-4 flex items-center justify-between
        ${isNight ? 'bg-gradient-to-b from-surface to-background' : 'bg-gradient-to-b from-surface-light to-surface'}
        ${isEnded ? 'bg-gradient-to-r from-purple-900/20 via-surface to-red-900/20' : ''}
        border-b border-primary/20
      `}
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* Moon phase indicator for night */}
      {isNight && (
        <motion.div
          className="absolute inset-0 pointer-events-none overflow-hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <motion.div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64"
            initial={{ opacity: 0, scale: 0.8, y: 50 }}
            animate={{ opacity: 0.1, scale: 1, y: 0 }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
          >
            <div className="w-full h-full rounded-full bg-gradient-to-br from-yellow-200 to-yellow-500 blur-3xl" />
          </motion.div>
        </motion.div>
      )}

      {/* Left: Day counter */}
      <div className="flex items-center gap-3">
        <motion.div
          className={`
            w-12 h-12 rounded-full flex items-center justify-center
            ${isNight ? 'bg-primary/20' : 'bg-accent/20'}
            ${isEnded ? 'bg-purple-500/20' : ''}
          `}
          animate={{
            boxShadow: isNight
              ? ['0 0 20px rgba(139, 92, 246, 0.3)', '0 0 40px rgba(139, 92, 246, 0.5)']
              : isEnded
              ? ['0 0 20px rgba(139, 92, 246, 0.3)', '0 0 20px rgba(139, 92, 246, 0.3)']
              : ['0 0 20px rgba(245, 158, 11, 0.3)', '0 0 40px rgba(245, 158, 11, 0.5)'],
          }}
          transition={{ duration: 2, repeat: Infinity, repeatType: 'reverse' }}
        >
          <span className="font-mono text-lg font-bold text-text-primary">
            {day || '-'}
          </span>
        </motion.div>

        <div>
          <div className="font-cinzel text-lg text-text-primary">
            第 {day} 天
          </div>
          <div className="text-xs text-text-muted">
            {day > 0 ? `${day} 夜过去` : '等待开始'}
          </div>
        </div>
      </div>

      {/* Center: Phase */}
      <motion.div
        className={`
          flex items-center gap-2 px-6 py-2 rounded-full
          ${isNight ? 'bg-primary/10 border border-primary/30' : 'bg-accent/10 border border-accent/30'}
          ${isEnded ? 'bg-purple-500/10 border border-purple-500/30' : ''}
        `}
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        {phaseIcons[phase] && (
          <motion.span
            className={isNight ? 'text-primary' : isEnded ? 'text-purple-400' : 'text-accent'}
            animate={{ rotate: phase === 'night' ? 360 : 0 }}
            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          >
            {phaseIcons[phase]}
          </motion.span>
        )}
        <span className={`
          font-cinzel text-sm tracking-wider
          ${isNight ? 'text-primary' : isEnded ? 'text-purple-400' : 'text-accent'}
        `}>
          {phaseLabels[phase]}
        </span>
      </motion.div>

      {/* Right: Settings */}
      <div className="flex items-center gap-2">
        {isEnded && winner && (
          <motion.div
            className={`
              px-4 py-2 rounded-lg font-cinzel text-sm
              ${winner === 'werewolf'
                ? 'bg-werewolf-camp/20 text-werewolf-camp border border-werewolf-camp/30'
                : 'bg-village-camp/20 text-village-camp border border-village-camp/30'
              }
            `}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5 }}
          >
            {winner === 'werewolf' ? '狼人胜利' : '好人胜利'}
          </motion.div>
        )}

        <button className="w-10 h-10 rounded-full bg-surface-light/50 hover:bg-surface-light flex items-center justify-center transition-colors">
          <svg className="w-5 h-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
    </motion.header>
  )
}
