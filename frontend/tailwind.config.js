/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0F1117',
        card: '#1E2130',
        'card-hover': '#252A3F',
        accent: '#6C63FF',
        'accent-dim': '#4A47A3',
        'accent-glow': 'rgba(108,99,255,0.15)',
        border: '#2A2F45',
        'text-primary': '#E2E8F0',
        'text-secondary': '#94A3B8',
        'text-muted': '#64748B',
        success: '#10B981',
        warning: '#F59E0B',
        danger: '#EF4444',
        'success-dim': 'rgba(16,185,129,0.15)',
        'warning-dim': 'rgba(245,158,11,0.15)',
        'danger-dim': 'rgba(239,68,68,0.15)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-accent': 'linear-gradient(135deg, #6C63FF 0%, #4A47A3 100%)',
      },
      boxShadow: {
        'card': '0 4px 24px rgba(0,0,0,0.4)',
        'glow': '0 0 24px rgba(108,99,255,0.25)',
        'glow-sm': '0 0 12px rgba(108,99,255,0.15)',
      },
      animation: {
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
