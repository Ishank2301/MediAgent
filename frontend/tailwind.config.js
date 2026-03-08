/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        forest: { DEFAULT:'#2d4a3e', mid:'#3d6455', light:'#5a8a78' },
        sage:   { DEFAULT:'#8cb8a8', light:'#d4ede6' },
        cream:  { DEFAULT:'#f8f6f1', warm:'#fdfcfa' },
      },
      fontFamily: {
        display: ['Syne', 'sans-serif'],
        body:    ['Instrument Sans', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

