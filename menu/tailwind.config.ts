import type { Config } from "tailwindcss";
import path from "node:path";
import fs from "node:fs";

const presetCandidates = [
  path.resolve(process.cwd(), "../design-system/tailwind.preset.cjs"),
  path.resolve(process.cwd(), "design-system/tailwind.preset.cjs"),
];

const presetPath = presetCandidates.find((candidate) => fs.existsSync(candidate));

const config: Config = {
  darkMode: ["class"],
  presets: presetPath ? [require(presetPath)] : [],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
