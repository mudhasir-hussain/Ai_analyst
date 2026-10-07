import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
})

/*
================================================================================
FILE SUMMARY: frontend/vite.config.ts
================================================================================
WHAT THIS FILE CONTAINS AND DOES:
This file defines the build, development server, and plugin configuration for Vite:
  - Registers '@vitejs/plugin-react' to enable Fast Refresh and JSX/TSX compilation.
  - Serves as the configuration foundation when running 'npm run dev' or 'npm run build'.

HOW IT CONNECTS TO OTHER FILES:
- Used by Vite CLI when compiling and bundling the React application in 'frontend/'.
- Integrates React transforms into all '.tsx' files under 'frontend/src/'.
================================================================================
*/
