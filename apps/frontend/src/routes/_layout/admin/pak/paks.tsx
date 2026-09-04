import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'

import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import { AddPak } from '@/components/Pak/Paks/AddPak'
import { PakFilters } from '@/components/Pak/Paks/PakFilters'
import PendingPaks from '@/components/Pak/Paks/PendingPaks'
import { createPakColumns } from '@/components/Pak/Paks/columns'
import { listPaks, type PakKind, type PakSort, type SortOrder } from '@/features/paks/paks-api'
import { listEnum, listOrder, listPage, listPageSize, listQuery } from '@/lib/list-search'

const pakKinds = ['ENGINEERING', 'OTK_LINE'] as const satisfies readonly PakKind[]
const pakStatuses = ['active', 'inactive'] as const
const pakTableSorts = [
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

type PaksQuery = Readonly<{
  active?: boolean
  archived: boolean
  kind?: PakKind
  order: SortOrder
  page: number
  pageSize: number
  query?: string
  sort: PakSort
}>
type StatusFilter = 'active' | 'all' | 'inactive'

function sortParams(sorting: DataTableSorting): Readonly<{ order: SortOrder; sort: PakSort }> {
  const [current] = sorting
  const sort = listEnum(pakTableSorts, current?.id)
  if (sort) {
    return { order: current?.desc ? 'desc' : 'asc', sort }
  }
  return { order: 'asc', sort: 'code' }
}
function queryOptions(params: PaksQuery) {
  return { queryFn: () => listPaks(params), queryKey: ['paks', params] }
}

function Paks() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const pagination: DataTablePaginationState = {
    pageIndex: (search.page ?? 1) - 1,
    pageSize: search.pageSize ?? (25 as PageSize),
  }
  const kind = search.kind ?? 'all'
  const status = search.status ?? 'all'
  const sorting = sortingFromSearch(search, archived)
  const [queryInput, setQueryInput] = useState(search.q ?? '')

  useEffect(() => {
    setQueryInput(search.q ?? '')
  }, [search.q])

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

  const paksQuery: PaksQuery = {
    active: !archived && status !== 'all' ? status === 'active' : undefined,
    archived,
    kind: kind !== 'all' ? kind : undefined,
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    query: search.q,
    ...sortParams(sorting),
  }
  const columns = useMemo(() => createPakColumns(archived), [archived])
  const {
    data: paks,
    isError,
    isFetching,
    refetch,
  } = useQuery({ ...queryOptions(paksQuery), placeholderData: keepPreviousData })
  const hasFilters = Boolean(search.q) || kind !== 'all' || (!archived && status !== 'all')
  const resetList = (nextArchived: boolean) => {
    navigate({
      search: (previous) => ({
        ...previous,
        archived: nextArchived ? true : undefined,
        order: undefined,
        page: undefined,
        sort: undefined,
        status: undefined,
      }),
    })
  }
  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">ПАК</h1>
        <p className="mt-2 text-muted-foreground">
          Управление программно-аппаратными комплексами.
        </p>
      </div>
      <Tabs
        className="mt-8"
        onValueChange={(value) => resetList(value === 'archived')}
        value={archived ? 'archived' : 'current'}
      >
        <TabsList>
          <TabsTrigger value="current">Текущие</TabsTrigger>
          <TabsTrigger value="archived">Архивные</TabsTrigger>
        </TabsList>
      </Tabs>
      <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
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
          onQueryChange={(value) => {
            setQueryInput(value)
          }}
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
        <AddPak />
      </div>
      <div className="mt-4">
        {!paks ? (
          isError ? (
            <DataLoadError onRetry={() => void refetch()} />
          ) : (
            <PendingPaks />
          )
        ) : paks.items.length === 0 ? (
          <EmptyState archived={archived} hasFilters={hasFilters} />
        ) : (
          <DataTable
            columns={columns}
            data={paks.items}
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
                  ...searchForSorting(nextSorting, archived),
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

type PaksSearch = Readonly<{
  archived?: true
  kind?: PakKind
  order?: SortOrder
  page?: number
  pageSize?: PageSize
  q?: string
  sort?: PakSort
  status?: Exclude<StatusFilter, 'all'>
}>

export function validatePaksSearch(search: Record<string, unknown>): PaksSearch {
  const archived = search.archived === true ? true : undefined

  return {
    archived,
    kind: listEnum(pakKinds, search.kind),
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    q: listQuery(search.q),
    sort: listEnum(pakTableSorts, search.sort),
    status: !archived ? listEnum(pakStatuses, search.status) : undefined,
  }
}

function sortingFromSearch(search: PaksSearch, archived: boolean): DataTableSorting {
  return [
    {
      desc: search.order ? search.order === 'desc' : archived,
      id: search.sort ?? (archived ? 'archived_at' : 'code'),
    },
  ]
}

function searchForSorting(sorting: DataTableSorting, archived: boolean) {
  const [current] = sorting
  const sort = listEnum(pakTableSorts, current?.id) ?? (archived ? 'archived_at' : 'code')
  const desc = current?.desc ?? archived
  const defaultSort = archived ? 'archived_at' : 'code'

  return {
    order: desc === archived && sort === defaultSort ? undefined : desc ? 'desc' : 'asc',
    sort: sort === defaultSort ? undefined : sort,
  } as const
}

function EmptyState({
  archived,
  hasFilters,
}: Readonly<{ archived: boolean; hasFilters: boolean }>) {
  return (
    <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed">
      <div className="text-center">
        <p className="font-medium">
          {hasFilters ? 'Ничего не найдено' : archived ? 'Архив пуст' : 'ПАК пока нет'}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {hasFilters
            ? 'Попробуйте изменить параметры поиска.'
            : archived
              ? 'Архивированные ПАК появятся здесь.'
              : 'Добавьте ПАК, чтобы он появился в списке.'}
        </p>
      </div>
    </div>
  )
}
