import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        /* Brand coral — signature color, used for primary actions */
        primary: {
          DEFAULT: "#FF5A36",
          focus: "#E03D1A",
          active: "#cc3a1a",
        },
        /* Airtable-inspired ink system */
        ink: {
          DEFAULT: "#181d26",
          "muted-80": "#333840",
          "muted-48": "#41454d",
          "border-strong": "#9297a0",
        },
        /* Surfaces */
        canvas: "#ffffff",
        pearl: "#ffffff",
        /* Signature surfaces (Airtable) */
        surface: {
          soft: "#f8fafc",
          strong: "#e0e2e6",
          dark: "#181d26",
          "dark-elevated": "#1d1f25",
        },
        signature: {
          coral: "#FF5A36",
          cream: "#f5e9d4",
          forest: "#0a2e0e",
          peach: "#fcab79",
          mint: "#a8d8c4",
          yellow: "#f4d35e",
          mustard: "#d9a441",
        },
        hairline: "#dddddd",
        /* Semantic */
        success: "#006400",
        "success-border": "#39bf45",
        warning: "#F59E0B",
        danger: "#EF4444",
        link: "#1b61c9",
        "link-active": "#1a3866",
        info: "#254fad",
        "info-border": "#458fff",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        display: ["Outfit", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xs: "2px",
        sm: "6px",
        md: "10px",
        lg: "12px",
        pill: "9999px",
      },
      spacing: {
        section: "96px",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
