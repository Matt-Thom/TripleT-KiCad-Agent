import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { BOMProvider } from './context/BOMContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BOMProvider>
      <App />
    </BOMProvider>
  </StrictMode>,
)
