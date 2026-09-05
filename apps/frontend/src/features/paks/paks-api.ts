import {
  auditListAuditEvents,
  pakCreatePak,
  pakDeletePak,
  pakGetAccessKey,
  pakListPak,
  pakRotateAccessKey,
  pakUpdateActive,
  pakUpdateArchived,
  pakUpdatePak,
  zPakDeviceKind,
  zPakStatus,
  type CreatePakDeviceRequest,
  type PakDeviceKind as ApiPakDeviceKind,
  type PakDeviceResponse,
  type PakStatus as ApiPakStatus,
  type UpdatePakDeviceRequest,
} from '@web-app/api-client'

export type PakKind = ApiPakDeviceKind
export type PakStatus = ApiPakStatus
export type SortOrder = 'asc' | 'desc'
export type PakSort = 'archived_at' | 'code' | 'created_at' | 'kind' | 'last_seen_at'
export type PakAuditSort = 'actor_display_name' | 'created_at'

export const pakKinds = zPakDeviceKind.options satisfies readonly PakKind[]

export const pakKindLabels: Readonly<Record<PakKind, string>> = {
  engineering: 'Инженерный',
  otk_line: 'Линия ОТК',
}

export const pakKindOptions: readonly Readonly<{ label: string; value: PakKind }>[] = pakKinds.map(
  (value) => ({ label: pakKindLabels[value], value }),
)

export const pakKindFilterOptions: readonly Readonly<{ label: string; value: PakKind | 'all' }>[] =
  [{ label: 'Все типы', value: 'all' }, ...pakKindOptions]

export const pakStatusLabels: Readonly<Record<PakStatus, string>> = {
  active: 'Активен',
  inactive: 'Неактивен',
}
export const pakStatuses = zPakStatus.options satisfies readonly PakStatus[]

export const pakStatusFilterOptions: readonly Readonly<{
  label: string
  value: PakStatus | 'all'
}>[] = [
  { label: 'Все статусы', value: 'all' },
  ...pakStatuses.map((value) => ({ label: pakStatusLabels[value], value })),
]

export type Pak = Readonly<{
  id: string
  code: string
  kind: PakKind
  oauthClientId: string
  status: PakStatus
  lastSeenAt: string | null
  archivedAt: string | null
}>

export type CreatePakInput = CreatePakDeviceRequest
export type UpdatePakInput = UpdatePakDeviceRequest

export type CreatePakResult = Readonly<{
  pak: Pak
  accessKey: string
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

export type PakFilters = Readonly<{
  kind?: PakKind
  query?: string
  status?: PakStatus
}>

export type PakAuditEvent = Readonly<{
  id: string
  createdAt: string
  actorType: string
  actorDisplayName: string | null
  actorIdentifier: string | null
  action: string
  entityDisplayName: string | null
  entityIdentifier: string | null
  oldData: Record<string, unknown> | null
  newData: Record<string, unknown> | null
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

export function isPakAlreadyExistsError(error: unknown): boolean {
  return error instanceof RequestError && error.code === 'pak_already_exists'
}

export async function listPaks({
  archived = false,
  kind,
  order = 'asc',
  page,
  pageSize,
  query,
  status,
  sort = 'code',
}: Pagination &
  PakFilters &
  Readonly<{ archived?: boolean; order?: SortOrder; sort?: PakSort }>): Promise<
  PaginatedResult<Pak>
> {
  const result = await pakListPak({
    query: {
      archived,
      kind,
      order,
      page,
      page_size: pageSize,
      q: query || undefined,
      sort,
      status,
    },
  })
  const payload = requireData(result.data, result.response?.status, result.error)

  return {
    items: payload.items.map(toPak),
    page: payload.page,
    pageSize: payload.page_size,
    total: payload.total,
  }
}

export async function createPak(input: CreatePakInput): Promise<CreatePakResult> {
  const result = await pakCreatePak({ body: input })
  const payload = requireData(result.data, result.response?.status, result.error)

  return { accessKey: payload.access_key, pak: toPak(payload.device) }
}

export async function updatePak(pakId: string, input: UpdatePakInput): Promise<Pak> {
  const result = await pakUpdatePak({ body: input, path: { pak_id: pakId } })
  return toPak(requireData(result.data, result.response?.status, result.error))
}

export async function getPakAccessKey(pakId: string): Promise<string> {
  const result = await pakGetAccessKey({ path: { pak_id: pakId } })
  return requireData(result.data, result.response?.status, result.error).access_key
}

export async function rotatePakAccessKey(pakId: string): Promise<string> {
  const result = await pakRotateAccessKey({ path: { pak_id: pakId } })
  return requireData(result.data, result.response?.status, result.error).access_key
}

export async function updatePakActive(pakId: string, active: boolean): Promise<Pak> {
  const result = await pakUpdateActive({ body: { active }, path: { pak_id: pakId } })
  return toPak(requireData(result.data, result.response?.status, result.error))
}

export async function updatePakArchived(pakId: string, archived: boolean): Promise<Pak> {
  const result = await pakUpdateArchived({ body: { archived }, path: { pak_id: pakId } })
  return toPak(requireData(result.data, result.response?.status, result.error))
}

export async function deletePak(pakId: string): Promise<void> {
  const result = await pakDeletePak({ path: { pak_id: pakId } })
  if (result.error !== undefined) {
    throw new RequestError(result.response?.status ?? 0, errorCode(result.error))
  }
}

export async function listPakAudit({
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
    sort?: PakAuditSort
  }>): Promise<PaginatedResult<PakAuditEvent>> {
  const result = await auditListAuditEvents({
    query: {
      created_from: createdFrom,
      created_to: createdTo,
      entity_type: ['pak'],
      order,
      page,
      page_size: pageSize,
      sort,
    },
  })
  const payload = requireData(result.data, result.response?.status, result.error)

  return {
    items: payload.items.map((event) => ({
      action: event.action,
      actorDisplayName: event.actor_display_name,
      actorIdentifier: event.actor_identifier,
      actorType: event.actor_type,
      createdAt: event.created_at,
      entityDisplayName: event.entity_display_name,
      entityIdentifier: event.entity_identifier,
      id: event.id,
      newData: event.new_data,
      oldData: event.old_data,
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

function toPak(pak: PakDeviceResponse): Pak {
  return {
    archivedAt: pak.archived_at,
    code: pak.code,
    id: pak.id,
    kind: pak.kind,
    lastSeenAt: pak.last_seen_at,
    oauthClientId: pak.oauth_client_id,
    status: pak.status,
  }
}
