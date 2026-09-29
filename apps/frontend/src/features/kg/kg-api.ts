import { KgOtkStatus, KgState, type KgUnit } from '@web-app/api-client'

export type { KgUnit }

export const kgStates: readonly KgState[] = Object.values(KgState)
export const kgOtkStatuses: readonly KgOtkStatus[] = Object.values(KgOtkStatus)

export const kgStateLabels: Readonly<Record<KgState, string>> = {
  registered: 'Зарегистрирована',
  packed: 'Упакована',
  shipped: 'Отгружена',
  scrapped: 'Списана',
}

export const kgOtkStatusLabels: Readonly<Record<KgOtkStatus, string>> = {
  not_verified: 'Не проверена',
  passed: 'ОТК пройдена',
  failed: 'ОТК не пройдена',
}

export const kgStateFilterOptions: readonly Readonly<{ label: string; value: KgState | 'all' }>[] =
  [
    { label: 'Все состояния', value: 'all' },
    ...kgStates.map((value) => ({ label: kgStateLabels[value], value })),
  ]

export const kgOtkStatusFilterOptions: readonly Readonly<{
  label: string
  value: KgOtkStatus | 'all'
}>[] = [
  { label: 'Любой результат ОТК', value: 'all' },
  ...kgOtkStatuses.map((value) => ({ label: kgOtkStatusLabels[value], value })),
]
