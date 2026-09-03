import {
  defectsCreateDefectGroup,
  defectsCreateDefectType,
  defectsDeleteDefectGroup,
  defectsDeleteDefectType,
  defectsListDefectGroups,
  defectsListDefectTypes,
  defectsUpdateDefectGroup,
  defectsUpdateDefectGroupArchived,
  defectsUpdateDefectType,
  defectsUpdateDefectTypeArchived,
  type CreateDefectGroupRequest,
  type CreateDefectTypeRequest,
  type DefectGroupListItemResponse,
  type DefectGroupResponse,
  type DefectTypeResponse,
  type UpdateDefectGroupRequest,
  type UpdateDefectTypeRequest,
} from '@web-app/api-client'

export type SortOrder = 'asc' | 'desc'
export type DefectSort = 'archived_at' | 'code' | 'created_at' | 'name' | 'updated_at'
export type Pagination = Readonly<{ page: number; pageSize: number }>
export type PaginatedResult<Item> = Readonly<{
  items: Item[]
  page: number
  pageSize: number
  total: number
}>

export type DefectGroup = Readonly<{
  activeTypesCount: number
  archivedAt: string | null
  code: string
  description: string | null
  id: string
  name: string
  typesCount: number
}>

export type DefectType = Readonly<{
  archivedAt: string | null
  code: string
  description: string
  engineerAction: string | null
  group: Readonly<{ archivedAt: string | null; code: string; id: string; name: string }>
  groupId: string
  id: string
  name: string
  possibleCause: string | null
}>

export type CreateDefectGroupInput = CreateDefectGroupRequest
export type UpdateDefectGroupInput = UpdateDefectGroupRequest
export type CreateDefectTypeInput = CreateDefectTypeRequest
export type UpdateDefectTypeInput = UpdateDefectTypeRequest

export class DefectsRequestError extends Error {
  readonly code: string | undefined
  readonly status: number

  constructor(status: number, code?: string) {
    super('Не удалось получить данные.')
    this.code = code
    this.name = 'DefectsRequestError'
    this.status = status
  }
}

export function defectErrorMessage(error: unknown): string | undefined {
  const messages: Record<string, string> = {
    defect_group_already_exists: 'Группа с таким кодом уже существует.',
    defect_group_archived:
      'Архивированную группу нельзя использовать для создания или восстановления типов.',
    defect_group_cannot_be_deleted: 'Группа используется в других данных и не может быть удалена.',
    defect_group_has_unarchived_types: 'Сначала архивируйте все активные типы этой группы.',
    defect_type_already_exists: 'Тип с таким кодом уже существует.',
    defect_type_cannot_be_deleted: 'Тип используется в других данных и не может быть удалён.',
  }
  const code = defectErrorCode(error)
  return code ? messages[code] : undefined
}

export function defectErrorCode(error: unknown): string | undefined {
  return error instanceof DefectsRequestError ? error.code : undefined
}

export async function listDefectGroups({
  archived = false,
  order = 'asc',
  page,
  pageSize,
  query,
  sort = 'code',
}: Pagination &
  Readonly<{ archived?: boolean; order?: SortOrder; query?: string; sort?: DefectSort }>): Promise<
  PaginatedResult<DefectGroup>
> {
  const result = await defectsListDefectGroups({
    query: { archived, order, page, page_size: pageSize, q: query || undefined, sort },
  })
  const payload = requireData(result.data, result.response?.status, result.error)
  return {
    items: payload.items.map(toGroupListItem),
    page: payload.page,
    pageSize: payload.page_size,
    total: payload.total,
  }
}

export async function listDefectTypes({
  archived = false,
  groupId,
  order = 'asc',
  page,
  pageSize,
  query,
  sort = 'code',
}: Pagination &
  Readonly<{
    archived?: boolean
    groupId?: string
    order?: SortOrder
    query?: string
    sort?: DefectSort
  }>): Promise<PaginatedResult<DefectType>> {
  const result = await defectsListDefectTypes({
    query: {
      archived,
      group_id: groupId,
      order,
      page,
      page_size: pageSize,
      q: query || undefined,
      sort,
    },
  })
  const payload = requireData(result.data, result.response?.status, result.error)
  return {
    items: payload.items.map(toType),
    page: payload.page,
    pageSize: payload.page_size,
    total: payload.total,
  }
}

