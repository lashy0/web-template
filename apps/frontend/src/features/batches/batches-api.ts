import {
  batchCompleteBatch,
  batchCreateBatch,
  batchDeleteBatch,
  batchGetBatch,
  batchListBatches,
  batchPreviewDevEuiRange,
  batchUpdateBatch,
  batchUpdateBatchArchived,
  zBatchStatus,
  type BatchResponse,
  type BatchStatus as ApiBatchStatus,
  type CreateBatchRequest,
  type DevEuiRangePreviewResponse,
  type UpdateBatchRequest,
} from '@web-app/api-client'

export type BatchStatus = ApiBatchStatus
export type CreateBatchInput = CreateBatchRequest
export type UpdateBatchInput = UpdateBatchRequest
export type DevEuiRangePreview = Readonly<{
  firstDevEui: string
  lastDevEui: string
}>
export type SortOrder = 'asc' | 'desc'
export type BatchSort =
  | 'archived_at'
  | 'completed_at'
  | 'created_at'
  | 'day_plan_qty'
  | 'name'
  | 'planned_qty'
  | 'status'
  | 'updated_at'

export const batchStatuses = zBatchStatus.options satisfies readonly BatchStatus[]

export const batchStatusLabels: Readonly<Record<BatchStatus, string>> = {
  COMPLETED: 'Завершена',
  IN_PRODUCTION: 'В производстве',
}

export const batchStatusOptions: readonly Readonly<{ label: string; value: BatchStatus }>[] =
  batchStatuses.map((value) => ({ label: batchStatusLabels[value], value }))

export const batchStatusFilterOptions: readonly Readonly<{
  label: string
  value: BatchStatus | 'all'
}>[] = [{ label: 'Все статусы', value: 'all' }, ...batchStatusOptions]

export type ProductionOrderSummary = Readonly<{
  id: string
  name: string
}>

export type Batch = Readonly<{
  archivedAt: string | null
  canDelete: boolean
  completedAt: string | null
  createdAt: string
  dayPlanQty: number
  description: string | null
  id: string
  name: string
  plannedQty: number
  productionOrder: ProductionOrderSummary | null
  status: BatchStatus
  updatedAt: string
}>

export type Pagination = Readonly<{ page: number; pageSize: number }>
export type PaginatedResult<Item> = Readonly<{
  items: Item[]
  page: number
  pageSize: number
  total: number
}>

export const batchQueryKeys = {
  all: ['batches'] as const,
  detail: (batchId: string) => ['batches', 'detail', batchId] as const,
  devEuiRange: (devEuiPrefix: string, plannedQty: number) =>
    ['batches', 'dev-eui-range', devEuiPrefix, plannedQty] as const,
  list: (params: unknown) => ['batches', 'list', params] as const,
}

export class BatchRequestError extends Error {
  readonly code: string | undefined
  readonly status: number

  constructor(status: number, code?: string) {
    super('Не удалось получить данные партии.')
    this.code = code
    this.name = 'BatchRequestError'
    this.status = status
  }
}

export async function listBatches({
  archived = false,
  order = 'desc',
  page,
  pageSize,
  query,
  sort = 'created_at',
  status,
}: Pagination &
  Readonly<{
    archived?: boolean
    order?: SortOrder
    query?: string
    sort?: BatchSort
    status?: BatchStatus
  }>): Promise<PaginatedResult<Batch>> {
  const result = await batchListBatches({
    query: {
      archived,
      order,
      page,
      page_size: pageSize,
      q: query || undefined,
      sort,
      status: status ?? undefined,
    },
  })
  const payload = requireData(result.data, result.response?.status, result.error)

  return {
    items: payload.items.map(toBatch),
    page: payload.page,
    pageSize: payload.page_size,
    total: payload.total,
  }
}

export async function getBatch(batchId: string): Promise<Batch> {
  const result = await batchGetBatch({ path: { batch_id: batchId } })
  return toBatch(requireData(result.data, result.response?.status, result.error))
}

