import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Outlet, createFileRoute } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'

import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import { BatchFilters } from '@/components/Batches/BatchFilters'
import { AddBatch } from '@/components/Batches/AddBatch'
import PendingBatches from '@/components/Batches/PendingBatches'
import { createBatchColumns } from '@/components/Batches/columns'
import {
  batchQueryKeys,
  listBatches,
  type BatchSort,
  type BatchStatus,
  type SortOrder,
} from '@/features/batches/batches-api'
import { listEnum, listOrder, listPage, listPageSize, listQuery } from '@/lib/list-search'
import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

const batchSorts = [
  'archived_at',
  'completed_at',
  'created_at',
  'day_plan_qty',
  'name',
  'planned_qty',
  'status',
  'updated_at',
] as const satisfies readonly BatchSort[]

const batchStatuses = ['IN_PRODUCTION', 'COMPLETED'] as const

export const Route = createFileRoute('/_layout/admin/production/batches')({
  component: BatchesRoute,
  pendingComponent: () => <PendingBatches showPageHeader />,
  validateSearch: validateBatchesSearch,
})

type BatchesSearch = Readonly<{
  archived?: true
  order?: SortOrder
  page?: number
  pageSize?: PageSize
  q?: string
  sort?: BatchSort
  status?: BatchStatus
}>
type BatchesQuery = Readonly<{
  archived: boolean
  order: SortOrder
  page: number
  pageSize: number
  query?: string
  sort: BatchSort
  status?: BatchStatus
}>

export function validateBatchesSearch(search: Record<string, unknown>): BatchesSearch {
  return {
    archived: search.archived === true ? true : undefined,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    q: listQuery(search.q),
    sort: listEnum(batchSorts, search.sort),
    status: listEnum(batchStatuses, search.status),
  }
}

function BatchesRoute() {
  return <Outlet />
}

export function Batches() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const pagination: DataTablePaginationState = {
    pageIndex: (search.page ?? 1) - 1,
    pageSize: search.pageSize ?? (25 as PageSize),
  }
  const sorting = sortingFromSearch(search, archived)
  const [queryInput, setQueryInput] = useState(search.q ?? '')

  useEffect(() => setQueryInput(search.q ?? ''), [search.q])
  useEffect(() => {
    const timeout = window.setTimeout(() => {
      const query = queryInput.trim()
      if (query !== (search.q ?? '')) {
        navigate({
          replace: true,
          search: (previous) => ({ ...previous, page: undefined, q: query || undefined }),
        })
      }
    }, 300)
    return () => window.clearTimeout(timeout)
  }, [navigate, queryInput, search.q])

  const params: BatchesQuery = {
    archived,
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    query: search.q,
    status: search.status,
    ...sortParams(sorting),
  }
  const columns = useMemo(() => createBatchColumns(), [])
  const { data, isError, isFetching, refetch } = useQuery({
    placeholderData: keepPreviousData,
    queryFn: () => listBatches(params),
    queryKey: batchQueryKeys.list(params),
  })

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">Партии</h1>
        {!archived ? <AddBatch /> : null}
      </div>
      <Tabs
        className="mt-5"
        onValueChange={(value) =>
          navigate({
            search: (previous) => ({
              ...previous,
              archived: value === 'archived' ? true : undefined,
              order: undefined,
              page: undefined,
              sort: undefined,
              status: undefined,
            }),
          })
        }
        value={archived ? 'archived' : 'current'}
      >
        <TabsList>
          <TabsTrigger value="current">Текущие</TabsTrigger>
          <TabsTrigger value="archived">Архивные</TabsTrigger>
        </TabsList>
      </Tabs>
      <div className="mt-5">
        <BatchFilters
          onQueryChange={setQueryInput}
          onStatusChange={(status) =>
            navigate({
              search: (previous) => ({
                ...previous,
                page: undefined,
                status: status === 'all' ? undefined : status,
              }),
            })
          }
          query={queryInput}
          status={search.status ?? 'all'}
        />
      </div>
      <div className="mt-4">
        {!data ? (
          isError ? (
            <DataLoadError onRetry={() => void refetch()} />
          ) : (
            <PendingBatches />
          )
        ) : data.items.length === 0 ? (
          <EmptyState archived={archived} hasQuery={Boolean(search.q) || Boolean(search.status)} />
        ) : (
          <DataTable
            columns={columns}
            data={data.items}
            loading={isFetching}
            onPaginationChange={(next) =>
              navigate({
                search: (previous) => ({
                  ...previous,
                  page: next.pageIndex === 0 ? undefined : next.pageIndex + 1,
                  pageSize: next.pageSize === 25 ? undefined : (next.pageSize as PageSize),
                }),
              })
            }
            onSortingChange={(next) =>
              navigate({
                search: (previous) => ({
                  ...previous,
                  ...searchForSorting(next, archived),
                  page: undefined,
                }),
              })
            }
            pagination={pagination}
            sorting={sorting}
            total={data.total}
          />
        )}
      </div>
    </section>
  )
}

function sortParams(sorting: DataTableSorting): Readonly<{ order: SortOrder; sort: BatchSort }> {
  const [current] = sorting
  const sort = listEnum(batchSorts, current?.id)
  return sort
    ? { order: current?.desc ? 'desc' : 'asc', sort }
    : { order: 'desc', sort: 'created_at' }
}

function sortingFromSearch(search: BatchesSearch, archived: boolean): DataTableSorting {
  const defaultSort = archived ? 'archived_at' : 'created_at'
  return [{ desc: search.order ? search.order === 'desc' : true, id: search.sort ?? defaultSort }]
}

function searchForSorting(sorting: DataTableSorting, archived: boolean) {
  const [current] = sorting
  const defaultSort = archived ? 'archived_at' : 'created_at'
  const sort = listEnum(batchSorts, current?.id) ?? defaultSort
  const desc = current?.desc ?? true
  return {
    order: desc ? undefined : 'asc',
    sort: sort === defaultSort ? undefined : sort,
  } as const
}

function EmptyState({ archived, hasQuery }: Readonly<{ archived: boolean; hasQuery: boolean }>) {
  return (
    <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed">
      <div className="flex flex-col gap-1 text-center">
        <p className="font-medium">
          {hasQuery ? 'Ничего не найдено' : archived ? 'Архив пуст' : 'Партий пока нет'}
        </p>
        <p className="text-sm text-muted-foreground">
          {hasQuery
            ? 'Попробуйте изменить параметры поиска.'
            : archived
              ? 'Архивированные партии появятся здесь.'
              : 'Добавьте партию, чтобы она появилась в списке.'}
        </p>
      </div>
    </div>
  )
}
