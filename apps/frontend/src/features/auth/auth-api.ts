import { getProfileOptions, getProfileQueryKey, isApiError, type User } from '@web-app/api-client'

export type AuthenticatedUser = User

export const currentUserQueryKey = getProfileQueryKey()

export const currentUserQueryOptions = {
  ...getProfileOptions(),
  staleTime: 5 * 60 * 1000,
  retry: false,
}

export function isUnauthorizedError(error: unknown): boolean {
  return isApiError(error) && error.status_code === 401
}
