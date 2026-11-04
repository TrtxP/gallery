import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] })
  ],
  build: {
    // three.js + R3F + drei are ~1.2 MB minified (~350 kB gzip); expected for a 3D page
    chunkSizeWarningLimit: 1500,
  },
})
