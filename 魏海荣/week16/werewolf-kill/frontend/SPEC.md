# 狼人杀前端 - SPEC.md

## 1. Concept & Vision

一个沉浸式的狼人杀游戏前端界面，采用黑暗哥特风格，营造神秘、紧张的社交推理氛围。界面以深紫和暗红为主色调，配合微妙的血迹纹理和月光效果，让玩家仿佛置身于月圆之夜的村庄。

## 2. Design Language

### Aesthetic Direction
- **风格**: 黑暗哥特 + 暗黑幻想
- **参考**: 《血与尊严》桌游界面 + 《Among Us》太空风格
- **关键词**: 月夜、神秘、紧张、社交推理

### Color Palette
```
Primary (狼人紫):     #8B5CF6
Secondary (血红色):   #DC2626
Accent (月光金):      #F59E0B
Background (深夜黑):  #0F0A1A
Surface (暗紫):       #1A1025
Surface-light:        #2D1F3D
Text-primary:         #F5F5F5
Text-muted:           #A78BFA
Werewolf-camp:        #7C3AED
Village-camp:          #059669
Dead-color:           #6B7280
```

### Typography
- **标题**: Cinzel (衬线，哥特感)
- **正文**: Inter (清晰易读)
- **数字/计时**: JetBrains Mono (等宽)

### Motion Philosophy
- 死亡动画: 灵魂飘散 + 渐隐 (800ms ease-out)
- 投票: 票数累积动画 + 高亮 (400ms spring)
- 发言气泡: 打字机效果 (40ms/字符)
- 阶段切换: 满月升起效果 (1200ms)
- 玩家入场: 从阴影中走出 (600ms staggered)

## 3. Layout & Structure

### Main Game Screen
```
┌─────────────────────────────────────────────────────────┐
│  [月相图标]  第 {N} 天 · {白天/夜晚}        [设置]    │  <- 顶部栏
├─────────────────────────────────────────────────────────┤
│                                                         │
│     [玩家1]    [玩家2]    [玩家3]    [玩家4]    [玩家5] │  <- 玩家区
│       ↑          ↑          ↑          ↑          ↑    │
│     发言中      存活       存活       死亡       存活   │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐   │
│  │ 发言内容显示区域 (气泡 + 历史)                      │   │  <- 发言区
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  [投票条] 或 [行动按钮]           [倒计时: 00:30]        │  <- 底部操作区
└─────────────────────────────────────────────────────────┘
```

### Responsive Strategy
- Desktop (>1024px): 5玩家横排
- Tablet (768-1024px): 5玩家横排，缩小
- Mobile (<768px): 玩家列表竖排，2列

## 4. Features & Interactions

### 核心功能

#### 4.1 游戏房间
- 显示房间ID、玩家列表
- 等待玩家加入动画
- 开始游戏按钮（房主可见）

#### 4.2 实时回合
- WebSocket 接收服务器推送
- 回合阶段: 等待 → 夜晚 → 白天 → 投票 → 结算
- 月相图标随天数的视觉变化

#### 4.3 玩家展示
- 圆形头像（默认角色图标）
- 身份标签（只有自己能看到自己的身份）
- 存活/死亡状态（死亡玩家灰显+灵魂特效）
- 当前说话玩家高亮光环
- 阵营颜色边框（狼人紫色/好人绿色）

#### 4.4 发言气泡
- 打字机效果逐字显示
- 气泡背景根据阵营着色
- 历史发言可滚动查看
- 死亡玩家发言带删除线

#### 4.5 投票系统
- 玩家头像列在投票条
- 点击投票给目标，头像之间产生票数连线动画
- 票数统计实时更新
- 投票结果高亮显示被投票出局者

#### 4.6 死亡动画
- 玩家死亡时：
  1. 头像闪烁红光 (200ms)
  2. 灵魂从身体飘出上升 (600ms)
  3. 头像渐变为灰度 (400ms)
  4. 显示死亡原因标签

#### 4.7 阵营显示
- 狼人阵营: 紫色渐变边框
- 好人阵营: 绿色渐变边框
- 死亡玩家: 灰色边框

