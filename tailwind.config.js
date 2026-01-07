/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'jet-black': '#000000',
        'jet-white': '#FFFFFF',
        'jet-red': '#F05545', // The coral/red color from the logo
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
} 