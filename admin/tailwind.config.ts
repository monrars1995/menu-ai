import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Outfit", "sans-serif"],
      },
      colors: {
        primary: "#FF5A36",
        "primary-focus": "#FF2A00",
        ink: "#0A192F",
        "ink-muted": "#8892B0",
        canvas: "#FCFCFD",
        pearl: "#FCFCFD",
        hairline: "rgba(10, 25, 47, 0.08)",
      },
    },
  },
  plugins: [],
};
export default config;
