import type { QueryClient } from '@tanstack/react-query'
import { isApiError, type KgVersion } from '@web-app/api-client'

import { invalidateTags } from '@/lib/queries'

export type { KgVersion }
export type KgVersionSort = 'archived_at' | 'code' | 'name'

export function isKgVersionCodeTakenError(error: unknown): boolean {
  return isApiError(error, 'kg_version_code_taken')
}

export function isKgVersionInUseError(error: unknown): boolean {
  return isApiError(error, 'kg_version_in_use')
}

/** Refresh the KG catalogs, which batches show too, and the audit log after a version has changed. */
export function invalidateKgVersionQueries(queryClient: QueryClient) {
  return invalidateTags(queryClient, 'KG catalogs', 'Audit')
}
