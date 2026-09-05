import type { Config } from "tailwindcss";

/**
 * Tailwind is extended with `brand-` prefixed token aliases so that every
 * class (e.g. `bg-brand-bg`, `text-brand-safe`) resolves to a CSS custom
 * property defined in styles/tokens.css. This way the dark/light mode swap
 * works purely via the `.light` class on <html> with zero JS colour logic.
 */
const config: Config = {
  darkMode: ["class", ".light"], // .light enables the light-mode token swap
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Legacy aliases (kept for any remaining raw Tailwind usage)
        background: "var(--color-bg)",
        foreground: "var(--color-text-primary)",

        // Brand token aliases
        brand: {
          bg:           "var(--color-bg)",
          elevated:     "var(--color-bg-elevated)",
          hover:        "var(--color-bg-hover)",
          border:       "var(--color-border)",
          "border-sub": "var(--color-border-subtle)",
          primary:      "var(--color-text-primary)",
          secondary:    "var(--color-text-secondary)",
          tertiary:     "var(--color-text-tertiary)",
          safe:         "var(--color-safe)",
          watch:        "var(--color-watch)",
          high:         "var(--color-high)",
          breach:       "var(--color-breach)",
          accent:       "var(--color-accent)",
          "accent-h":   "var(--color-accent-hover)",
          "accent-m":   "var(--color-accent-muted)",
          "safe-m":     "var(--color-safe-muted)",
          "watch-m":    "var(--color-watch-muted)",
          "high-m":     "var(--color-high-muted)",
          "breach-m":   "var(--color-breach-muted)",
        },
      },
      fontFamily: {
        ui:   ["var(--font-ui)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        DEFAULT: "var(--radius-lg)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      transitionDuration: {
        fast:   "150",
        normal: "300",
      },
      transitionTimingFunction: {
        "ease-out-expo": "cubic-bezier(0.16, 1, 0.3, 1)",
      },
      keyframes: {
        "flash-green": {
          "0%":   { backgroundColor: "transparent" },
          "20%":  { backgroundColor: "rgba(47, 169, 107, 0.20)" },
          "100%": { backgroundColor: "transparent" },
        },
        "flash-red": {
          "0%":   { backgroundColor: "transparent" },
          "20%":  { backgroundColor: "rgba(217, 72, 61, 0.20)" },
          "100%": { backgroundColor: "transparent" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "toast-in": {
          from: { transform: "translateY(16px) scale(0.97)", opacity: "0" },
          to:   { transform: "translateY(0) scale(1)",       opacity: "1" },
        },
        "slide-in-right": {
          from: { transform: "translateX(100%)", opacity: "0" },
          to:   { transform: "translateX(0)",    opacity: "1" },
        },
      },
      animation: {
        "flash-green":     "flash-green 150ms ease-out",
        "flash-red":       "flash-red 150ms ease-out",
        shimmer:           "shimmer 1.6s ease-in-out infinite",
        "toast-in":        "toast-in 200ms cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-in-right":  "slide-in-right 250ms cubic-bezier(0.16, 1, 0.3, 1)",
      },
    },
  },
  plugins: [],
};
export default config;
