import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '狼人杀 - Werewolf Kill',
  description: 'AI狼人杀游戏 - 与AI角色进行社交推理游戏',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">
        {children}
      </body>
    </html>
  )
}
