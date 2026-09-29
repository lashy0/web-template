import type { QueryClient } from '@tanstack/react-query'
import { isApiError, type DefectGroup, type DefectType } from '@web-app/api-client'

import { invalidateTags } from '@/lib/queries'

export type { DefectGroup, DefectType }
export type DefectSort = 'archived_at' | 'code' | 'name'

export function isDefectGroupCodeTakenError(error: unknown): boolean {
  return isApiError(error, 'defect_group_code_taken')
}

export function isDefectGroupArchivedError(error: unknown): boolean {
  return isApiError(error, 'defect_group_archived')
}

export function isDefectGroupHasActiveTypesError(error: unknown): boolean {
  return isApiError(error, 'defect_group_has_active_types')
}

export function isDefectGroupInUseError(error: unknown): boolean {
  return isApiError(error, 'defect_group_in_use')
}

export function isDefectTypeCodeTakenError(error: unknown): boolean {
  return isApiError(error, 'defect_type_code_taken')
}

/** Refresh the defect catalog and the audit log after a group or a type has changed. */
export function invalidateDefectQueries(queryClient: QueryClient) {
  return invalidateTags(queryClient, 'Defect catalog', 'Audit')
}
