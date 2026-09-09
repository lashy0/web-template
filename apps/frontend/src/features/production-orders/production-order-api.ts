import {
  productionOrderArchiveOrder,
  productionOrderCreateOrder,
  productionOrderDeleteOrder,
  productionOrderGetOrder,
  productionOrderListOrders,
  productionOrderUpdateOrder,
  type CreateProductionOrderRequest,
  type ProductionOrderResponse,
  type UpdateProductionOrderRequest,
} from '@web-app/api-client'

export type SortOrder = 'asc' | 'desc'
export type ProductionOrderSort =
  | 'archived_at'
  | 'batches_count'
  | 'created_at'
  | 'name'
  | 'total_planned_qty'
  | 'updated_at'

export type ProductionOrderSummary = Readonly<{
  archivedAt: string | null
  id: string
  name: string
}>

export type ProductionOrder = Readonly<
  ProductionOrderSummary & {
    batchesCount: number
    createdAt: string
    description: string | null
    totalPlannedQty: number
    updatedAt: string
  }
>

export type CreateProductionOrderInput = CreateProductionOrderRequest
export type UpdateProductionOrderInput = UpdateProductionOrderRequest

export type Pagination = Readonly<{ page: number; pageSize: number }>
export type PaginatedResult<Item> = Readonly<{
  items: Item[]
  page: number
  pageSize: number
  total: number
}>

export const productionOrderQueryKeys = {
  all: ['production-orders'] as const,
  detail: (orderId: string) => ['production-orders', 'detail', orderId] as const,
  list: (params: unknown) => ['production-orders', 'list', params] as const,
}

export class ProductionOrderRequestError extends Error {
  readonly code: string | undefined
  readonly status: number

  constructor(status: number, code?: string) {
    super('Не удалось получить данные производственного заказа.')
    this.code = code
    this.name = 'ProductionOrderRequestError'
    this.status = status
  }
}

export async function listProductionOrders({
  archived = false,
  order = 'desc',
  page,
  pageSize,
  query,
  sort = 'created_at',
}: Pagination &
  Readonly<{
    archived?: boolean
    order?: SortOrder
    query?: string
    sort?: ProductionOrderSort
  }>): Promise<PaginatedResult<ProductionOrder>> {
  const result = await productionOrderListOrders({
    query: {
      archived,
      order,
      page,
      page_size: pageSize,
      q: query || undefined,
      sort,
    },
  })
  const payload = requireData(result.data, result.response?.status, result.error)

  return {
    items: payload.items.map(toProductionOrder),
    page: payload.page,
    pageSize: payload.page_size,
    total: payload.total,
  }
}

export async function getProductionOrder(orderId: string): Promise<ProductionOrder> {
  const result = await productionOrderGetOrder({ path: { order_id: orderId } })
  return toProductionOrder(requireData(result.data, result.response?.status, result.error))
}

export async function createProductionOrder(
  input: CreateProductionOrderInput,
): Promise<ProductionOrder> {
  const result = await productionOrderCreateOrder({ body: input })
  return toProductionOrder(requireData(result.data, result.response?.status, result.error))
}

export async function updateProductionOrder(
  orderId: string,
  input: UpdateProductionOrderInput,
): Promise<ProductionOrder> {
  const result = await productionOrderUpdateOrder({ body: input, path: { order_id: orderId } })
  return toProductionOrder(requireData(result.data, result.response?.status, result.error))
}

export async function updateProductionOrderArchived(
  orderId: string,
  archived: boolean,
): Promise<ProductionOrder> {
  const result = await productionOrderArchiveOrder({
    body: { archived },
    path: { order_id: orderId },
  })
  return toProductionOrder(requireData(result.data, result.response?.status, result.error))
}

export async function deleteProductionOrder(orderId: string): Promise<void> {
  const result = await productionOrderDeleteOrder({ path: { order_id: orderId } })
  if (result.error !== undefined) {
    throw new ProductionOrderRequestError(result.response?.status ?? 0, errorCode(result.error))
  }
}

export function productionOrderErrorCode(error: unknown): string | undefined {
  return error instanceof ProductionOrderRequestError ? error.code : undefined
}

export function productionOrderErrorMessage(error: unknown): string | undefined {
  switch (productionOrderErrorCode(error)) {
    case 'production_order_archived':
      return 'Производственный заказ архивирован.'
    case 'production_order_cannot_be_deleted':
      return 'Невозможно удалить производственный заказ: в нём есть партии.'
    case 'production_order_conflict':
      return 'Производственный заказ с таким названием уже существует.'
    case 'production_order_not_found':
      return 'Производственный заказ не найден. Возможно, он уже был удалён.'
    default:
      return undefined
  }
}

function requireData<T>(data: T | undefined, status: number | undefined, error: unknown): T {
  if (data === undefined) {
    throw new ProductionOrderRequestError(status ?? 0, errorCode(error))
  }
  return data
}

function errorCode(error: unknown): string | undefined {
  if (typeof error !== 'object' || error === null || !('code' in error)) return undefined
  return typeof error.code === 'string' ? error.code : undefined
}

function toProductionOrder(order: ProductionOrderResponse): ProductionOrder {
  return {
    archivedAt: order.archived_at,
    batchesCount: order.batches_count,
    createdAt: order.created_at,
    description: order.description,
    id: order.id,
    name: order.name,
    totalPlannedQty: order.total_planned_qty,
    updatedAt: order.updated_at,
  }
}
