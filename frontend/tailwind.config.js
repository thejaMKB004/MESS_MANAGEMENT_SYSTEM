/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1B2A2A",
        forest: "#2F5D50",
        forestdark: "#22453B",
        clay: "#C97A3B",
        sand: "#F6F1E7",
        sandline: "#E4DCC9",
        leaf: "#7FA98A",
      },
      fontFamily: {
        display: ["'Fraunces'", "serif"],
        body: ["'Inter'", "sans-serif"],
      },
    },
  },
  plugins: [],
}
