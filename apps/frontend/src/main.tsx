import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@web-app/ui/styles.css'

import { App } from '@/app/app'
import { queryClient } from '@/app/query-client'
import { router } from '@/app/router'
import { installSessionLifecycle } from '@/app/session-lifecycle'

installSessionLifecycle({ queryClient, router, window })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
