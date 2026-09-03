import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import { AuditFilter } from '@/components/Common/AuditFilter'
import { auditColumns } from '@/components/User/Audit/columns'
import PendingAudit from '@/components/User/Audit/PendingAudit'
import { listUserAudit, type AuditSort, type SortOrder } from '@/features/users/users-api'
import { toExclusiveUtcDateRange, type DatePeriod } from '@/lib/date'
import { listDate, listEnum, listOrder, listPage, listPageSize } from '@/lib/list-search'

const userAuditSorts = ['actor_display_name', 'created_at'] as const satisfies readonly AuditSort[]

export const Route = createFileRoute('/_layout/admin/user/audit')({
  validateSearch: validateUserAuditSearch,
  component: Audit,
  pendingComponent: () => <PendingAudit showPageHeader />,
})

type AuditQuery = Readonly<{
  createdFrom?: string
  createdTo?: string
  order: SortOrder
  page: number
  pageSize: number
  sort: AuditSort
}>

function auditSortParams(
  sorting: DataTableSorting,
): Readonly<{ order: SortOrder; sort: AuditSort }> {
  const [current] = sorting
  const sort = listEnum(userAuditSorts, current?.id) ?? 'created_at'
  return { order: current?.desc ? 'desc' : 'asc', sort }
}

function getUserAuditQueryOptions(params: AuditQuery) {
  return {
    queryFn: () => listUserAudit(params),
    queryKey: ['audit', 'user', params],
  }
}

export function Audit() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const pagination: DataTablePaginationState = {
    pageIndex: (search.page ?? 1) - 1,
    pageSize: search.pageSize ?? (25 as PageSize),
  }
  const sorting = sortingFromSearch(search)
  const period = search.from && search.to ? { from: search.from, to: search.to } : null
  const auditQuery = {
    ...(period ? toAuditPeriodQuery(period) : {}),
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    ...auditSortParams(sorting),
  }
  const {
    data: audit,
    isError,
    isFetching,
    refetch,
  } = useQuery({
    ...getUserAuditQueryOptions(auditQuery),
    placeholderData: keepPreviousData,
  })

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 lg:px-12">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Аудит пользователей</h1>
        <p className="mt-2 text-muted-foreground">История действий с учётными записями.</p>
      </div>
      <div className="pt-8">
        <div className="mb-4 flex justify-end">
          <AuditFilter
            onApply={(nextPeriod) => {
              navigate({
                search: (previous) => ({
                  ...previous,
                  from: nextPeriod?.from,
                  page: undefined,
                  to: nextPeriod?.to,
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
            columns={auditColumns}
            data={audit.items}
            fixedLayout
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
            onSortingChange={(nextSorting) => {
              navigate({
                search: (previous) => ({
                  ...previous,
                  ...searchForSorting(nextSorting),
                  page: undefined,
                }),
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

function toAuditPeriodQuery(
  period: DatePeriod,
): Readonly<{ createdFrom: string; createdTo: string }> {
  const range = toExclusiveUtcDateRange(period)

  return {
    createdFrom: range.from,
    createdTo: range.to,
  }
}

type UserAuditSearch = Readonly<{
  from?: string
  order?: SortOrder
  page?: number
  pageSize?: PageSize
  sort?: AuditSort
  to?: string
}>

export function validateUserAuditSearch(search: Record<string, unknown>): UserAuditSearch {
  const from = listDate(search.from)
  const to = listDate(search.to)

  return {
    from: from && to && from <= to ? from : undefined,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    sort: listEnum(userAuditSorts, search.sort),
    to: from && to && from <= to ? to : undefined,
  }
}

function sortingFromSearch(search: UserAuditSearch): DataTableSorting {
  return [{ id: search.sort ?? 'created_at', desc: search.order ? search.order === 'desc' : true }]
}

function searchForSorting(sorting: DataTableSorting) {
  const [current] = sorting
  const sort = listEnum(userAuditSorts, current?.id) ?? 'created_at'
  const desc = current?.desc ?? true

  return {
    order: sort === 'created_at' && desc ? undefined : desc ? 'desc' : 'asc',
    sort: sort === 'created_at' ? undefined : sort,
  } as const
}
