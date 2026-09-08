import {
  kgCreateKgVersion,
  kgDeleteKgVersion,
  kgListKgVersions,
  kgUpdateKgVersion,
  kgUpdateKgVersionArchived,
  type CreateKgVersionRequest,
  type KgVersionResponse,
  type UpdateKgVersionRequest,
} from '@web-app/api-client'

export type KgVersion = Readonly<{
  archivedAt: string | null
  batchCount: number
  code: string
  createdAt: string
  description: string | null
  id: string
  name: string
  updatedAt: string
}>

export type KgVersionSort = 'archived_at' | 'code' | 'name'

export type PaginatedKgVersions = Readonly<{
  items: KgVersion[]
  page: number
  pageSize: number
  total: number
}>

export type CreateKgVersionInput = CreateKgVersionRequest
export type UpdateKgVersionInput = UpdateKgVersionRequest

export class KgVersionRequestError extends Error {
  readonly code: string | undefined

  constructor(code?: string) {
    super('Не удалось получить данные.')
    this.code = code
    this.name = 'KgVersionRequestError'
  }
}

export function kgVersionErrorCode(error: unknown): string | undefined {
  return error instanceof KgVersionRequestError ? error.code : undefined
}

export function kgVersionErrorMessage(error: unknown): string | undefined {
  const messages: Record<string, string> = {
    kg_version_conflict: 'Версия КГ с таким кодом уже существует.',
    kg_version_in_use:
      'Невозможно удалить версию КГ: она используется в одной или нескольких партиях.',
    kg_version_not_found: 'Версия КГ не найдена.',
  }
  const code = kgVersionErrorCode(error)
  return code ? messages[code] : undefined
}

export async function listKgVersions(
  params: Readonly<{
    archived: boolean
    order: 'asc' | 'desc'
    page: number
    pageSize: number
    query?: string
    sort: KgVersionSort
  }>,
): Promise<PaginatedKgVersions> {
  const result = await kgListKgVersions({
    query: {
      archived: params.archived,
      page: params.page,
      page_size: params.pageSize,
      q: params.query || undefined,
      sort_by: params.sort,
      sort_order: params.order,
    },
  })
  const payload = requireData(result.data, result.error)
  return {
    items: payload.items.map(toKgVersion),
    page: payload.page,
    pageSize: payload.page_size,
    total: payload.total,
  }
}

export async function createKgVersion(input: CreateKgVersionInput): Promise<KgVersion> {
  const result = await kgCreateKgVersion({ body: input })
  return toKgVersion(requireData(result.data, result.error))
}

export async function updateKgVersion(
  versionId: string,
  input: UpdateKgVersionInput,
): Promise<KgVersion> {
  const result = await kgUpdateKgVersion({ body: input, path: { version_id: versionId } })
  return toKgVersion(requireData(result.data, result.error))
}

export async function updateKgVersionArchived(
  versionId: string,
  archived: boolean,
): Promise<KgVersion> {
  const result = await kgUpdateKgVersionArchived({
    body: { archived },
    path: { version_id: versionId },
  })
  return toKgVersion(requireData(result.data, result.error))
}

export async function deleteKgVersion(versionId: string): Promise<void> {
  const result = await kgDeleteKgVersion({ path: { version_id: versionId } })
  if (result.error !== undefined) throw new KgVersionRequestError(errorCode(result.error))
}

function requireData<T>(data: T | undefined, error: unknown): T {
  if (data === undefined) throw new KgVersionRequestError(errorCode(error))
  return data
}

function errorCode(error: unknown): string | undefined {
  if (typeof error !== 'object' || error === null || !('code' in error)) return undefined
  return typeof error.code === 'string' ? error.code : undefined
}

function toKgVersion(version: KgVersionResponse): KgVersion {
  return {
    archivedAt: version.archived_at,
    batchCount: version.batch_count,
    code: version.code,
    createdAt: version.created_at,
    description: version.description,
    id: version.id,
    name: version.name,
    updatedAt: version.updated_at,
  }
}
