import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { AuthGate } from './auth/AuthGate.tsx'
import { ErrorBoundary } from './components/ErrorBoundary.tsx'
import { usePipelineStore } from './pipeline/pipelineStore.ts'

// The gate wraps `App` rather than living inside it, so nothing in the pipeline mounts — and
// nothing it fetches on mount fires — until somebody is signed in. See AuthGate's docstring.
//
// The boundary wraps the gate in turn, so it catches a throw from anywhere below including the
// gate's own render. Its reset drops back to a blank chat with `discardUnsaved`, which is the one
// exit that does not re-render whatever just threw: the default path would flush the crashed
// chat's state back to the server on the way out.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary onReset={() => usePipelineStore.getState().startNewChat({ discardUnsaved: true })}>
      <AuthGate>
        <App />
      </AuthGate>
    </ErrorBoundary>
  </StrictMode>,
)
