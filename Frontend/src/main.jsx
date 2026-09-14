import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

import { getSavedTheme, applyTheme } from './services/useFinnyTheme'

// Initialize visual theme from persistence
applyTheme(getSavedTheme());

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
