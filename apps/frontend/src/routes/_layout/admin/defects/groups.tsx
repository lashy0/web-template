import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { listDefectGroupsOptions } from '@web-app/api-client'
import { useMemo } from 'react'

import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

import { AddDefectGroup } from '@/components/Defects/Groups/AddDefectGroup'
import { DefectGroupFilters } from '@/components/Defects/Groups/DefectGroupFilters'
import PendingDefectGroups from '@/components/Defects/Groups/PendingDefectGroups'
import { createDefectGroupColumns } from '@/components/Defects/Groups/columns'
import { DataLoadError } from '@/components/Common/DataLoadError'
import { ListEmptyState } from '@/components/Common/ListEmptyState'
import { DataTable } from '@/components/Common/DataTable'
import { type DefectSort } from '@/features/defects/defects-api'
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

const defectSorts = ['archived_at', 'code', 'name'] as const satisfies readonly DefectSort[]

export const Route = createFileRoute('/_layout/admin/defects/groups')({
  validateSearch: validateDefectGroupSearch,
  component: DefectGroups,
  pendingComponent: PendingDefectGroups,
})

type DefectGroupSearch = ListPageSearch &
  ListSortSearch<DefectSort> &
  Readonly<{ archived?: true; q?: string }>

function validateDefectGroupSearch(search: Record<string, unknown>): DefectGroupSearch {
  return {
    archived: search.archived === true ? true : undefined,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    q: listQuery(search.q),
    sort: listEnum(defectSorts, search.sort),
  }
}

function defaultSort(archived: boolean): ListSortDefault<DefectSort> {
  return archived ? { desc: true, id: 'archived_at' } : { desc: false, id: 'code' }
}

function DefectGroups() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const pagination = paginationFromSearch(search)
  const sorting = sortingFromSearch(search, defaultSort(archived))
  const [queryInput, setQueryInput] = useSearchInput(search.q, (q) => {
    navigate({ replace: true, search: (previous) => ({ ...previous, page: undefined, q }) })
  })
  const columns = useMemo(() => createDefectGroupColumns(archived), [archived])

  const result = useQuery({
    ...listDefectGroupsOptions({
      query: {
        ...pageQuery(pagination),
        ...sortQuery(defectSorts, sorting, defaultSort(archived)),
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
        <h1 className="text-3xl font-semibold tracking-tight">Группы дефектов</h1>
        <AddDefectGroup />
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
        <DefectGroupFilters onQueryChange={setQueryInput} query={queryInput} />
      </div>
      <div className="mt-4">
        {!result.data ? (
          result.isError ? (
            <DataLoadError onRetry={() => void result.refetch()} />
          ) : (
            <PendingDefectGroups />
          )
        ) : result.data.items.length === 0 ? (
          <ListEmptyState
            description={
              search.q
                ? 'Попробуйте изменить параметры поиска.'
                : archived
                  ? 'Архивированные группы появятся здесь.'
                  : 'Добавьте группу, чтобы она появилась в списке.'
            }
            title={search.q ? 'Ничего не найдено' : archived ? 'Архив пуст' : 'Групп пока нет'}
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
                  ...searchFromSorting(defectSorts, next, defaultSort(archived)),
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
