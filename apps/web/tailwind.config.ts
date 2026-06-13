import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Bright blood-orange brand palette (primary ~ rgb(245 76 32)).
        brand: {
          50: "#fff3ef",
          100: "#ffe4db",
          200: "#ffc7b6",
          300: "#fda286",
          400: "#fb7650",
          500: "#f95a2e",
          600: "#f54c20", // primary
          700: "#d33c14",
          800: "#a83014",
          900: "#882a16",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
