import { isDataTablePageSize } from '@/components/Common/DataTable/DataTable.constants'
import type { PageSize } from '@/components/Common/DataTable'
import { z } from 'zod'

export type ListOrder = 'asc' | 'desc'

const listOrderSchema = z.enum(['asc', 'desc'])
const listPageSchema = z.coerce.number().int().min(2)
const listPageSizeSchema = z.coerce.number().refine(isDataTablePageSize)
const listQuerySchema = z
  .string()
  .trim()
  .min(1)
  .transform((value) => value.slice(0, 200))
const listDateSchema = z.iso.date()

export function listEnum<T extends string>(
  values: readonly [T, ...T[]],
  value: unknown,
): T | undefined {
  return z.enum(values).safeParse(value).data
}

export function listOrder(value: unknown): ListOrder | undefined {
  return listOrderSchema.safeParse(value).data
}

export function listPage(value: unknown): number | undefined {
  return listPageSchema.safeParse(value).data
}

export function listPageSize(value: unknown): PageSize | undefined {
  const pageSize = listPageSizeSchema.safeParse(value).data
  return pageSize === 25 ? undefined : pageSize
}

export function listQuery(value: unknown): string | undefined {
  return listQuerySchema.safeParse(value).data
}

export function listDate(value: unknown): string | undefined {
  return listDateSchema.safeParse(value).data
}
