import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Blood-orange brand palette.
        brand: {
          50: "#fef3ee",
          100: "#fde0d2",
          200: "#fabfa4",
          300: "#f5966d",
          400: "#ee6a3c",
          500: "#e44a1f",
          600: "#cf3f1a", // primary
          700: "#ad3216",
          800: "#8a2917",
          900: "#722416",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
