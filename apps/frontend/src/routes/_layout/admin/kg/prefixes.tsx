import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { listKgPrefixesOptions } from '@web-app/api-client'
import { useMemo } from 'react'

import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

import { AddKgPrefix } from '@/components/Kg/Prefixes/AddKgPrefix'
import { createKgPrefixColumns } from '@/components/Kg/Prefixes/columns'
import { KgPrefixFilters } from '@/components/Kg/Prefixes/KgPrefixFilters'
import { DataLoadError } from '@/components/Common/DataLoadError'
import { ListEmptyState } from '@/components/Common/ListEmptyState'
import { DataTable } from '@/components/Common/DataTable'
import { type KgPrefixSort } from '@/features/kg/kg-prefixes-api'
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

const kgPrefixSorts = [
  'archived_at',
  'name',
  'prefix',
  'short_code',
] as const satisfies readonly KgPrefixSort[]

export const Route = createFileRoute('/_layout/admin/kg/prefixes')({
  component: KgPrefixes,
  validateSearch: validateKgPrefixSearch,
})

type KgPrefixSearch = ListPageSearch &
  ListSortSearch<KgPrefixSort> &
  Readonly<{ archived?: true; q?: string }>

function validateKgPrefixSearch(search: Record<string, unknown>): KgPrefixSearch {
  return {
    archived: search.archived === true ? true : undefined,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    q: listQuery(search.q),
    sort: listEnum(kgPrefixSorts, search.sort),
  }
}

function defaultSort(archived: boolean): ListSortDefault<KgPrefixSort> {
  return archived ? { desc: true, id: 'archived_at' } : { desc: false, id: 'prefix' }
}

function KgPrefixes() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const pagination = paginationFromSearch(search)
  const sorting = sortingFromSearch(search, defaultSort(archived))
  const [queryInput, setQueryInput] = useSearchInput(search.q, (q) => {
    navigate({ replace: true, search: (previous) => ({ ...previous, page: undefined, q }) })
  })
  const columns = useMemo(() => createKgPrefixColumns(archived), [archived])

  const result = useQuery({
    ...listKgPrefixesOptions({
      query: {
        ...pageQuery(pagination),
        ...sortQuery(kgPrefixSorts, sorting, defaultSort(archived)),
        archived,
        searchIgnoreCase: true,
        searchString: search.q,
      },
    }),
    placeholderData: keepPreviousData,
  })

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">DevEUI-префиксы</h1>
        <AddKgPrefix />
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
        <KgPrefixFilters onQueryChange={setQueryInput} query={queryInput} />
      </div>
      <div className="mt-4">
        {!result.data ? (
          result.isError ? (
            <DataLoadError onRetry={() => void result.refetch()} />
          ) : (
            <PendingKgPrefixes />
          )
        ) : result.data.items.length === 0 ? (
          <ListEmptyState
            description={
              search.q
                ? 'Попробуйте изменить параметры поиска.'
                : archived
                  ? 'Архивированные префиксы появятся здесь.'
                  : 'Добавьте префикс, чтобы он появился в списке.'
            }
            title={search.q ? 'Ничего не найдено' : archived ? 'Архив пуст' : 'Префиксов пока нет'}
          />
        ) : (
          <DataTable
            columns={columns}
            data={result.data.items}
            loading={result.isFetching}
            onPaginationChange={(next) => {
              navigate({
                search: (previous) => ({ ...previous, ...searchFromPagination(next) }),
              })
            }}
            onSortingChange={(next) => {
              navigate({
                search: (previous) => ({
                  ...previous,
                  ...searchFromSorting(kgPrefixSorts, next, defaultSort(archived)),
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

function PendingKgPrefixes() {
  return (
    <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed">
      <p className="text-sm text-muted-foreground">Загрузка префиксов…</p>
    </div>
  )
}
