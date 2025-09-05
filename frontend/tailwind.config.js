/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
      "./src/**/*.{js,jsx,ts,tsx}",
      "./templates/**/*.html",           // Add this for global templates
      "./home/templates/**/*.html",      // Add this for your home app templates
      "./**/templates/**/*.html",        // Add this to catch all app templates
      "./static/js/**/*.js",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}

