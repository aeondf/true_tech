/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        mts: {
          red:    '#ED1C24',
          blue:   '#0066FF',
          teal:   '#00D4AA',
          purple: '#7B3FF2',
          dark:   '#0F0F0F',
          dark2:  '#1A1A1A',
          dark3:  '#2D2D2D',
          border: '#404040',
          muted:  '#B0B0B0',
        },
      },
      fontFamily: {
        sans: ['MTS Sans', 'Manrope', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: { mts: '10px' },
      animation: {
        'pulse-red': 'pulseRed 2s ease-in-out infinite',
        'slide-up':  'slideUp 0.3s ease-out',
        'fade-in':   'fadeIn 0.2s ease-out',
        'wave':      'wave 1.5s ease-in-out infinite',
      },
      keyframes: {
        pulseRed: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(237,28,36,0.4)' },
          '50%':      { boxShadow: '0 0 0 12px rgba(237,28,36,0)' },
        },
        slideUp: {
          from: { transform: 'translateY(12px)', opacity: '0' },
          to:   { transform: 'translateY(0)',    opacity: '1' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        wave: {
          '0%, 100%': { transform: 'scaleY(0.4)' },
          '50%':      { transform: 'scaleY(1.0)' },
        },
      },
    },
  },
  plugins: [],
}
