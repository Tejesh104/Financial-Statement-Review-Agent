/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#050811',
          900: '#070B14',
          850: '#0B1120',
          800: '#0F172A',
          750: '#15203B',
          700: '#1E293B',
          600: '#334155',
        },
        cyan: {
          400: '#00E5FF',
          500: '#00C4DF',
        },
        fintech: {
          green: '#10B981',
          yellow: '#F59E0B',
          red: '#EF4444',
          cyan: '#00E5FF',
          blue: '#3B82F6',
          purple: '#8B5CF6',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      },
      boxShadow: {
        'glow-cyan': '0 0 25px -5px rgba(0, 229, 255, 0.25)',
        'glow-purple': '0 0 25px -5px rgba(139, 92, 246, 0.25)',
        'glow-green': '0 0 25px -5px rgba(16, 185, 129, 0.25)',
        'glow-red': '0 0 25px -5px rgba(239, 68, 68, 0.25)',
      },
      animation: {
        'scan': 'scan 3s ease-in-out infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        scan: {
          '0%, 100%': { transform: 'translateY(0%)' },
          '50%': { transform: 'translateY(100%)' },
        }
      }
    },
  },
  plugins: [],
}
