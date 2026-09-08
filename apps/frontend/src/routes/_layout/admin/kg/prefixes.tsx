import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'

import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

import { AddKgPrefix } from '@/components/Kg/Prefixes/AddKgPrefix'
import { createKgPrefixColumns } from '@/components/Kg/Prefixes/columns'
import { KgPrefixFilters } from '@/components/Kg/Prefixes/KgPrefixFilters'
import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import { listKgPrefixes, type KgPrefixSort } from '@/features/kg/kg-prefixes-api'
import { listEnum, listOrder, listPage, listPageSize, listQuery } from '@/lib/list-search'

const kgPrefixTableSorts = [
  'archived_at',
  'name',
  'prefix',
  'short_code',
] as const satisfies readonly KgPrefixSort[]

export const Route = createFileRoute('/_layout/admin/kg/prefixes')({
  component: KgPrefixes,
  validateSearch: validateKgPrefixSearch,
})

function KgPrefixes() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const pagination: DataTablePaginationState = {
    pageIndex: (search.page ?? 1) - 1,
    pageSize: search.pageSize ?? (25 as PageSize),
  }
  const sorting = sortingFromSearch(search, archived)
  const [queryInput, setQueryInput] = useState('')

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

  const params = {
    archived,
    order: sorting[0]?.desc ? ('desc' as const) : ('asc' as const),
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    query: search.q,
    sort: sortFor(sorting[0]?.id, archived),
  }
  const result = useQuery({
    queryFn: () => listKgPrefixes(params),
    queryKey: ['kg', 'prefixes', params],
    placeholderData: keepPreviousData,
  })
  const prefixes = result.data?.items ?? []
  const columns = useMemo(() => createKgPrefixColumns(archived), [archived])

  const setArchived = (nextArchived: boolean) => {
    navigate({
      search: (previous) => ({
        ...previous,
        archived: nextArchived ? true : undefined,
        order: undefined,
        page: undefined,
        sort: undefined,
      }),
    })
  }

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">DevEUI-префиксы</h1>
        <AddKgPrefix />
      </div>
      <Tabs
        className="mt-5"
        onValueChange={(value) => setArchived(value === 'archived')}
        value={archived ? 'archived' : 'current'}
      >
        <TabsList>
          <TabsTrigger value="current">Текущие</TabsTrigger>
          <TabsTrigger value="archived">Архивные</TabsTrigger>
        </TabsList>
      </Tabs>
      <div className="mt-4">
        <KgPrefixFilters onQueryChange={setQueryInput} query={queryInput} />
      </div>
      <div className="mt-4">
        {!result.data ? (
          result.isError ? (
            <DataLoadError onRetry={() => void result.refetch()} />
          ) : (
            <PendingKgPrefixes />
          )
        ) : prefixes.length === 0 ? (
          <EmptyState />
        ) : (
          <DataTable
            columns={columns}
            data={prefixes}
            loading={result.isFetching}
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
                search: (previous) => ({
                  ...previous,
                  ...searchForSorting(next, archived),
                  page: undefined,
                }),
              })
            }}
            pagination={pagination}
            sorting={sorting}
            total={result.data?.total ?? 0}
          />
        )}
      </div>
    </section>
  )
}

function sortFor(id: string | undefined, archived: boolean): KgPrefixSort {
  return listEnum(kgPrefixTableSorts, id) ?? (archived ? 'archived_at' : 'prefix')
}

export function validateKgPrefixSearch(search: Record<string, unknown>): KgPrefixSearch {
  return {
    archived: search.archived === true ? true : undefined,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    q: listQuery(search.q),
    sort: listEnum(kgPrefixTableSorts, search.sort),
  }
}

type KgPrefixSearch = Readonly<{
  archived?: true
  order?: 'asc' | 'desc'
  page?: number
  pageSize?: PageSize
  q?: string
  sort?: KgPrefixTableSort
}>

type KgPrefixTableSort = (typeof kgPrefixTableSorts)[number]

function sortingFromSearch(search: KgPrefixSearch, archived: boolean): DataTableSorting {
  return [
    {
      desc: search.order ? search.order === 'desc' : archived,
      id: search.sort ?? (archived ? 'archived_at' : 'prefix'),
    },
  ]
}

function searchForSorting(sorting: DataTableSorting, archived: boolean) {
  const [current] = sorting
  const sort = listEnum(kgPrefixTableSorts, current?.id) ?? (archived ? 'archived_at' : 'prefix')
  const desc = current?.desc ?? archived
  const defaultSort = archived ? 'archived_at' : 'prefix'

  return {
    order: desc === archived && sort === defaultSort ? undefined : desc ? 'desc' : 'asc',
    sort: sort === defaultSort ? undefined : sort,
  } as const
}

function EmptyState() {
  return (
    <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed">
      <div className="text-center">
        <p className="font-medium">Префиксов пока нет</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Добавьте префикс, чтобы он появился в списке.
        </p>
      </div>
    </div>
  )
}

function PendingKgPrefixes() {
  return (
    <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed">
      <p className="text-sm text-muted-foreground">Загрузка префиксов…</p>
    </div>
  )
}
