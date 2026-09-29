import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { listBatchesOptions } from '@web-app/api-client'
import { useMemo } from 'react'

import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

import { DataLoadError } from '@/components/Common/DataLoadError'
import { ListEmptyState } from '@/components/Common/ListEmptyState'
import { DataTable } from '@/components/Common/DataTable'
import { BatchFilters } from '@/components/Batches/BatchFilters'
import { AddBatch } from '@/components/Batches/AddBatch'
import PendingBatches from '@/components/Batches/PendingBatches'
import { createBatchColumns } from '@/components/Batches/columns'
import { batchStatuses, type BatchSort, type BatchStatus } from '@/features/batches/batches-api'
import {
  listEnum,
  listOrder,
  listPage,
  listPageSize,
  listQuery,
  pageQuery,
  paginationFromSearch,
  searchFromPagination,
  searchFromSorting,
  sortingFromSearch,
  sortQuery,
  useSearchInput,
  type ListPageSearch,
  type ListSortDefault,
  type ListSortSearch,
} from '@/lib/list-search'

const batchSorts = [
  'archived_at',
  'created_at',
  'name',
  'planned_qty',
  'status',
] as const satisfies readonly BatchSort[]

export const Route = createFileRoute('/_layout/admin/production/batches/')({
  component: Batches,
  pendingComponent: () => <PendingBatches showPageHeader />,
  validateSearch: validateBatchesSearch,
})

type BatchesSearch = ListPageSearch &
  ListSortSearch<BatchSort> &
  Readonly<{ archived?: true; q?: string; status?: BatchStatus }>

function validateBatchesSearch(search: Record<string, unknown>): BatchesSearch {
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

function defaultSort(archived: boolean): ListSortDefault<BatchSort> {
  return { desc: true, id: archived ? 'archived_at' : 'created_at' }
}

function Batches() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const pagination = paginationFromSearch(search)
  const sorting = sortingFromSearch(search, defaultSort(archived))
  const [queryInput, setQueryInput] = useSearchInput(search.q, (q) => {
    navigate({ replace: true, search: (previous) => ({ ...previous, page: undefined, q }) })
  })
  const columns = useMemo(() => createBatchColumns(), [])

  const { data, isError, isFetching, refetch } = useQuery({
    ...listBatchesOptions({
      query: {
        ...pageQuery(pagination),
        ...sortQuery(batchSorts, sorting, defaultSort(archived)),
        archived,
        searchIgnoreCase: true,
        searchString: search.q,
        statusIn: search.status ? [search.status] : undefined,
      },
    }),
    placeholderData: keepPreviousData,
  })
  const filtered = Boolean(search.q || search.status)

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">Партии</h1>
        <AddBatch />
      </div>
      <Tabs
        className="mt-5"
        onValueChange={(value) => {
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
        }}
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
          onStatusChange={(status) => {
            navigate({
              search: (previous) => ({
                ...previous,
                page: undefined,
                status: status === 'all' ? undefined : status,
              }),
            })
          }}
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
          <ListEmptyState
            description={
              filtered
                ? 'Попробуйте изменить параметры поиска.'
                : archived
                  ? 'Архивированные партии появятся здесь.'
                  : 'Добавьте партию, чтобы она появилась в списке.'
            }
            title={filtered ? 'Ничего не найдено' : archived ? 'Архив пуст' : 'Партий пока нет'}
          />
        ) : (
          <DataTable
            columns={columns}
            data={data.items}
            loading={isFetching}
            onPaginationChange={(next) => {
              navigate({
                search: (previous) => ({ ...previous, ...searchFromPagination(next) }),
              })
            }}
            onSortingChange={(next) => {
              navigate({
                search: (previous) => ({
                  ...previous,
                  ...searchFromSorting(batchSorts, next, defaultSort(archived)),
                  page: undefined,
                }),
              })
            }}
            pagination={pagination}
            sorting={sorting}
            total={data.total}
          />
        )}
      </div>
    </section>
  )
}
