import { isDataTablePageSize } from '@/components/Common/DataTable/DataTable.constants'
import type {
  DataTablePaginationState,
  DataTableSorting,
  PageSize,
} from '@/components/Common/DataTable'
import { useEffect, useRef, useState } from 'react'
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

export function listEnum<T extends string>(values: readonly T[], value: unknown): T | undefined {
  return isOneOf(values, value) ? value : undefined
}

function isOneOf<T extends string>(values: readonly T[], value: unknown): value is T {
  return typeof value === 'string' && values.some((item) => item === value)
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

/** The page and page size a list keeps in the URL; the defaults stay out of it. */
export type ListPageSearch = Readonly<{ page?: number; pageSize?: PageSize }>

/** The sorting a list keeps in the URL; the default sorting stays out of it. */
export type ListSortSearch<Sort extends string> = Readonly<{ order?: ListOrder; sort?: Sort }>

/** The column a list sorts by when the URL names none, such as `{ id: 'name', desc: false }`. */
export type ListSortDefault<Sort extends string> = Readonly<{ desc: boolean; id: Sort }>

export function paginationFromSearch(search: ListPageSearch): DataTablePaginationState {
  return { pageIndex: (search.page ?? 1) - 1, pageSize: search.pageSize ?? 25 }
}

export function searchFromPagination(pagination: DataTablePaginationState): ListPageSearch {
  return {
    page: pagination.pageIndex === 0 ? undefined : pagination.pageIndex + 1,
    pageSize: pagination.pageSize === 25 ? undefined : (pagination.pageSize as PageSize),
  }
}

/** The page parameters of a generated list query. */
export function pageQuery(pagination: DataTablePaginationState) {
  return { currentPage: pagination.pageIndex + 1, pageSize: pagination.pageSize }
}

export function sortingFromSearch<Sort extends string>(
  search: ListSortSearch<Sort>,
  fallback: ListSortDefault<Sort>,
): DataTableSorting {
  const id = search.sort ?? fallback.id
  const desc = search.order ? search.order === 'desc' : id === fallback.id && fallback.desc
  return [{ desc, id }]
}

export function searchFromSorting<Sort extends string>(
  sorts: readonly Sort[],
  sorting: DataTableSorting,
  fallback: ListSortDefault<Sort>,
): ListSortSearch<Sort> {
  const [current] = sorting
  const sort = listEnum(sorts, current?.id) ?? fallback.id
  const desc = current?.desc ?? fallback.desc
  if (sort === fallback.id && desc === fallback.desc) {
    return { order: undefined, sort: undefined }
  }
  return { order: desc ? 'desc' : 'asc', sort: sort === fallback.id ? undefined : sort }
}

/** The sorting parameters of a generated list query. */
export function sortQuery<Sort extends string>(
  sorts: readonly Sort[],
  sorting: DataTableSorting,
  fallback: ListSortDefault<Sort>,
): Readonly<{ orderBy: Sort; sortOrder: ListOrder }> {
  const [current] = sorting
  const sort = listEnum(sorts, current?.id)
  if (!sort) {
    return { orderBy: fallback.id, sortOrder: fallback.desc ? 'desc' : 'asc' }
  }
  return { orderBy: sort, sortOrder: current?.desc ? 'desc' : 'asc' }
}

/**
 * The text of a search box that commits to the URL 300 ms after the last
 * keystroke; `commit` receives the trimmed text, or `undefined` when empty.
 */
export function useSearchInput(
  committed: string | undefined,
  commit: (query: string | undefined) => void,
): [string, (value: string) => void] {
  const [input, setInput] = useState(committed ?? '')
  const commitRef = useRef(commit)

  useEffect(() => {
    commitRef.current = commit
  })

  useEffect(() => {
    setInput(committed ?? '')
  }, [committed])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      const query = input.trim()
      if (query !== (committed ?? '')) {
        commitRef.current(query || undefined)
      }
    }, 300)
    return () => window.clearTimeout(timeout)
  }, [committed, input])

  return [input, setInput]
}
