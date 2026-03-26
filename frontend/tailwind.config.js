/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'ops-black': '#030712',
        'ops-dark': '#0a0f1a',
        'ops-panel': '#111827',
        'ops-border': '#1f2937',
        'ops-muted': '#6b7280',
        'alert-red': '#dc2626',
        'alert-red-glow': '#ef4444',
        'safe-green': '#10b981',
        'warn-yellow': '#f59e0b',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-alert': 'pulse-alert 1.5s ease-in-out infinite',
        'flash-red': 'flash-red 0.5s ease-in-out 6',
        'slide-down': 'slide-down 0.3s ease-out',
        'fade-in': 'fade-in 0.5s ease-out',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'scan-line': 'scan-line 3s linear infinite',
      },
      keyframes: {
        'pulse-alert': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        'flash-red': {
          '0%, 100%': { borderColor: '#dc2626', boxShadow: '0 0 0 0 rgba(220, 38, 38, 0)' },
          '50%': { borderColor: '#ef4444', boxShadow: '0 0 20px 4px rgba(220, 38, 38, 0.4)' },
        },
        'slide-down': {
          '0%': { transform: 'translateY(-100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'glow': {
          '0%': { boxShadow: '0 0 5px rgba(220, 38, 38, 0.3)' },
          '100%': { boxShadow: '0 0 25px rgba(220, 38, 38, 0.6)' },
        },
        'scan-line': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
      },
    },
  },
  plugins: [],
}
