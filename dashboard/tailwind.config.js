/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: { colors: { brand: { 50: '#eef4ff', 500: '#3b5bdb', 700: '#2741a6', 900: '#14216b' } } },
  },
  plugins: [],
};
