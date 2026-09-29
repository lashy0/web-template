import type { QueryClient } from '@tanstack/react-query'
import { isApiError, UserRole, type User } from '@web-app/api-client'

import { invalidateTags } from '@/lib/queries'

export type { User }
export type Role = UserRole
export type UserSort = 'archived_at' | 'name'

export const userRoles: readonly Role[] = Object.values(UserRole)

export const roleLabels: Readonly<Record<Role, string>> = {
  administrator: 'Администратор',
  manager: 'Менеджер',
  engineer: 'Инженер',
  packer: 'Упаковщик',
  operator: 'Оператор',
}

export const roleOptions: readonly Readonly<{ label: string; value: Role }>[] = userRoles.map(
  (value) => ({ label: roleLabels[value], value }),
)

export const roleFilterOptions: readonly Readonly<{ label: string; value: Role | 'all' }>[] = [
  { label: 'Все роли', value: 'all' },
  ...roleOptions,
]

export function isLoginTakenError(error: unknown): boolean {
  return isApiError(error, 'user_login_taken')
}

/** Refresh the user lists and the audit log after a user has changed. */
export function invalidateUserQueries(queryClient: QueryClient) {
  return invalidateTags(queryClient, 'User Accounts', 'Audit')
}
