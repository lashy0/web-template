import {
  kgListKgByBatch,
  type KgBatchListItemResponse,
  type KgCurrentState as ApiKgCurrentState,
} from '@web-app/api-client'

export type KgCurrentState = ApiKgCurrentState

export const kgCurrentStates = [
  'IN_REPAIR',
  'ON_OTK',
  'OTK_FAILED',
  'OTK_PASSED',
  'PACKED',
  'REGISTERED',
  'SCRAPPED',
  'SHIPPED',
] as const satisfies readonly KgCurrentState[]

export const kgCurrentStateLabels: Readonly<Record<KgCurrentState, string>> = {
  IN_REPAIR: 'В ремонте',
  ON_OTK: 'На ОТК',
  OTK_FAILED: 'ОТК не пройдена',
  OTK_PASSED: 'ОТК пройдена',
  PACKED: 'Упакована',
  REGISTERED: 'Зарегистрирована',
  SCRAPPED: 'Списана',
  SHIPPED: 'Отгружена',
}

export const kgCurrentStateFilterOptions: readonly Readonly<{
  label: string
  value: KgCurrentState | 'all'
}>[] = [{ label: 'Все состояния', value: 'all' }, ...kgCurrentStates.map((value) => ({
  label: kgCurrentStateLabels[value],
  value,
}))]

export type Kg = Readonly<{
  devEui: string
  firmwareVersion: string | null
  lastVerificationAt: string | null
  currentState: KgCurrentState
}>

export type KgList = Readonly<{
  items: readonly Kg[]
  page: number
  pageSize: number
  total: number
}>

export const kgQueryKeys = {
  batch: (params: unknown) => ['kg', 'batch', params] as const,
}

export class KgRequestError extends Error {
  constructor() {
    super('Не удалось получить список КГ.')
  }
}

export async function listKgByBatch({
  batchId,
  page,
  pageSize,
  query,
  currentState,
}: Readonly<{
  batchId: string
  page: number
  pageSize: number
  query?: string
  currentState?: KgCurrentState
}>): Promise<KgList> {
  const result = await kgListKgByBatch({
    path: { batch_id: batchId },
    query: { page, page_size: pageSize, q: query || undefined, current_state: currentState },
  })
  if (result.data === undefined) throw new KgRequestError()

  return {
    items: result.data.items.map(toKg),
    page: result.data.page,
    pageSize: result.data.page_size,
    total: result.data.total,
  }
}

function toKg(kg: KgBatchListItemResponse): Kg {
  return {
    devEui: kg.dev_eui,
    firmwareVersion: kg.firmware_version ?? null,
    lastVerificationAt: kg.last_verification_at ?? null,
    currentState: kg.current_state,
  }
}
