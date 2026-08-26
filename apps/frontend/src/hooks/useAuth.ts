import { useQuery, useQueryClient } from '@tanstack/react-query'

import { currentUserQueryKey, currentUserQueryOptions } from '@/features/auth/auth-api'
import { createBrowserLogoutUrl } from '@/features/auth/logout-flow'

/**
 * Provides the current Kratos session user and ends the browser session.
 *
 * Authentication is backed by an HttpOnly Kratos cookie, so no access token
 * is stored in browser storage.
 */
export function useAuth() {
  const queryClient = useQueryClient()
  const userQuery = useQuery(currentUserQueryOptions)

  const logout = async () => {
    const logoutUrl = await createBrowserLogoutUrl()
    queryClient.removeQueries({ queryKey: currentUserQueryKey })
    window.location.assign(logoutUrl)
  }

  return {
    user: userQuery.data,
    isAuthenticated: userQuery.data !== undefined,
    isLoading: userQuery.isPending,
    error: userQuery.error,
    logout,
  }
}

export default useAuth
