'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { MoonIcon } from '@/components/Icons'

export default function HomePage() {
  const router = useRouter()
  const [gameId, setGameId] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [isJoining, setIsJoining] = useState(false)

  const handleCreateGame = async () => {
    setIsCreating(true)
    try {
      const response = await fetch('http://localhost:8000/api/games', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      const data = await response.json()
      router.push(`/game/${data.game_id}`)
    } catch (error) {
      console.error('Failed to create game:', error)
      setIsCreating(false)
    }
  }

  const handleJoinGame = async () => {
    if (!gameId.trim()) return
    setIsJoining(true)
    try {
      const response = await fetch(`http://localhost:8000/api/games/${gameId}`)
      if (response.ok) {
        router.push(`/game/${gameId}`)
      } else {
        alert('游戏不存在')
        setIsJoining(false)
      }
    } catch (error) {
      console.error('Failed to join game:', error)
      setIsJoining(false)
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-gradient-to-b from-purple-950/20 via-background to-background" />
      <div className="absolute inset-0 blood-texture" />

      {/* Floating particles */}
      {[...Array(20)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 rounded-full bg-primary/30"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
          }}
          animate={{
            y: [0, -30, 0],
            opacity: [0.3, 0.6, 0.3],
          }}
          transition={{
            duration: 3 + Math.random() * 2,
            repeat: Infinity,
            delay: Math.random() * 2,
          }}
        />
      ))}

      {/* Moon glow */}
      <motion.div
        className="absolute top-20 right-20 w-32 h-32 rounded-full bg-gradient-to-br from-yellow-200 to-yellow-500"
        style={{
          boxShadow: '0 0 60px 20px rgba(253, 224, 71, 0.2), 0 0 100px 40px rgba(253, 224, 71, 0.1)',
        }}
        animate={{
          boxShadow: [
            '0 0 60px 20px rgba(253, 224, 71, 0.2), 0 0 100px 40px rgba(253, 224, 71, 0.1)',
            '0 0 80px 30px rgba(253, 224, 71, 0.3), 0 0 120px 50px rgba(253, 224, 71, 0.15)',
            '0 0 60px 20px rgba(253, 224, 71, 0.2), 0 0 100px 40px rgba(253, 224, 71, 0.1)',
          ],
        }}
        transition={{ duration: 4, repeat: Infinity }}
      />

      {/* Content */}
      <motion.div
        className="relative z-10 text-center"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
      >
        {/* Logo */}
        <motion.div
          className="mb-8"
          animate={{ rotate: [0, 5, -5, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        >
          <MoonIcon className="w-24 h-24 text-primary mx-auto" />
        </motion.div>

        {/* Title */}
        <h1 className="font-cinzel text-6xl text-text-primary mb-4 tracking-wider">
          狼人杀
        </h1>
        <p className="text-text-muted text-lg mb-12">
          Werewolf Kill · AI Social Deduction Game
        </p>

        {/* Actions */}
        <div className="flex flex-col items-center gap-6">
          {/* Create Game */}
          <motion.button
            onClick={handleCreateGame}
            disabled={isCreating}
            className="relative px-12 py-4 rounded-xl bg-gradient-to-r from-primary to-purple-600 text-white font-cinzel text-lg tracking-wider overflow-hidden group disabled:opacity-50"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <span className="relative z-10">
              {isCreating ? '创建中...' : '创建游戏'}
            </span>
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-purple-600 to-primary"
              initial={{ x: '-100%' }}
              whileHover={{ x: 0 }}
              transition={{ duration: 0.3 }}
            />
          </motion.button>

          {/* Divider */}
          <div className="flex items-center gap-4 text-text-muted">
            <div className="w-16 h-px bg-text-muted/30" />
            <span className="text-sm">或者</span>
            <div className="w-16 h-px bg-text-muted/30" />
          </div>

          {/* Join Game */}
          <div className="flex gap-3">
            <input
              type="text"
              value={gameId}
              onChange={(e) => setGameId(e.target.value)}
              placeholder="输入游戏ID"
              className="px-4 py-3 rounded-xl bg-surface border border-primary/30 text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary w-64"
              onKeyDown={(e) => e.key === 'Enter' && handleJoinGame()}
            />
            <motion.button
              onClick={handleJoinGame}
              disabled={isJoining || !gameId.trim()}
              className="px-6 py-3 rounded-xl bg-surface-light border border-primary/30 text-text-primary hover:border-primary transition-colors disabled:opacity-50"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {isJoining ? '加入中...' : '加入'}
            </motion.button>
          </div>
        </div>

        {/* Features */}
        <div className="mt-16 grid grid-cols-3 gap-8 text-center">
          {[
            { icon: '🌙', title: '月夜对决', desc: '紧张刺激的社交推理' },
            { icon: '🤖', title: 'AI玩家', desc: '智能NPC角色扮演' },
            { icon: '🎭', title: '多样角色', desc: '预言家女巫猎人村民' },
          ].map((feature, i) => (
            <motion.div
              key={i}
              className="p-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + i * 0.1 }}
            >
              <div className="text-3xl mb-2">{feature.icon}</div>
              <div className="font-cinzel text-text-primary mb-1">{feature.title}</div>
              <div className="text-sm text-text-muted">{feature.desc}</div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Footer */}
      <div className="absolute bottom-4 text-text-muted text-sm">
        Powered by AI Agents
      </div>
    </main>
  )
}
