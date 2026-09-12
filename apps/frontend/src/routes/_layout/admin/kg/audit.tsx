import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'

import { AuditFilter } from '@/components/Common/AuditFilter'
import { DataLoadError } from '@/components/Common/DataLoadError'
import { ListEmptyState } from '@/components/Common/ListEmptyState'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import PendingAudit from '@/components/Kg/Audit/PendingAudit'
import { kgAuditColumns } from '@/components/Kg/Audit/columns'
import { listKgAudit, type KgAuditSort } from '@/features/kg/kg-prefixes-api'
import { toExclusiveUtcDateRange } from '@/lib/date'
import { listDate, listEnum, listOrder, listPage, listPageSize } from '@/lib/list-search'

const kgAuditSorts = ['actor_display_name', 'created_at'] as const satisfies readonly KgAuditSort[]

export const Route = createFileRoute('/_layout/admin/kg/audit')({
  validateSearch: validateKgAuditSearch,
  component: KgAudit,
  pendingComponent: () => <PendingAudit showPageHeader />,
})

function KgAudit() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const pagination: DataTablePaginationState = {
    pageIndex: (search.page ?? 1) - 1,
    pageSize: search.pageSize ?? (25 as PageSize),
  }
  const sorting = sortingFromSearch(search)
  const [current] = sorting
  const sort = listEnum(kgAuditSorts, current?.id) ?? 'created_at'
  const order = current?.desc ? 'desc' : 'asc'
  const period = search.from && search.to ? { from: search.from, to: search.to } : null
  const range = period ? toExclusiveUtcDateRange(period) : undefined
  const {
    data: audit,
    isError,
    isFetching,
    refetch,
  } = useQuery({
    queryFn: () =>
      listKgAudit({
        createdFrom: range?.from,
        createdTo: range?.to,
        order,
        page: pagination.pageIndex + 1,
        pageSize: pagination.pageSize,
        sort,
      }),
    queryKey: ['audit', 'kg', range, order, pagination, sort],
    placeholderData: keepPreviousData,
  })

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Аудит КГ</h1>
      </div>
      <div className="mt-5">
        <div className="mb-4 flex">
          <AuditFilter
            onApply={(next) => {
              navigate({
                search: (previous) => ({
                  ...previous,
                  from: next?.from,
                  page: undefined,
                  to: next?.to,
                }),
              })
            }}
            value={period}
          />
        </div>
        {!audit ? (
          isError ? (
            <DataLoadError onRetry={() => void refetch()} />
          ) : (
            <PendingAudit />
          )
        ) : audit.items.length === 0 ? (
          <EmptyState />
        ) : (
          <DataTable
            columns={kgAuditColumns}
            data={audit.items}
            loading={isFetching}
            onPaginationChange={(next) => {
              navigate({
                search: (previous) => ({
                  ...previous,
                  page: next.pageIndex === 0 ? undefined : next.pageIndex + 1,
                  pageSize: next.pageSize === 25 ? undefined : (next.pageSize as PageSize),
                }),
              })
            }}
            onSortingChange={(next) => {
              navigate({
                search: (previous) => ({ ...previous, ...searchForSorting(next), page: undefined }),
              })
            }}
            pagination={pagination}
            sorting={sorting}
            total={audit.total}
          />
        )}
      </div>
    </section>
  )
}

function EmptyState() {
  return (
    <ListEmptyState description="Попробуйте изменить параметры поиска." title="Ничего не найдено" />
  )
}

type KgAuditSearch = Readonly<{
  from?: string
  order?: 'asc' | 'desc'
  page?: number
  pageSize?: PageSize
  sort?: KgAuditSort
  to?: string
}>

export function validateKgAuditSearch(search: Record<string, unknown>): KgAuditSearch {
  const from = listDate(search.from)
  const to = listDate(search.to)

  return {
    from: from && to && from <= to ? from : undefined,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    sort: listEnum(kgAuditSorts, search.sort),
    to: from && to && from <= to ? to : undefined,
  }
}

function sortingFromSearch(search: KgAuditSearch): DataTableSorting {
  return [{ id: search.sort ?? 'created_at', desc: search.order ? search.order === 'desc' : true }]
}

function searchForSorting(sorting: DataTableSorting) {
  const [current] = sorting
  const sort = listEnum(kgAuditSorts, current?.id) ?? 'created_at'
  const desc = current?.desc ?? true

  return {
    order: sort === 'created_at' && desc ? undefined : desc ? 'desc' : 'asc',
    sort: sort === 'created_at' ? undefined : sort,
  } as const
}
