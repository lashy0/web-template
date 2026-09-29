import type { QueryClient } from '@tanstack/react-query'
import { isApiError, type KgPrefix } from '@web-app/api-client'

import { invalidateTags } from '@/lib/queries'

export type { KgPrefix }
export type KgPrefixSort = 'archived_at' | 'name' | 'prefix' | 'short_code'

export function isKgPrefixTakenError(error: unknown): boolean {
  return isApiError(error, 'kg_prefix_taken')
}

export function isKgPrefixShortCodeTakenError(error: unknown): boolean {
  return isApiError(error, 'kg_prefix_short_code_taken')
}

export function isKgPrefixInUseError(error: unknown): boolean {
  return isApiError(error, 'kg_prefix_in_use')
}

/** Refresh the KG catalogs, which batches show too, and the audit log after a prefix has changed. */
export function invalidateKgPrefixQueries(queryClient: QueryClient) {
  return invalidateTags(queryClient, 'KG catalogs', 'Audit')
}
