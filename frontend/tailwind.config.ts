import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

/** Maps a theme.css HSL token to a Tailwind color that supports `/opacity`. */
const token = (name: string): string => `hsl(var(--${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: token("background"),
        foreground: token("foreground"),
        border: token("border"),
        input: token("input"),
        ring: token("ring"),
        card: { DEFAULT: token("card"), foreground: token("card-foreground") },
        popover: { DEFAULT: token("popover"), foreground: token("popover-foreground") },
        primary: { DEFAULT: token("primary"), foreground: token("primary-foreground") },
        secondary: { DEFAULT: token("secondary"), foreground: token("secondary-foreground") },
        muted: { DEFAULT: token("muted"), foreground: token("muted-foreground") },
        accent: { DEFAULT: token("accent"), foreground: token("accent-foreground") },
        success: { DEFAULT: token("success"), soft: token("success-soft") },
        warning: { DEFAULT: token("warning"), soft: token("warning-soft") },
        destructive: { DEFAULT: token("destructive"), foreground: token("destructive-foreground") },
      },
      borderRadius: {
        "2xl": "var(--radius)",
        xl: "calc(var(--radius) - 4px)",
        lg: "calc(var(--radius) - 6px)",
        md: "calc(var(--radius) - 8px)",
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        heading: ["var(--font-heading)"],
      },
      backgroundImage: {
        brand: "linear-gradient(135deg, hsl(var(--gradient-from)), hsl(var(--gradient-to)))",
      },
      boxShadow: {
        soft: "var(--shadow-soft)",
        glow: "var(--shadow-glow)",
      },
      spacing: {
        topbar: "var(--topbar-height)",
        tabbar: "var(--tabbar-height)",
      },
      maxWidth: {
        content: "var(--content-max-width)",
      },
    },
  },
  plugins: [animate],
};

export default config;
