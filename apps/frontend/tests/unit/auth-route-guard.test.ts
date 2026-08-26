import { QueryClient } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { currentUserQueryKey, type AuthenticatedUser } from '@/features/auth/auth-api'
import { Route } from '@/routes/_layout'

const currentUser: AuthenticatedUser = {
  id: 'user-id',
  name: 'Администратор',
  login: 'admin',
  role: 'administrator',
}

describe('protected route guard', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('reuses the fresh current-user query instead of requesting auth/me again', async () => {
    const queryClient = new QueryClient()
    queryClient.setQueryData(currentUserQueryKey, currentUser)
    const fetchMock = vi.fn<typeof fetch>()
    vi.stubGlobal('fetch', fetchMock)

    const beforeLoad = Route.options.beforeLoad

    await expect(beforeLoad?.({ context: { queryClient } } as never)).resolves.toEqual({
      currentUser,
    })
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
