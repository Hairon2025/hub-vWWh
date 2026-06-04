'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import type { GameRecord, DayRecord } from '@/types/game'
import { PlayIcon, PauseIcon, ChevronLeftIcon, ChevronRightIcon } from './Icons'

interface ReplayControlsProps {
  record: GameRecord
  onSeek: (dayRecordIndex: number) => void
  onPlay: () => void
  onPause: () => void
  onSpeedChange: (speed: number) => void
  isPlaying: boolean
  currentDayRecordIndex: number
  speed: number
}

export function ReplayControls({
  record,
  onSeek,
  onPlay,
  onPause,
  onSpeedChange,
  isPlaying,
  currentDayRecordIndex,
  speed,
}: ReplayControlsProps) {
  const totalDays = record.day_records?.length || 0
  const dayRecords = record.day_records || []

  return (
    <div className="bg-surface/80 backdrop-blur-sm rounded-xl p-4 border border-primary/20">
      {/* Timeline */}
      <div className="mb-4">
        <input
          type="range"
          min={0}
          max={totalDays - 1}
          value={currentDayRecordIndex}
          onChange={(e) => onSeek(parseInt(e.target.value))}
          className="w-full h-2 bg-surface-light rounded-full appearance-none cursor-pointer
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:w-4
            [&::-webkit-slider-thumb]:h-4
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:bg-primary
            [&::-webkit-slider-thumb]:cursor-pointer
            [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(139,92,246,0.5)]
          "
        />
        <div className="flex justify-between text-xs text-text-muted mt-1">
          <span>第1天</span>
          <span>第{totalDays}天</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        {/* Playback controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onSeek(Math.max(0, currentDayRecordIndex - 1))}
            disabled={currentDayRecordIndex <= 0}
            className="p-2 rounded-lg bg-surface-light hover:bg-primary/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeftIcon className="w-5 h-5 text-text-primary" />
          </button>

          <motion.button
            onClick={isPlaying ? onPause : onPlay}
            className="w-12 h-12 rounded-full bg-primary hover:bg-primary/80 flex items-center justify-center transition-colors"
            whileTap={{ scale: 0.95 }}
          >
            {isPlaying ? (
              <PauseIcon className="w-6 h-6 text-white" />
            ) : (
              <PlayIcon className="w-6 h-6 text-white ml-1" />
            )}
          </motion.button>

          <button
            onClick={() => onSeek(Math.min(totalDays - 1, currentDayRecordIndex + 1))}
            disabled={currentDayRecordIndex >= totalDays - 1}
            className="p-2 rounded-lg bg-surface-light hover:bg-primary/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRightIcon className="w-5 h-5 text-text-primary" />
          </button>
        </div>

        {/* Speed control */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-text-muted">倍速:</span>
          {[1, 2, 4].map((s) => (
            <button
              key={s}
              onClick={() => onSpeedChange(s)}
              className={`
                px-3 py-1 rounded text-sm font-mono
                ${speed === s
                  ? 'bg-primary text-white'
                  : 'bg-surface-light text-text-muted hover:bg-primary/20'
                }
                transition-colors
              `}
            >
              {s}x
            </button>
          ))}
        </div>

        {/* Current day indicator */}
        <div className="text-sm text-text-muted">
          第{dayRecords[currentDayRecordIndex]?.day_number || 1}天
        </div>
      </div>

      {/* Day markers */}
      <div className="mt-4 flex gap-1 overflow-x-auto pb-2">
        {dayRecords.map((dr, index) => (
          <button
            key={dr.day_number}
            onClick={() => onSeek(index)}
            className={`
              flex-shrink-0 px-3 py-1 rounded text-xs font-mono
              ${index === currentDayRecordIndex
                ? 'bg-primary text-white'
                : 'bg-surface-light text-text-muted hover:bg-primary/20'
              }
              transition-colors
            `}
          >
            D{dr.day_number}
          </button>
        ))}
      </div>
    </div>
  )
}