export function batchErrorCode(error: unknown): string | undefined {
  return error instanceof BatchRequestError ? error.code : undefined
}

export function batchErrorMessage(error: unknown): string | undefined {
  switch (batchErrorCode(error)) {
    case 'batch_archived':
      return 'Партия архивирована.'
    case 'batch_already_completed':
      return 'Партия уже завершена.'
    case 'batch_cannot_be_deleted':
      return 'Невозможно удалить партию: по ней уже есть производственные операции.'
    case 'batch_conflict':
      return 'Параметры партии конфликтуют с существующими данными.'
    case 'batch_dev_eui_prefix_not_found':
      return 'Выбранный DevEUI-префикс не найден.'
    case 'batch_edit_not_allowed':
    case 'batch_edit_window_expired':
      return 'Изменение этой партии больше недоступно.'
    case 'batch_kg_version_archived':
      return 'Архивную версию КГ нельзя назначить партии.'
    case 'batch_kg_version_not_found':
      return 'Выбранная версия КГ не найдена.'
    case 'batch_not_found':
      return 'Партия не найдена. Возможно, она уже была удалена.'
    default:
      return undefined
  }
}

export async function createBatch(input: CreateBatchInput): Promise<Batch> {
  const result = await batchCreateBatch({ body: input })
  return toBatch(requireData(result.data, result.response?.status, result.error))
}

export async function completeBatch(batchId: string): Promise<Batch> {
  const result = await batchCompleteBatch({ path: { batch_id: batchId } })
  return toBatch(requireData(result.data, result.response?.status, result.error))
}

export async function previewDevEuiRange(
  devEuiPrefix: string,
  plannedQty: number,
): Promise<DevEuiRangePreview> {
  const result = await batchPreviewDevEuiRange({
    query: {
      dev_eui_prefix: devEuiPrefix,
      planned_qty: plannedQty,
    },
  })
  return toDevEuiRangePreview(requireData(result.data, result.response?.status, result.error))
}

export async function updateBatch(batchId: string, input: UpdateBatchInput): Promise<Batch> {
  const result = await batchUpdateBatch({ body: input, path: { batch_id: batchId } })
  return toBatch(requireData(result.data, result.response?.status, result.error))
}

export async function updateBatchArchived(batchId: string, archived: boolean): Promise<Batch> {
  const result = await batchUpdateBatchArchived({
    body: { archived },
    path: { batch_id: batchId },
  })
  return toBatch(requireData(result.data, result.response?.status, result.error))
}

export async function deleteBatch(batchId: string): Promise<void> {
  const result = await batchDeleteBatch({ path: { batch_id: batchId } })
  if (result.error !== undefined) {
    throw new BatchRequestError(result.response?.status ?? 0, errorCode(result.error))
  }
}

function requireData<T>(data: T | undefined, status: number | undefined, error: unknown): T {
  if (data === undefined) {
    throw new BatchRequestError(status ?? 0, errorCode(error))
  }
  return data
}

function errorCode(error: unknown): string | undefined {
  if (typeof error !== 'object' || error === null || !('code' in error)) return undefined
  return typeof error.code === 'string' ? error.code : undefined
}

function toBatch(batch: BatchResponse): Batch {
  return {
    archivedAt: batch.archived_at,
    canDelete: batch.can_delete,
    completedAt: batch.completed_at,
    createdAt: batch.created_at,
    dayPlanQty: batch.day_plan_qty,
    description: batch.description,
    id: batch.id,
    name: batch.name,
    plannedQty: batch.planned_qty,
    productionOrder: batch.production_order
      ? { id: batch.production_order.id, name: batch.production_order.name }
      : null,
    status: batch.status,
    updatedAt: batch.updated_at,
  }
}

function toDevEuiRangePreview(preview: DevEuiRangePreviewResponse): DevEuiRangePreview {
  return {
    firstDevEui: preview.first_dev_eui,
    lastDevEui: preview.last_dev_eui,
  }
}
