import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#8B5CF6',
        secondary: '#DC2626',
        accent: '#F59E0B',
        background: '#0F0A1A',
        surface: '#1A1025',
        'surface-light': '#2D1F3D',
        'text-primary': '#F5F5F5',
        'text-muted': '#A78BFA',
        'werewolf-camp': '#7C3AED',
        'village-camp': '#059669',
        'dead-color': '#6B7280',
      },
      fontFamily: {
        cinzel: ['Cinzel', 'serif'],
        inter: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.6s ease-out',
        'slide-up': 'slideUp 0.6s ease-out',
        'soul-rise': 'soulRise 1.2s ease-out forwards',
        'pulse-red': 'pulseRed 0.3s ease-out',
        'vote-bounce': 'voteBounce 0.4s ease-out',
        'typing': 'typing 40ms steps(1) forwards',
        'moon-rise': 'moonRise 1.2s ease-out',
        'blood-flash': 'bloodFlash 0.5s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        soulRise: {
          '0%': { opacity: '1', transform: 'translateY(0) scale(1)' },
          '50%': { opacity: '0.8', transform: 'translateY(-30px) scale(1.1)' },
          '100%': { opacity: '0', transform: 'translateY(-60px) scale(0.8)' },
        },
        pulseRed: {
          '0%': { boxShadow: '0 0 0 0 rgba(220, 38, 38, 0.7)' },
          '100%': { boxShadow: '0 0 0 20px rgba(220, 38, 38, 0)' },
        },
        voteBounce: {
          '0%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.15)' },
          '100%': { transform: 'scale(1)' },
        },
        moonRise: {
          '0%': { opacity: '0', transform: 'translateY(100px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        bloodFlash: {
          '0%': { backgroundColor: 'rgba(220, 38, 38, 0.3)' },
          '100%': { backgroundColor: 'transparent' },
        },
      },
    },
  },
  plugins: [],
}

export default config
