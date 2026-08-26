import { queryOptions } from '@tanstack/react-query'
import { authMe, type Role, type UserResponse } from '@web-app/api-client'

export type AuthenticatedUser = Readonly<{
  id: string
  name: string
  role: Role
  login: string | null
}>

export class RequestError extends Error {
  readonly status: number

  constructor(status: number) {
    super('Не удалось получить данные.')
    this.name = 'RequestError'
    this.status = status
  }
}

export const currentUserQueryKey = ['auth', 'current-user'] as const

export const currentUserQueryOptions = queryOptions({
  queryKey: currentUserQueryKey,
  queryFn: loadCurrentUser,
  staleTime: 5 * 60 * 1000,
  retry: false,
})

export async function loadCurrentUser(): Promise<AuthenticatedUser> {
  const result = await authMe()
  const payload = requireData(result.data, result.response?.status)
  return toAuthenticatedUser(payload)
}

function requireData<T>(data: T | undefined, status: number | undefined): T {
  if (data === undefined) {
    throw new RequestError(status ?? 0)
  }
  return data
}

function toAuthenticatedUser(user: UserResponse): AuthenticatedUser {
  return {
    id: user.id,
    name: user.name,
    role: user.role,
    login: user.login,
  }
}
