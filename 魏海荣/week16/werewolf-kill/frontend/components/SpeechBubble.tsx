'use client'

import { motion } from 'framer-motion'
import type { SpeechEvent, Camp } from '@/types/game'

interface SpeechBubbleProps {
  speech: SpeechEvent
  speakerName: string
  speakerCamp: Camp
  isAlive: boolean
  isCurrent?: boolean
  index: number
}

export function SpeechBubble({
  speech,
  speakerName,
  speakerCamp,
  isAlive,
  isCurrent = false,
  index,
}: SpeechBubbleProps) {
  const bubbleBg = speakerCamp === 'werewolf'
    ? 'bg-gradient-to-r from-werewolf-camp/20 to-werewolf-camp/10'
    : 'bg-gradient-to-r from-village-camp/20 to-village-camp/10'

  return (
    <motion.div
      className="relative"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1, duration: 0.3 }}
    >
      <div className={`
        relative p-4 rounded-2xl
        ${bubbleBg}
        border border-l-4
        ${speakerCamp === 'werewolf' ? 'border-werewolf-camp' : 'border-village-camp'}
        ${!isAlive ? 'opacity-60' : ''}
        ${isCurrent ? 'ring-2 ring-accent' : ''}
      `}>
        {/* Speaker name */}
        <div className="flex items-center gap-2 mb-2">
          <span className={`
            font-medium text-sm
            ${speakerCamp === 'werewolf' ? 'text-werewolf-camp' : 'text-village-camp'}
            ${!isAlive ? 'line-through' : ''}
          `}>
            {speakerName}
          </span>
          {!isAlive && (
            <span className="text-xs text-dead-color">(已死亡)</span>
          )}
          {isCurrent && (
            <span className="text-xs text-accent animate-pulse">发言中...</span>
          )}
        </div>

        {/* Speech content with typing effect */}
        <div className="text-text-primary">
          {isCurrent ? (
            <TypingText text={speech.content} />
          ) : (
            <span className={!isAlive ? 'line-through' : ''}>{speech.content}</span>
          )}
        </div>

        {/* Timestamp */}
        <div className="mt-2 text-xs text-text-muted">
          第{speech.day}天 · 第{speech.speech_order + 1}个发言
        </div>

        {/* Tail */}
        <div className={`
          absolute -left-2 top-4 w-0 h-0
          border-t-8 border-t-transparent
          border-b-8 border-b-transparent
          border-r-8 ${speakerCamp === 'werewolf' ? 'border-r-werewolf-camp' : 'border-r-village-camp'}
        `} />
      </div>
    </motion.div>
  )
}

function TypingText({ text }: { text: string }) {
  return (
    <motion.span
      initial={{ width: '0%' }}
      animate={{ width: '100%' }}
      transition={{ duration: text.length * 0.04, ease: 'linear' }}
      className="overflow-hidden whitespace-nowrap"
    >
      {text}
    </motion.span>
  )
}