export async function createDefectGroup(input: CreateDefectGroupInput): Promise<DefectGroup> {
  const result = await defectsCreateDefectGroup({ body: input })
  return toGroup(requireData(result.data, result.response?.status, result.error))
}

export async function updateDefectGroup(
  groupId: string,
  input: UpdateDefectGroupInput,
): Promise<DefectGroup> {
  const result = await defectsUpdateDefectGroup({ body: input, path: { group_id: groupId } })
  return toGroup(requireData(result.data, result.response?.status, result.error))
}

export async function updateDefectGroupArchived(
  groupId: string,
  archived: boolean,
): Promise<DefectGroup> {
  const result = await defectsUpdateDefectGroupArchived({
    body: { archived },
    path: { group_id: groupId },
  })
  return toGroup(requireData(result.data, result.response?.status, result.error))
}

export async function deleteDefectGroup(groupId: string): Promise<void> {
  const result = await defectsDeleteDefectGroup({ path: { group_id: groupId } })
  if (result.error !== undefined)
    throw new DefectsRequestError(result.response?.status ?? 0, errorCode(result.error))
}

export async function createDefectType(input: CreateDefectTypeInput): Promise<DefectType> {
  const result = await defectsCreateDefectType({ body: input })
  return toType(requireData(result.data, result.response?.status, result.error))
}

export async function updateDefectType(
  defectTypeId: string,
  input: UpdateDefectTypeInput,
): Promise<DefectType> {
  const result = await defectsUpdateDefectType({
    body: input,
    path: { defect_type_id: defectTypeId },
  })
  return toType(requireData(result.data, result.response?.status, result.error))
}

export async function updateDefectTypeArchived(
  defectTypeId: string,
  archived: boolean,
): Promise<DefectType> {
  const result = await defectsUpdateDefectTypeArchived({
    body: { archived },
    path: { defect_type_id: defectTypeId },
  })
  return toType(requireData(result.data, result.response?.status, result.error))
}

export async function deleteDefectType(defectTypeId: string): Promise<void> {
  const result = await defectsDeleteDefectType({ path: { defect_type_id: defectTypeId } })
  if (result.error !== undefined)
    throw new DefectsRequestError(result.response?.status ?? 0, errorCode(result.error))
}

function requireData<T>(data: T | undefined, status: number | undefined, error: unknown): T {
  if (data === undefined) throw new DefectsRequestError(status ?? 0, errorCode(error))
  return data
}

function errorCode(error: unknown): string | undefined {
  if (typeof error !== 'object' || error === null || !('code' in error)) return undefined
  return typeof error.code === 'string' ? error.code : undefined
}

function toGroup(group: DefectGroupResponse): DefectGroup {
  return {
    activeTypesCount: 0,
    archivedAt: group.archived_at,
    code: group.code,
    description: group.description,
    id: group.id,
    name: group.name,
    typesCount: 0,
  }
}

function toGroupListItem(group: DefectGroupListItemResponse): DefectGroup {
  return {
    ...toGroup(group),
    activeTypesCount: group.active_types_count,
    typesCount: group.types_count,
  }
}

function toType(defectType: DefectTypeResponse): DefectType {
  return {
    archivedAt: defectType.archived_at,
    code: defectType.code,
    description: defectType.description,
    engineerAction: defectType.engineer_action,
    group: {
      archivedAt: defectType.group.archived_at,
      code: defectType.group.code,
      id: defectType.group.id,
      name: defectType.group.name,
    },
    groupId: defectType.group_id,
    id: defectType.id,
    name: defectType.name,
    possibleCause: defectType.possible_cause,
  }
}
