import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

/*
================================================================================
FILE SUMMARY: frontend/src/main.tsx
================================================================================
WHAT THIS FILE CONTAINS AND DOES:
This file is the client-side JavaScript/TypeScript bootstrapping entry point.
It locates the HTML container element with ID 'root' in 'frontend/index.html',
initializes a React 19 concurrent root via 'createRoot', and renders the top-level
'App' component wrapped in 'StrictMode' for highlighting potential problems.

HOW IT CONNECTS TO OTHER FILES:
- Injected by Vite into 'frontend/index.html' via '<script type="module" src="/src/main.tsx">'.
- Imports and renders the primary application UI component from 'frontend/src/App.tsx'.
- Loads global application styling, resets, and CSS custom variables from 'frontend/src/index.css'.
================================================================================
*/
