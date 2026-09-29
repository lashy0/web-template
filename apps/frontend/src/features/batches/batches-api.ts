import type { QueryClient } from '@tanstack/react-query'
import { BatchStatus, isApiError, type Batch } from '@web-app/api-client'

import { invalidateTags } from '@/lib/queries'

export type { Batch, BatchStatus }
export type BatchSort = 'archived_at' | 'created_at' | 'name' | 'planned_qty' | 'status'

/** How long after creation a batch can be edited or deleted; `BATCH_EDIT_WINDOW` in the backend. */
const BATCH_EDIT_WINDOW_MS = 60 * 60 * 1000

export const batchStatuses: readonly BatchStatus[] = Object.values(BatchStatus)

export const batchStatusLabels: Readonly<Record<BatchStatus, string>> = {
  in_production: 'В производстве',
  completed: 'Завершена',
}

export const batchStatusFilterOptions: readonly Readonly<{
  label: string
  value: BatchStatus | 'all'
}>[] = [
  { label: 'Все статусы', value: 'all' },
  ...batchStatuses.map((value) => ({ label: batchStatusLabels[value], value })),
]

/** Whether the edit window is still open; the backend has the final say. */
export function isBatchEditable(batch: Pick<Batch, 'archivedAt' | 'createdAt'>): boolean {
  return (
    batch.archivedAt === null && Date.now() - Date.parse(batch.createdAt) < BATCH_EDIT_WINDOW_MS
  )
}

export function isBatchEditWindowExpiredError(error: unknown): boolean {
  return isApiError(error, 'batch_edit_window_expired')
}

export function isBatchInUseError(error: unknown): boolean {
  return isApiError(error, 'batch_in_use')
}

/**
 * Refresh the batches, the production orders that count them, the KG units
 * and the audit log after a batch has changed.
 */
export function invalidateBatchQueries(queryClient: QueryClient) {
  return invalidateTags(
    queryClient,
    'Batches',
    'Production orders',
    'KG catalogs',
    'KG units',
    'Audit',
  )
}
