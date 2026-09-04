import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { AuditFilter } from '@/components/Common/AuditFilter'
import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import PendingAudit from '@/components/Defects/Audit/PendingAudit'
import { defectAuditColumns } from '@/components/Defects/Audit/columns'
import {
  listDefectAudit,
  type DefectAuditSort,
  type SortOrder,
} from '@/features/defects/defects-api'
import { toExclusiveUtcDateRange } from '@/lib/date'
import { listDate, listEnum, listOrder, listPage, listPageSize } from '@/lib/list-search'

const defectAuditSorts = [
  'actor_display_name',
  'created_at',
] as const satisfies readonly DefectAuditSort[]

export const Route = createFileRoute('/_layout/admin/defects/audit')({
  validateSearch: validateDefectAuditSearch,
  component: DefectAudit,
  pendingComponent: () => <PendingAudit showPageHeader />,
})

function DefectAudit() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const pagination: DataTablePaginationState = {
    pageIndex: (search.page ?? 1) - 1,
    pageSize: search.pageSize ?? (25 as PageSize),
  }
  const sorting = sortingFromSearch(search)
  const period = search.from && search.to ? { from: search.from, to: search.to } : null
  const [current] = sorting
  const sort: DefectAuditSort = listEnum(defectAuditSorts, current?.id) ?? 'created_at'
  const order: SortOrder = current?.desc ? 'desc' : 'asc'
  const range = period ? toExclusiveUtcDateRange(period) : undefined
  const {
    data: audit,
    isError,
    isFetching,
    refetch,
  } = useQuery({
    queryFn: () =>
      listDefectAudit({
        createdFrom: range?.from,
        createdTo: range?.to,
        order,
        page: pagination.pageIndex + 1,
        pageSize: pagination.pageSize,
        sort,
      }),
    queryKey: ['audit', 'defects', range, order, pagination, sort],
    placeholderData: keepPreviousData,
  })

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Аудит дефектов</h1>
        <p className="mt-2 text-muted-foreground">История действий с группами и типами дефектов.</p>
      </div>
      <div className="pt-8">
        <div className="mb-4 flex justify-end">
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
        ) : audit.items.length === 0 && period ? (
          <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed">
            <div className="text-center">
              <p className="font-medium">Ничего не найдено</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Попробуйте изменить параметры поиска.
              </p>
            </div>
          </div>
        ) : (
          <DataTable
            columns={defectAuditColumns}
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

type DefectAuditSearch = Readonly<{
  from?: string
  order?: SortOrder
  page?: number
  pageSize?: PageSize
  sort?: DefectAuditSort
  to?: string
}>

export function validateDefectAuditSearch(search: Record<string, unknown>): DefectAuditSearch {
  const from = listDate(search.from)
  const to = listDate(search.to)

  return {
    from: from && to && from <= to ? from : undefined,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    sort: listEnum(defectAuditSorts, search.sort),
    to: from && to && from <= to ? to : undefined,
  }
}

function sortingFromSearch(search: DefectAuditSearch): DataTableSorting {
  return [{ id: search.sort ?? 'created_at', desc: search.order ? search.order === 'desc' : true }]
}

function searchForSorting(sorting: DataTableSorting) {
  const [current] = sorting
  const sort = listEnum(defectAuditSorts, current?.id) ?? 'created_at'
  const desc = current?.desc ?? true

  return {
    order: sort === 'created_at' && desc ? undefined : desc ? 'desc' : 'asc',
    sort: sort === 'created_at' ? undefined : sort,
  } as const
}
