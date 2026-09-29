import type { QueryClient } from '@tanstack/react-query'
import { isApiError, PakDeviceKind, type PakDevice } from '@web-app/api-client'

import { invalidateTags } from '@/lib/queries'

export type Pak = PakDevice
export type PakKind = PakDeviceKind
export type PakSort = 'archived_at' | 'code' | 'kind' | 'last_seen_at'

export const pakKinds: readonly PakKind[] = Object.values(PakDeviceKind)

export const pakKindLabels: Readonly<Record<PakKind, string>> = {
  engineering: 'Инженерный',
  otk_line: 'Линия ОТК',
}

export const pakKindOptions: readonly Readonly<{ label: string; value: PakKind }>[] = pakKinds.map(
  (value) => ({ label: pakKindLabels[value], value }),
)

export const pakKindFilterOptions: readonly Readonly<{ label: string; value: PakKind | 'all' }>[] =
  [{ label: 'Все типы', value: 'all' }, ...pakKindOptions]

export function isPakCodeTakenError(error: unknown): boolean {
  return isApiError(error, 'pak_device_code_taken')
}

export function isPakInUseError(error: unknown): boolean {
  return isApiError(error, 'pak_in_use')
}

/** Refresh the PAK lists and the audit log after a PAK has changed. */
export function invalidatePakQueries(queryClient: QueryClient) {
  return invalidateTags(queryClient, 'PAK devices', 'Audit')
}
