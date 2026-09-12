import {
  kgListKgByBatch,
  type KgBatchListItemResponse,
  type KgStatus as ApiKgStatus,
} from '@web-app/api-client'

export type KgStatus = ApiKgStatus

export const kgStatuses = [
  'IN_ENGINEER_REPAIR',
  'IN_PRODUCTION_REPAIR',
  'PACKED',
  'READY_FOR_PACKING',
  'READY_FOR_RETEST',
  'REGISTERED',
  'SCRAPPED',
  'SHIPPED',
  'TEST_FAILED',
  'TESTING',
] as const satisfies readonly KgStatus[]

export const kgStatusLabels: Readonly<Record<KgStatus, string>> = {
  IN_ENGINEER_REPAIR: 'Инженерный ремонт',
  IN_PRODUCTION_REPAIR: 'Производственный ремонт',
  PACKED: 'Упакована',
  READY_FOR_PACKING: 'Готова к упаковке',
  READY_FOR_RETEST: 'Готова к повторной ОТК',
  REGISTERED: 'Зарегистрирована',
  SCRAPPED: 'Списана',
  SHIPPED: 'Отгружена',
  TEST_FAILED: 'ОТК не пройдена',
  TESTING: 'На ОТК',
}

export const kgStatusFilterOptions: readonly Readonly<{
  label: string
  value: KgStatus | 'all'
}>[] = [{ label: 'Все статусы', value: 'all' }, ...kgStatuses.map((value) => ({
  label: kgStatusLabels[value],
  value,
}))]

export type Kg = Readonly<{
  devEui: string
  firmwareVersion: string | null
  lastVerificationAt: string | null
  status: KgStatus
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
  status,
}: Readonly<{
  batchId: string
  page: number
  pageSize: number
  query?: string
  status?: KgStatus
}>): Promise<KgList> {
  const result = await kgListKgByBatch({
    path: { batch_id: batchId },
    query: { page, page_size: pageSize, q: query || undefined, status },
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
    status: kg.status,
  }
}
