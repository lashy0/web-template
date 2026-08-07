import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { configureApiClient } from '@web-app/api-client'
import '@web-app/ui/styles.css'

import { App } from '@/app/app'

configureApiClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
