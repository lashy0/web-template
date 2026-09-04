import {
  auditListAuditEvents,
  usersCreateUser,
  usersDeleteUser,
  usersListUsers,
  usersUpdateActive,
  usersUpdateArchived,
  usersUpdatePassword,
  usersUpdateUser,
  zAuthState,
  zRole,
  type CreateUserRequest,
  type Role as ApiRole,
  type UpdateUserRequest,
  type UserResponse,
} from '@web-app/api-client'

export type Role = ApiRole
export type AuthState = UserResponse['auth_state']
export type SortOrder = 'asc' | 'desc'
export type UserSort = 'archived_at' | 'login' | 'name'
export type AuditSort = 'actor_display_name' | 'created_at'

export const userRoles = zRole.options satisfies readonly Role[]
export const authStates = zAuthState.options satisfies readonly AuthState[]

export const roleLabels: Readonly<Record<Role, string>> = {
  administrator: 'Администратор',
  manager: 'Менеджер',
  engineer: 'Инженер',
  packer: 'Упаковщик',
  operator: 'Оператор',
}

export const roleOptions: readonly Readonly<{ label: string; value: Role }>[] = userRoles.map((value) => ({
  label: roleLabels[value],
  value,
}))

export const roleFilterOptions: readonly Readonly<{ label: string; value: Role | 'all' }>[] = [
  { label: 'Все роли', value: 'all' },
  ...roleOptions,
]

export const authStateLabels: Readonly<Record<AuthState, string>> = {
  active: 'Активен',
  inactive: 'Неактивен',
}

export const authStateFilterOptions: readonly Readonly<{
  label: string
  value: AuthState | 'all'
}>[] = [
  { label: 'Все статусы', value: 'all' },
  ...authStates.map((value) => ({ label: authStateLabels[value], value })),
]

export type User = Readonly<{
  id: string
  name: string
  role: Role
  login: string | null
  authState: AuthState
  archivedAt: string | null
}>

export type CreateUserInput = CreateUserRequest
export type UpdateUserInput = UpdateUserRequest

export type AuditEvent = Readonly<{
  id: string
  createdAt: string
  actorType: string
  actorId: string | null
  actorDisplayName: string | null
  actorIdentifier: string | null
  action: string
  entityType: string
  entityId: string | null
  entityDisplayName: string | null
  entityIdentifier: string | null
  oldData: Record<string, unknown> | null
  newData: Record<string, unknown> | null
}>

export type Pagination = Readonly<{
  page: number
  pageSize: number
}>

export type PaginatedResult<Item> = Readonly<{
  items: Item[]
  page: number
  pageSize: number
  total: number
}>

export type UserFilters = Readonly<{
  query?: string
  role?: Role
  authState?: AuthState
}>

export class RequestError extends Error {
  readonly code: string | undefined
  readonly status: number

  constructor(status: number, code?: string) {
    super('Не удалось получить данные.')
    this.code = code
    this.name = 'RequestError'
    this.status = status
  }
}

export function isLoginAlreadyExistsError(error: unknown): boolean {
  return error instanceof RequestError && error.code === 'login_already_exists'
}

export async function listUsers({
  archived = false,
  authState,
  order = 'asc',
  page,
  pageSize,
  query,
  role,
  sort = 'name',
}: Pagination &
  UserFilters &
  Readonly<{ archived?: boolean; order?: SortOrder; sort?: UserSort }>): Promise<
  PaginatedResult<User>
> {
  const result = await usersListUsers({
    query: {
      archived,
      auth_state: authState,
      order,
      page,
      page_size: pageSize,
      q: query || undefined,
      role,
      sort,
    },
  })
  const payload = requireData(result.data, result.response?.status, result.error)
  return {
    items: payload.items.map(toUser),
    page: payload.page,
    pageSize: payload.page_size,
    total: payload.total,
  }
}

export async function createUser(input: CreateUserInput): Promise<User> {
  const result = await usersCreateUser({ body: input })
  return toUser(requireData(result.data, result.response?.status, result.error))
}

export async function updateUser(userId: string, input: UpdateUserInput): Promise<User> {
  const result = await usersUpdateUser({ body: input, path: { user_id: userId } })
  return toUser(requireData(result.data, result.response?.status, result.error))
}

export async function updateUserPassword(userId: string, password: string): Promise<void> {
  const result = await usersUpdatePassword({ body: { password }, path: { user_id: userId } })

  if (result.error !== undefined) {
    throw new RequestError(result.response?.status ?? 0, errorCode(result.error))
  }
}

export async function updateUserActive(userId: string, active: boolean): Promise<User> {
  const result = await usersUpdateActive({ body: { active }, path: { user_id: userId } })
  return toUser(requireData(result.data, result.response?.status, result.error))
}

export async function updateUserArchived(userId: string, archived: boolean): Promise<User> {
  const result = await usersUpdateArchived({ body: { archived }, path: { user_id: userId } })
  return toUser(requireData(result.data, result.response?.status, result.error))
}

export async function deleteUser(userId: string): Promise<void> {
  const result = await usersDeleteUser({ path: { user_id: userId } })
  if (result.error !== undefined) {
    throw new RequestError(result.response?.status ?? 0, errorCode(result.error))
  }
}

export async function listUserAudit({
  createdFrom,
  createdTo,
  order = 'desc',
  page,
  pageSize,
  sort = 'created_at',
}: Pagination &
  Readonly<{
    createdFrom?: string
    createdTo?: string
    order?: SortOrder
    sort?: AuditSort
  }>): Promise<PaginatedResult<AuditEvent>> {
  const result = await auditListAuditEvents({
    query: {
      created_from: createdFrom,
      created_to: createdTo,
      entity_type: ['user'],
      order,
      page,
      page_size: pageSize,
      sort,
    },
  })
  const payload = requireData(result.data, result.response?.status, result.error)
  return {
    items: payload.items.map((event) => ({
      id: event.id,
      createdAt: event.created_at,
      actorType: event.actor_type,
      actorId: event.actor_id,
      actorDisplayName: event.actor_display_name,
      actorIdentifier: event.actor_identifier,
      action: event.action,
      entityType: event.entity_type,
      entityId: event.entity_id,
      entityDisplayName: event.entity_display_name,
      entityIdentifier: event.entity_identifier,
      oldData: event.old_data,
      newData: event.new_data,
    })),
    page: payload.page,
    pageSize: payload.page_size,
    total: payload.total,
  }
}

function requireData<T>(data: T | undefined, status: number | undefined, error: unknown): T {
  if (data === undefined) {
    throw new RequestError(status ?? 0, errorCode(error))
  }
  return data
}

function errorCode(error: unknown): string | undefined {
  if (typeof error !== 'object' || error === null || !('code' in error)) {
    return undefined
  }
  return typeof error.code === 'string' ? error.code : undefined
}

function toUser(user: UserResponse): User {
  return {
    id: user.id,
    name: user.name,
    role: user.role,
    login: user.login,
    authState: user.auth_state,
    archivedAt: user.archived_at,
  }
}
