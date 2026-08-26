import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { AuthGate } from './auth/AuthGate.tsx'

// The gate wraps `App` rather than living inside it, so nothing in the pipeline mounts — and
// nothing it fetches on mount fires — until somebody is signed in. See AuthGate's docstring.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthGate>
      <App />
    </AuthGate>
  </StrictMode>,
)
