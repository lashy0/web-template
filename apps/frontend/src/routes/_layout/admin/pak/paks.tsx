import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { listPakDevicesOptions } from '@web-app/api-client'
import { useMemo } from 'react'

import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

import { DataLoadError } from '@/components/Common/DataLoadError'
import { ListEmptyState } from '@/components/Common/ListEmptyState'
import { DataTable } from '@/components/Common/DataTable'
import { AddPak } from '@/components/Pak/Paks/AddPak'
import { PakFilters } from '@/components/Pak/Paks/PakFilters'
import PendingPaks from '@/components/Pak/Paks/PendingPaks'
import { createPakColumns } from '@/components/Pak/Paks/columns'
import { pakKinds, type PakKind, type PakSort } from '@/features/paks/paks-api'
import { activeFilter, activities, type Activity } from '@/lib/activity'
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

const pakSorts = [
  'archived_at',
  'code',
  'kind',
  'last_seen_at',
] as const satisfies readonly PakSort[]

export const Route = createFileRoute('/_layout/admin/pak/paks')({
  validateSearch: validatePaksSearch,
  component: Paks,
  pendingComponent: () => <PendingPaks showPageHeader />,
})

type PaksSearch = ListPageSearch &
  ListSortSearch<PakSort> &
  Readonly<{
    archived?: true
    kind?: PakKind
    q?: string
    status?: Activity
  }>

function validatePaksSearch(search: Record<string, unknown>): PaksSearch {
  const archived = search.archived === true ? true : undefined

  return {
    archived,
    kind: listEnum(pakKinds, search.kind),
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    q: listQuery(search.q),
    sort: listEnum(pakSorts, search.sort),
    status: !archived ? listEnum(activities, search.status) : undefined,
  }
}

function defaultSort(archived: boolean): ListSortDefault<PakSort> {
  return archived ? { desc: true, id: 'archived_at' } : { desc: false, id: 'code' }
}

function Paks() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const kind = search.kind ?? 'all'
  const status = search.status ?? 'all'
  const pagination = paginationFromSearch(search)
  const sorting = sortingFromSearch(search, defaultSort(archived))
  const [queryInput, setQueryInput] = useSearchInput(search.q, (q) => {
    navigate({ replace: true, search: (previous) => ({ ...previous, page: undefined, q }) })
  })
  const columns = useMemo(() => createPakColumns(archived), [archived])

  const {
    data: paks,
    isError,
    isFetching,
    refetch,
  } = useQuery({
    ...listPakDevicesOptions({
      query: {
        ...pageQuery(pagination),
        ...sortQuery(pakSorts, sorting, defaultSort(archived)),
        active: activeFilter(archived, status),
        archived,
        kindIn: kind !== 'all' ? [kind] : undefined,
        searchIgnoreCase: true,
        searchString: search.q,
      },
    }),
    placeholderData: keepPreviousData,
  })

  const hasFilters = Boolean(search.q) || kind !== 'all' || (!archived && status !== 'all')

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">ПАК</h1>
        <AddPak />
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
      <div className="mt-4">
        <PakFilters
          archived={archived}
          kind={kind}
          onKindChange={(value) => {
            navigate({
              search: (previous) => ({
                ...previous,
                kind: value === 'all' ? undefined : value,
                page: undefined,
              }),
            })
          }}
          onQueryChange={setQueryInput}
          onStatusChange={(value) => {
            navigate({
              search: (previous) => ({
                ...previous,
                page: undefined,
                status: value === 'all' ? undefined : value,
              }),
            })
          }}
          query={queryInput}
          status={status}
        />
      </div>
      <div className="mt-4">
        {!paks ? (
          isError ? (
            <DataLoadError onRetry={() => void refetch()} />
          ) : (
            <PendingPaks />
          )
        ) : paks.items.length === 0 ? (
          <ListEmptyState
            description={
              hasFilters
                ? 'Попробуйте изменить параметры поиска.'
                : archived
                  ? 'Архивированные ПАК появятся здесь.'
                  : 'Добавьте ПАК, чтобы он появился в списке.'
            }
            title={hasFilters ? 'Ничего не найдено' : archived ? 'Архив пуст' : 'ПАК пока нет'}
          />
        ) : (
          <DataTable
            columns={columns}
            data={paks.items}
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
                  ...searchFromSorting(pakSorts, next, defaultSort(archived)),
                  page: undefined,
                }),
              })
            }}
            pagination={pagination}
            sorting={sorting}
            total={paks.total}
          />
        )}
      </div>
    </section>
  )
}
