import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  presets: [require("../design-system/tailwind.preset.cjs")],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