#### 4.8 Replay 回放
- 从API获取游戏记录
- 时间轴拖动条
- 播放/暂停/倍速控制
- 每回合状态完整重放

### 交互细节

| 交互 | 效果 |
|------|------|
| 鼠标悬停玩家 | 显示玩家信息卡（轻微放大+阴影）|
| 点击投票目标 | 票数+1动画，目标头像抖动确认 |
| 死亡触发 | 屏幕轻微震动 + 红色闪烁边缘 |
| 新的一天 | 月亮升起动画 + 钟声音效提示 |
| 狼人击杀 | 红色闪电效果在目标头像 |

## 5. Component Inventory

### 5.1 GameHeader
- 月相图标 + 天数 + 阶段名称
- 设置按钮（gear图标）
- 状态: 正常 | 夜晚（深蓝色调）| 结算（高亮）

### 5.2 PlayerCard
- 头像区（80px圆形）
- 身份图标（脚下小图标）
- 玩家名称
- 存活状态 | 死亡状态（灵魂特效）
- 投票数标记
- 阵营边框色
- 状态: default | speaking | voting | dead | targeted

### 5.3 SpeechBubble
- 气泡尾巴（指向说话玩家）
- 背景（阵营色渐变）
- 打字机文字
- 时间戳
- 状态: speaking | history | dead-speaking

### 5.4 VoteBar
- 投票标题
- 玩家头像列表（可点击）
- 票数统计
- 确认/取消按钮
- 状态: idle | voting | resolved

### 5.5 ActionPanel
- 夜晚行动选择（如：狼人选择击杀目标）
- 预言家查验按钮
- 女巫救人/毒人按钮
- 状态: idle | selecting | confirmed

### 5.6 DeathAnimation
- 全屏覆盖层
- 灵魂上升粒子效果
- 死亡原因文字
- 状态: triggered | playing | finished

### 5.7 ReplayControls
- 时间轴滑块
- 播放/暂停按钮
- 倍速选择（1x, 2x, 4x）
- 回合跳转按钮

### 5.8 PhaseTransition
- 全屏动画层
- 月亮/太阳图形
- 阶段名称文字
- 状态: night-to-day | day-to-night

## 6. Technical Approach

### Framework & Build
```
- Next.js 14 (App Router)
- Tailwind CSS 3
- TypeScript
- Framer Motion (动画)
```

### Project Structure
```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx           # 主页/创建房间
│   ├── game/
│   │   └── [gameId]/
│   │       └── page.tsx  # 游戏页面
│   └── replay/
│       └── [gameId]/
│           └── page.tsx  # 回放页面
├── components/
│   ├── GameHeader.tsx
│   ├── PlayerCard.tsx
│   ├── SpeechBubble.tsx
│   ├── VoteBar.tsx
│   ├── ActionPanel.tsx
│   ├── DeathAnimation.tsx
│   ├── PhaseTransition.tsx
│   └── ReplayControls.tsx
├── hooks/
│   ├── useWebSocket.ts    # WebSocket连接
│   └── useGameState.ts    # 游戏状态管理
├── lib/
│   └── api.ts             # API调用封装
├── types/
│   └── game.ts            # TypeScript类型
└── tailwind.config.ts
```

### API Integration
- REST API: 创建游戏、获取游戏状态
- WebSocket: 实时游戏事件推送
  - `night_phase` - 夜晚开始
  - `day_phase` - 白天开始
  - `speech` - 发言
  - `vote` - 投票
  - `death` - 死亡
  - `game_over` - 游戏结束

### WebSocket Protocol
```typescript
// 客户端发送
{ type: "join", gameId: string, playerId: string }
{ type: "vote", targetId: string }
{ type: "action", action: NightAction }

// 服务器推送
{ type: "phase_change", phase: "night" | "day", day: number }
{ type: "speech", playerId: string, content: string }
{ type: "vote_update", votes: Record<string, string> }
{ type: "death", playerId: string, reason: string }
{ type: "game_over", winner: "werewolf" | "village" }
```
