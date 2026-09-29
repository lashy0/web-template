import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { listKgVersionsOptions } from '@web-app/api-client'
import { useMemo } from 'react'

import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

import { AddKgVersion } from '@/components/Kg/Versions/AddKgVersion'
import { createKgVersionColumns } from '@/components/Kg/Versions/columns'
import { KgVersionFilters } from '@/components/Kg/Versions/KgVersionFilters'
import PendingKgVersions from '@/components/Kg/Versions/PendingKgVersions'
import { DataLoadError } from '@/components/Common/DataLoadError'
import { ListEmptyState } from '@/components/Common/ListEmptyState'
import { DataTable } from '@/components/Common/DataTable'
import { type KgVersionSort } from '@/features/kg/kg-versions-api'
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

const kgVersionSorts = ['archived_at', 'code', 'name'] as const satisfies readonly KgVersionSort[]

export const Route = createFileRoute('/_layout/admin/kg/versions')({
  validateSearch: validateKgVersionSearch,
  component: KgVersions,
  pendingComponent: PendingKgVersions,
})

type KgVersionSearch = ListPageSearch &
  ListSortSearch<KgVersionSort> &
  Readonly<{ archived?: true; q?: string }>

function validateKgVersionSearch(search: Record<string, unknown>): KgVersionSearch {
  return {
    archived: search.archived === true ? true : undefined,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    q: listQuery(search.q),
    sort: listEnum(kgVersionSorts, search.sort),
  }
}

function defaultSort(archived: boolean): ListSortDefault<KgVersionSort> {
  return archived ? { desc: true, id: 'archived_at' } : { desc: false, id: 'code' }
}

function KgVersions() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const pagination = paginationFromSearch(search)
  const sorting = sortingFromSearch(search, defaultSort(archived))
  const [queryInput, setQueryInput] = useSearchInput(search.q, (q) => {
    navigate({ replace: true, search: (previous) => ({ ...previous, page: undefined, q }) })
  })
  const columns = useMemo(() => createKgVersionColumns(archived), [archived])

  const result = useQuery({
    ...listKgVersionsOptions({
      query: {
        ...pageQuery(pagination),
        ...sortQuery(kgVersionSorts, sorting, defaultSort(archived)),
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
        <h1 className="text-3xl font-semibold tracking-tight">Версии КГ</h1>
        <AddKgVersion />
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
          <ListEmptyState
            description={
              search.q
                ? 'Попробуйте изменить параметры поиска.'
                : archived
                  ? 'Архивированные версии появятся здесь.'
                  : 'Добавьте версию, чтобы она появилась в списке.'
            }
            title={search.q ? 'Ничего не найдено' : archived ? 'Архив пуст' : 'Версий КГ пока нет'}
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
                  ...searchFromSorting(kgVersionSorts, next, defaultSort(archived)),
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
