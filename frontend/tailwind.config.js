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
        // Engineering console palette — mirrors CSS variables
        bg: '#0e1012',
        surface: {
          DEFAULT: '#16191c',
          raised:  '#1d2126',
          inset:   '#0b0d0f',
        },
        border: {
          DEFAULT: '#272c31',
          strong:  '#363d44',
          subtle:  '#1e2227',
        },
        ink: {
          DEFAULT: '#dde2e8',
          muted:   '#6e7a86',
          dim:     '#404850',
        },
        // Amber accent — instrument panel
        accent: {
          DEFAULT: '#d4891a',
          strong:  '#e89f2b',
          dim:     '#7a4e0e',
        },
        // Status colors — muted, solid, purposeful
        ok:   '#3a8c5e',
        warn: '#b5832b',
        fail: '#b03030',
        info: '#2e6a9e',
        // Keep legacy color names for component compatibility
        space: {
          950: '#0b0d0f',
          900: '#0e1012',
          850: '#13161a',
          800: '#16191c',
          700: '#272c31',
          600: '#363d44',
        },
        stellar: {
          cyan:    '#7cb8d4',  // muted blue-grey, not neon
          emerald: '#3a8c5e',
          amber:   '#d4891a',
          rose:    '#b03030',
          violet:  '#6d6a9a',
          blue:    '#2e6a9e',
        },
      },
      fontFamily: {
        sans:  ['"DM Sans"', 'system-ui', 'sans-serif'],
        mono:  ['"Space Mono"', 'ui-monospace', 'monospace'],
        // Legacy compatibility
        'mono-tech': ['"Space Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'xxs': ['0.6875rem', { lineHeight: '1.3' }],
      },
      borderRadius: {
        sm: '2px',
        md: '4px',
        lg: '6px',
        xl: '8px',
        '2xl': '10px',
        full: '9999px',
      },
      boxShadow: {
        // No glow shadows — architectural inset/elevation only
        'panel': '0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.4)',
        'inner-sm': 'inset 0 1px 2px rgba(0,0,0,0.4)',
      },
      animation: {
        'live': 'live-pulse 1.8s ease-in-out infinite',
        'blink': 'blink 1.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
