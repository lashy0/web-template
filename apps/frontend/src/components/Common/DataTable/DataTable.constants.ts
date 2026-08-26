import type { PageSize } from './DataTable.types'

export const dataTablePageSizes = [5, 10, 25, 50] as const

export function isDataTablePageSize(value: number): value is PageSize {
  return dataTablePageSizes.includes(value as PageSize)
}
