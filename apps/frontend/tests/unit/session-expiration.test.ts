import { QueryClient } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { authMe, configureApiClient } from '@web-app/api-client'

import { installSessionLifecycle } from '@/app/session-lifecycle'
import { currentUserQueryKey, type AuthenticatedUser } from '@/features/auth/auth-api'

const currentUser: AuthenticatedUser = {
  id: 'user-id',
  name: 'Администратор',
  login: 'admin',
  role: 'administrator',
}

describe('session expiration', () => {
  afterEach(() => {
    configureApiClient()
    vi.unstubAllGlobals()
  })

  it('clears the cached session and redirects only once when requests receive 401', async () => {
    const queryClient = new QueryClient()
    queryClient.setQueryData(currentUserQueryKey, currentUser)
    const navigate = vi.fn<() => Promise<void>>().mockResolvedValue(undefined)
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 401 }))
    vi.stubGlobal('fetch', fetchMock)
    const browserWindow = {
      addEventListener: () => undefined,
      location: { hash: '', pathname: '/admin/user/users', search: '' },
      removeEventListener: () => undefined,
    }
    const cleanup = installSessionLifecycle({
      apiBaseUrl: 'https://api.example.test',
      queryClient,
      router: {
        navigate,
        state: {
          location: { pathname: '/admin/user/users' },
          matches: [{ routeId: '/_layout' }],
        },
      },
      window: browserWindow as never,
    })

    await Promise.all([authMe(), authMe()])

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(queryClient.getQueryData(currentUserQueryKey)).toBeUndefined()
    expect(navigate).toHaveBeenCalledOnce()
    expect(navigate).toHaveBeenCalledWith({
      to: '/login',
      search: { flow: undefined, return_to: '/admin/user/users' },
    })
    cleanup()
  })
})
