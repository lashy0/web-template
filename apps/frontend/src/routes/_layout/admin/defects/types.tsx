import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { listDefectTypesOptions } from '@web-app/api-client'
import { useMemo } from 'react'
import { z } from 'zod'

import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

import { AddDefectType } from '@/components/Defects/Types/AddDefectType'
import { DefectTypeFilters } from '@/components/Defects/Types/DefectTypeFilters'
import PendingDefectTypes from '@/components/Defects/Types/PendingDefectTypes'
import { createDefectTypeColumns } from '@/components/Defects/Types/columns'
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
const groupIdSchema = z.uuid()

export const Route = createFileRoute('/_layout/admin/defects/types')({
  validateSearch: validateDefectTypeSearch,
  component: DefectTypes,
  pendingComponent: PendingDefectTypes,
})

type DefectTypeSearch = ListPageSearch &
  ListSortSearch<DefectSort> &
  Readonly<{ archived?: true; group?: string; q?: string }>

function validateDefectTypeSearch(search: Record<string, unknown>): DefectTypeSearch {
  return {
    archived: search.archived === true ? true : undefined,
    group: groupIdSchema.safeParse(search.group).data,
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

function DefectTypes() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const groupId = search.group
  const pagination = paginationFromSearch(search)
  const sorting = sortingFromSearch(search, defaultSort(archived))
  const [queryInput, setQueryInput] = useSearchInput(search.q, (q) => {
    navigate({ replace: true, search: (previous) => ({ ...previous, page: undefined, q }) })
  })
  const columns = useMemo(() => createDefectTypeColumns(archived), [archived])

  const result = useQuery({
    ...listDefectTypesOptions({
      query: {
        ...pageQuery(pagination),
        ...sortQuery(defectSorts, sorting, defaultSort(archived)),
        archived,
        groupIdIn: groupId ? [groupId] : undefined,
        searchIgnoreCase: true,
        searchString: search.q,
      },
    }),
    placeholderData: keepPreviousData,
  })
  const filtered = Boolean(search.q || groupId)

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">Типы дефектов</h1>
        <AddDefectType groupId={groupId} />
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
        <DefectTypeFilters
          groupId={groupId}
          onGroupChange={(value) => {
            navigate({
              search: (previous) => ({
                ...previous,
                group: value === 'all' ? undefined : value,
                page: undefined,
              }),
            })
          }}
          onQueryChange={setQueryInput}
          query={queryInput}
        />
      </div>
      <div className="mt-4">
        {!result.data ? (
          result.isError ? (
            <DataLoadError onRetry={() => void result.refetch()} />
          ) : (
            <PendingDefectTypes />
          )
        ) : result.data.items.length === 0 ? (
          <ListEmptyState
            description={
              filtered
                ? 'Попробуйте изменить параметры поиска.'
                : archived
                  ? 'Архивированные типы появятся здесь.'
                  : 'Добавьте тип, чтобы он появился в списке.'
            }
            title={filtered ? 'Ничего не найдено' : archived ? 'Архив пуст' : 'Типов пока нет'}
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
