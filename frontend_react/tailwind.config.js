/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f4fbf8",
          100: "#dff3ea",
          500: "#0f9f6e",
          600: "#0b825a",
          900: "#0b2a21"
        },
        primary: {
          50: "#eef2ff",
          100: "#e0e7ff",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca"
        },
        secondary: {
          50: "#f0fdf4",
          100: "#dcfce7",
          500: "#22c55e",
          600: "#16a34a",
          700: "#15803d"
        }
      },
      boxShadow: {
        glow: "0 20px 60px rgba(15,159,110,0.25)",
        soft: "0 10px 25px rgba(0,0,0,0.05)",
        card: "0 4px 12px rgba(0,0,0,0.08)",
        elevation: "0 12px 32px rgba(0,0,0,0.1)"
      },
      keyframes: {
        floatIn: {
          "0%": { opacity: 0, transform: "translateY(8px)" },
          "100%": { opacity: 1, transform: "translateY(0)" }
        },
        slideUp: {
          "0%": { opacity: 0, transform: "translateY(16px)" },
          "100%": { opacity: 1, transform: "translateY(0)" }
        },
        fadeIn: {
          "0%": { opacity: 0 },
          "100%": { opacity: 1 }
        }
      },
      animation: {
        floatIn: "floatIn 500ms ease-out both",
        slideUp: "slideUp 400ms ease-out both",
        fadeIn: "fadeIn 300ms ease-out both"
      }
    }
  },
  plugins: []
};
