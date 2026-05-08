import type { Config } from 'tailwindcss';
import tailwindcssAnimate from 'tailwindcss-animate';

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
    './content/**/*.{md,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: 'var(--bg)',
          soft: 'var(--bg-soft)',
          deep: 'var(--bg-deep)',
        },
        ink: {
          DEFAULT: 'var(--ink)',
          soft: 'var(--ink-soft)',
          mute: 'var(--ink-mute)',
        },
        olive: {
          DEFAULT: 'var(--olive)',
          soft: 'var(--olive-soft)',
          deep: 'var(--olive-deep)',
        },
        rule: 'var(--rule)',
        accent: 'var(--accent)',
      },
      fontFamily: {
        display: ['var(--font-display)', 'Georgia', 'serif'],
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        // Editorial scale
        'micro': ['0.6875rem', { lineHeight: '1', letterSpacing: '0.08em' }],
        'eyebrow': ['0.75rem', { lineHeight: '1.2', letterSpacing: '0.16em' }],
      },
      letterSpacing: {
        'tightest': '-0.04em',
        'editorial': '-0.025em',
      },
      maxWidth: {
        'reading': '62ch',
        'editorial': '1320px',
      },
      animation: {
        'fade-up': 'fade-up 0.8s cubic-bezier(0.16, 1, 0.3, 1) both',
        'rule-draw': 'rule-draw 1.2s cubic-bezier(0.65, 0, 0.35, 1) both',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'rule-draw': {
          '0%': { transform: 'scaleX(0)', transformOrigin: 'left' },
          '100%': { transform: 'scaleX(1)', transformOrigin: 'left' },
        },
      },
    },
  },
  plugins: [tailwindcssAnimate],
};

export default config;
