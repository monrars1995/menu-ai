/** @type {import('tailwindcss').Config} */
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#181d26",
          active: "#0d1218",
          subtle: "rgba(24, 29, 38, 0.08)",
        },
        brand: {
          DEFAULT: "#ff5a36",
          active: "#e84f2e",
        },
        ink: {
          DEFAULT: "#181d26",
          "muted-80": "#333840",
          "muted-48": "#41454d",
          "border-strong": "#9297a0",
        },
        body: "#333840",
        canvas: "#ffffff",
        pearl: "#ffffff",
        hairline: "#dddddd",
        surface: {
          soft: "#f8fafc",
          strong: "#e0e2e6",
          dark: "#181d26",
          "dark-elevated": "#1d1f25",
        },
        signature: {
          coral: "#aa2d00",
          cream: "#f5e9d4",
          forest: "#0a2e0e",
          peach: "#fcab79",
          mint: "#a8d8c4",
          yellow: "#f4d35e",
          mustard: "#d9a441",
        },
        success: "#006400",
        "success-border": "#39bf45",
        warning: "#f59e0b",
        danger: "#dc2626",
        link: {
          DEFAULT: "#1b61c9",
          active: "#1a3866",
        },
        info: "#254fad",
        "info-border": "#458fff",
        pricing: {
          ink: "#1d1f25",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "-apple-system", "sans-serif"],
        display: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
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
};
