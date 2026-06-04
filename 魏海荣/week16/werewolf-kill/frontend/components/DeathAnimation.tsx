'use client'

import { motion, AnimatePresence } from 'framer-motion'
import type { DeathReason } from '@/types/game'
import { GhostIcon } from './Icons'

interface DeathAnimationProps {
  playerId: string
  reason: DeathReason
  isPlaying: boolean
  onComplete?: () => void
}

const reasonTexts: Record<DeathReason, string> = {
  werewolf_kill: '被狼人击杀',
  vote: '投票出局',
  hunter_shoot: '猎人追枪',
  witch_poison: '女巫毒杀',
}

export function DeathAnimation({ playerId, reason, isPlaying, onComplete }: DeathAnimationProps) {
  return (
    <AnimatePresence>
      {isPlaying && (
        <motion.div
          className="fixed inset-0 z-50 pointer-events-none"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Red flash overlay */}
          <motion.div
            className="absolute inset-0 bg-gradient-to-b from-transparent via-red-900/30 to-transparent"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.5, 0] }}
            transition={{ duration: 0.5 }}
          />

          {/* Death content */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            {/* Ghost rising */}
            <motion.div
              className="relative"
              initial={{ opacity: 0, y: 50, scale: 0.8 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <motion.div
                animate={{
                  y: [0, -10, 0],
                  opacity: [1, 0.8, 1],
                }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <GhostIcon className="w-24 h-24 text-dead-color" />
              </motion.div>

              {/* Soul particles */}
              {[...Array(8)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute w-2 h-2 rounded-full bg-purple-300"
                  initial={{
                    x: 0,
                    y: 0,
                    opacity: 1,
                    scale: 1,
                  }}
                  animate={{
                    x: (Math.random() - 0.5) * 100,
                    y: -50 - Math.random() * 50,
                    opacity: [1, 0],
                    scale: [1, 0],
                  }}
                  transition={{
                    duration: 1.5,
                    delay: 0.3 + i * 0.1,
                    ease: 'easeOut',
                  }}
                  style={{
                    left: '50%',
                    top: '50%',
                  }}
                />
              ))}
            </motion.div>

            {/* Death text */}
            <motion.div
              className="mt-8 text-center"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <div className="text-2xl font-cinzel text-text-primary mb-2">
                {playerId.replace('player_', '玩家')}
              </div>
              <div className="text-lg text-secondary">
                {reasonTexts[reason]}
              </div>
            </motion.div>
          </div>

          {/* Auto complete */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 2 }}
            onAnimationComplete={onComplete}
          />
        </motion.div>
      )}
    </AnimatePresence>
  )
}
