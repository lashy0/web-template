import {
  auditListAuditEvents,
  kgCreateDevEuiPrefix,
  kgDeleteDevEuiPrefix,
  kgListDevEuiPrefixes,
  kgUpdateDevEuiPrefix,
  kgUpdateDevEuiPrefixArchived,
  type CreateKgDevEuiPrefixRequest,
  type KgDevEuiPrefixResponse,
  type UpdateKgDevEuiPrefixRequest,
} from '@web-app/api-client'

export type KgPrefix = Readonly<{
  archivedAt: string | null
  createdAt: string
  name: string | null
  prefix: string
  shortCode: string
}>
export type KgPrefixSort = 'archived_at' | 'created_at' | 'name' | 'prefix' | 'short_code'
export type KgPrefixAuditSort = 'actor_display_name' | 'created_at'
export type KgPrefixAuditEvent = Readonly<{
  action: string
  actorDisplayName: string | null
  actorIdentifier: string | null
  actorType: string
  createdAt: string
  entityDisplayName: string | null
  entityIdentifier: string | null
  id: string
  newData: Record<string, unknown> | null
  oldData: Record<string, unknown> | null
}>
export type PaginatedKgPrefixes = Readonly<{
  items: KgPrefix[]
  page: number
  pageSize: number
  total: number
}>
export type PaginatedKgPrefixAudit = Readonly<{
  items: KgPrefixAuditEvent[]
  page: number
  pageSize: number
  total: number
}>

export type CreateKgPrefixInput = CreateKgDevEuiPrefixRequest
export type UpdateKgPrefixInput = UpdateKgDevEuiPrefixRequest

export class KgPrefixRequestError extends Error {
  readonly code: string | undefined

  constructor(code?: string) {
    super('Не удалось получить данные.')
    this.code = code
    this.name = 'KgPrefixRequestError'
  }
}

export function kgPrefixErrorCode(error: unknown): string | undefined {
  return error instanceof KgPrefixRequestError ? error.code : undefined
}

export function kgPrefixErrorMessage(error: unknown): string | undefined {
  const messages: Record<string, string> = {
    kg_dev_eui_prefix_conflict: 'Префикс или короткий код уже существует.',
    kg_dev_eui_prefix_in_use: 'Префикс используется партией и не может быть удалён.',
    kg_dev_eui_prefix_not_found: 'Префикс не найден.',
  }
  const code = kgPrefixErrorCode(error)
  return code ? messages[code] : undefined
}

export async function listKgPrefixes(
  params: Readonly<{
    archived: boolean
    page: number
    pageSize: number
    query?: string
    sort: KgPrefixSort
    order: 'asc' | 'desc'
  }>,
): Promise<PaginatedKgPrefixes> {
  const result = await kgListDevEuiPrefixes({
    query: {
      archived: params.archived,
      order: params.order,
      page: params.page,
      page_size: params.pageSize,
      q: params.query || undefined,
      sort: params.sort,
    },
  })
  const payload = requireData(result.data, result.error)
  return {
    items: payload.items.map(toKgPrefix),
    page: payload.page,
    pageSize: payload.page_size,
    total: payload.total,
  }
}

export async function updateKgPrefixArchived(prefix: string, archived: boolean): Promise<KgPrefix> {
  const result = await kgUpdateDevEuiPrefixArchived({ body: { archived }, path: { prefix } })
  return toKgPrefix(requireData(result.data, result.error))
}

export async function listKgPrefixAudit(
  params: Readonly<{
    createdFrom?: string
    createdTo?: string
    order: 'asc' | 'desc'
    page: number
    pageSize: number
    sort: KgPrefixAuditSort
  }>,
): Promise<PaginatedKgPrefixAudit> {
  const result = await auditListAuditEvents({
    query: {
      created_from: params.createdFrom,
      created_to: params.createdTo,
      entity_type: ['kg_dev_eui_prefix'],
      order: params.order,
      page: params.page,
      page_size: params.pageSize,
      sort: params.sort,
    },
  })
  const payload = requireData(result.data, result.error)
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

export async function createKgPrefix(input: CreateKgPrefixInput): Promise<KgPrefix> {
  const result = await kgCreateDevEuiPrefix({ body: input })
  return toKgPrefix(requireData(result.data, result.error))
}

export async function updateKgPrefix(
  prefix: string,
  input: UpdateKgPrefixInput,
): Promise<KgPrefix> {
  const result = await kgUpdateDevEuiPrefix({ body: input, path: { prefix } })
  return toKgPrefix(requireData(result.data, result.error))
}

export async function deleteKgPrefix(prefix: string): Promise<void> {
  const result = await kgDeleteDevEuiPrefix({ path: { prefix } })
  if (result.error !== undefined) throw new KgPrefixRequestError(errorCode(result.error))
}

function requireData<T>(data: T | undefined, error: unknown): T {
  if (data === undefined) throw new KgPrefixRequestError(errorCode(error))
  return data
}

function errorCode(error: unknown): string | undefined {
  if (typeof error !== 'object' || error === null || !('code' in error)) return undefined
  return typeof error.code === 'string' ? error.code : undefined
}

function toKgPrefix(prefix: KgDevEuiPrefixResponse): KgPrefix {
  return {
    archivedAt: prefix.archived_at,
    createdAt: prefix.created_at,
    name: prefix.name,
    prefix: prefix.prefix,
    shortCode: prefix.short_code,
  }
}
