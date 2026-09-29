import type { QueryClient } from '@tanstack/react-query'
import { isApiError, type ProductionOrder } from '@web-app/api-client'

import { invalidateTags } from '@/lib/queries'

export type { ProductionOrder }
export type ProductionOrderSort =
  | 'archived_at'
  | 'batches_count'
  | 'created_at'
  | 'name'
  | 'total_planned_qty'

export function isProductionOrderInUseError(error: unknown): boolean {
  return isApiError(error, 'production_order_in_use')
}

/** Refresh the orders, the batches that show them, and the audit log after an order has changed. */
export function invalidateProductionOrderQueries(queryClient: QueryClient) {
  return invalidateTags(queryClient, 'Production orders', 'Batches', 'Audit')
}
