'use client'

import { motion, AnimatePresence } from 'framer-motion'
import type { Phase } from '@/types/game'
import { MoonIcon, SunIcon } from './Icons'

interface PhaseTransitionProps {
  phase: Phase
  day: number
  isPlaying: boolean
  onComplete?: () => void
}

export function PhaseTransition({ phase, day, isPlaying, onComplete }: PhaseTransitionProps) {
  const isNight = phase === 'night'

  return (
    <AnimatePresence>
      {isPlaying && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onAnimationComplete={onComplete}
        >
          {/* Background overlay */}
          <motion.div
            className={`
              absolute inset-0
              ${isNight
                ? 'bg-gradient-to-b from-purple-950 via-background to-background'
                : 'bg-gradient-to-b from-amber-950 via-background to-background'
              }
            `}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />

          {/* Moon or Sun */}
          <motion.div
            className="relative"
            initial={{
              opacity: 0,
              scale: 0.5,
              y: isNight ? 100 : -100,
            }}
            animate={{
              opacity: 1,
              scale: 1,
              y: 0,
            }}
            exit={{
              opacity: 0,
              scale: 0.8,
              y: isNight ? -50 : 50,
            }}
            transition={{
              duration: 1,
              ease: 'easeOut',
            }}
          >
            {/* Moon */}
            {isNight && (
              <motion.div
                className="w-40 h-40 rounded-full bg-gradient-to-br from-yellow-200 via-yellow-100 to-yellow-300"
                style={{
                  boxShadow: '0 0 60px 20px rgba(253, 224, 71, 0.3), 0 0 100px 40px rgba(253, 224, 71, 0.1)',
                }}
                animate={{
                  boxShadow: [
                    '0 0 60px 20px rgba(253, 224, 71, 0.3), 0 0 100px 40px rgba(253, 224, 71, 0.1)',
                    '0 0 80px 30px rgba(253, 224, 71, 0.4), 0 0 120px 50px rgba(253, 224, 71, 0.15)',
                    '0 0 60px 20px rgba(253, 224, 71, 0.3), 0 0 100px 40px rgba(253, 224, 71, 0.1)',
                  ],
                }}
                transition={{ duration: 3, repeat: Infinity }}
              >
                {/* Moon craters */}
                <div className="absolute top-8 left-12 w-6 h-6 rounded-full bg-yellow-200/50" />
                <div className="absolute top-16 right-10 w-8 h-8 rounded-full bg-yellow-200/30" />
                <div className="absolute bottom-12 left-16 w-4 h-4 rounded-full bg-yellow-200/40" />
              </motion.div>
            )}

            {/* Sun */}
            {!isNight && (
              <motion.div
                className="w-40 h-40 rounded-full bg-gradient-to-br from-amber-200 via-amber-400 to-orange-500"
                style={{
                  boxShadow: '0 0 60px 20px rgba(251, 191, 36, 0.4), 0 0 100px 40px rgba(251, 191, 36, 0.2)',
                }}
                animate={{
                  boxShadow: [
                    '0 0 60px 20px rgba(251, 191, 36, 0.4), 0 0 100px 40px rgba(251, 191, 36, 0.2)',
                    '0 0 80px 30px rgba(251, 191, 36, 0.5), 0 0 120px 50px rgba(251, 191, 36, 0.25)',
                    '0 0 60px 20px rgba(251, 191, 36, 0.4), 0 0 100px 40px rgba(251, 191, 36, 0.2)',
                  ],
                }}
                transition={{ duration: 3, repeat: Infinity }}
              >
                {/* Sun rays */}
                {[...Array(12)].map((_, i) => (
                  <div
                    key={i}
                    className="absolute w-1 h-4 bg-amber-300 rounded-full"
                    style={{
                      left: '50%',
                      top: '-8px',
                      transformOrigin: '0 84px',
                      transform: `translateX(-50%) rotate(${i * 30}deg)`,
                    }}
                  />
                ))}
              </motion.div>
            )}
          </motion.div>

          {/* Phase text */}
          <motion.div
            className="absolute bottom-32 text-center"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.5 }}
          >
            <div className="text-4xl font-cinzel text-text-primary mb-2">
              第 {day} {day === 1 ? '天' : '天'}
            </div>
            <div className={`
              text-2xl font-cinzel
              ${isNight ? 'text-primary' : 'text-accent'}
            `}>
              {isNight ? '夜幕降临' : '天亮了'}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
