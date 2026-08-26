import type { QueryClient } from '@tanstack/react-query'
import { configureApiClient } from '@web-app/api-client'

import { currentUserQueryOptions } from '@/features/auth/auth-api'

type SessionQueryClient = Pick<QueryClient, 'cancelQueries' | 'clear' | 'fetchQuery'>

type SessionRouter = Readonly<{
  navigate: (
    options: Readonly<{
      to: '/login'
      search: Readonly<{ flow: undefined; return_to: string }>
    }>,
  ) => Promise<unknown>
  state: Readonly<{
    location: Readonly<{ pathname: string }>
    matches: readonly Readonly<{ routeId: string }>[]
  }>
}>

type BrowserWindow = Pick<Window, 'addEventListener' | 'location' | 'removeEventListener'>

type SessionLifecycleDependencies = Readonly<{
  apiBaseUrl?: string
  queryClient: SessionQueryClient
  router: SessionRouter
  window: BrowserWindow
}>

/**
 * Installs the application-wide session lifecycle: response handling and foreground validation.
 * Returns a cleanup function for tests and application teardown.
 */
export function installSessionLifecycle({
  apiBaseUrl,
  queryClient,
  router,
  window,
}: SessionLifecycleDependencies) {
  let redirectStarted = false

  const redirectToLogin = async () => {
    if (redirectStarted || router.state.location.pathname === '/login') {
      return
    }

    redirectStarted = true
    await queryClient.cancelQueries()
    queryClient.clear()

    const { hash, pathname, search } = window.location
    await router.navigate({
      to: '/login',
      search: { flow: undefined, return_to: `${pathname}${search}${hash}` },
    })
  }

  const validateSession = () => {
    const isProtectedRoute = router.state.matches.some((match) => match.routeId === '/_layout')
    if (!isProtectedRoute) {
      return
    }

    void queryClient.fetchQuery({ ...currentUserQueryOptions, staleTime: 0 }).catch(() => undefined)
  }

  configureApiClient({ baseUrl: apiBaseUrl, onUnauthorized: redirectToLogin })
  window.addEventListener('focus', validateSession)

  return () => {
    configureApiClient()
    window.removeEventListener('focus', validateSession)
  }
}
