import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'

import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

import { AddKgVersion } from '@/components/Kg/Versions/AddKgVersion'
import { createKgVersionColumns } from '@/components/Kg/Versions/columns'
import { KgVersionFilters } from '@/components/Kg/Versions/KgVersionFilters'
import PendingKgVersions from '@/components/Kg/Versions/PendingKgVersions'
import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import { listKgVersions, type KgVersionSort } from '@/features/kg/kg-versions-api'
import { listEnum, listOrder, listPage, listPageSize, listQuery } from '@/lib/list-search'

const kgVersionTableSorts = ['archived_at', 'code', 'name'] as const

export const Route = createFileRoute('/_layout/admin/kg/versions')({
  validateSearch: validateKgVersionSearch,
  component: KgVersions,
  pendingComponent: PendingKgVersions,
})

function KgVersions() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const pagination: DataTablePaginationState = {
    pageIndex: (search.page ?? 1) - 1,
    pageSize: search.pageSize ?? (25 as PageSize),
  }
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

  const params = {
    archived,
    order: sorting[0]?.desc ? ('desc' as const) : ('asc' as const),
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    query: search.q,
    sort: sortFor(sorting[0]?.id, archived),
  }
  const result = useQuery({
    queryFn: () => listKgVersions(params),
    queryKey: ['kg', 'versions', params],
    placeholderData: keepPreviousData,
  })
  const columns = useMemo(() => createKgVersionColumns(archived), [archived])

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
        <h1 className="text-3xl font-semibold tracking-tight">Версии КГ</h1>
        <AddKgVersion />
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
        <KgVersionFilters onQueryChange={setQueryInput} query={queryInput} />
      </div>
      <div className="mt-4">
        {!result.data ? (
          result.isError ? (
            <DataLoadError onRetry={() => void result.refetch()} />
          ) : (
            <PendingKgVersions />
          )
        ) : result.data.items.length === 0 ? (
          <EmptyState archived={archived} filtered={Boolean(search.q)} />
        ) : (
          <DataTable
            columns={columns}
            data={result.data.items}
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
            total={result.data.total}
          />
        )}
      </div>
    </section>
  )
}

function sortFor(id: string | undefined, archived: boolean): KgVersionSort {
  return listEnum(kgVersionTableSorts, id) ?? (archived ? 'archived_at' : 'code')
}

export function validateKgVersionSearch(search: Record<string, unknown>): KgVersionSearch {
  return {
    archived: search.archived === true ? true : undefined,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    q: listQuery(search.q),
    sort: listEnum(kgVersionTableSorts, search.sort),
  }
}

type KgVersionSearch = Readonly<{
  archived?: true
  order?: 'asc' | 'desc'
  page?: number
  pageSize?: PageSize
  q?: string
  sort?: KgVersionTableSort
}>

type KgVersionTableSort = (typeof kgVersionTableSorts)[number]

function sortingFromSearch(search: KgVersionSearch, archived: boolean): DataTableSorting {
  return [
    {
      desc: search.order ? search.order === 'desc' : archived,
      id: search.sort ?? (archived ? 'archived_at' : 'code'),
    },
  ]
}

function searchForSorting(sorting: DataTableSorting, archived: boolean) {
  const [current] = sorting
  const sort = listEnum(kgVersionTableSorts, current?.id) ?? (archived ? 'archived_at' : 'code')
  const desc = current?.desc ?? archived
  const defaultSort = archived ? 'archived_at' : 'code'

  return {
    order: desc === archived && sort === defaultSort ? undefined : desc ? 'desc' : 'asc',
    sort: sort === defaultSort ? undefined : sort,
  } as const
}

function EmptyState({ archived, filtered }: Readonly<{ archived: boolean; filtered: boolean }>) {
  return (
    <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed">
      <div className="text-center">
        <p className="font-medium">
          {filtered ? 'Ничего не найдено' : archived ? 'Архив пуст' : 'Версий КГ пока нет'}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {filtered
            ? 'Попробуйте изменить параметры поиска.'
            : archived
              ? 'Архивированные версии появятся здесь.'
              : 'Добавьте версию, чтобы она появилась в списке.'}
        </p>
      </div>
    </div>
  )
}
