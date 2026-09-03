import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'

import { Button } from '@web-app/ui/components/button'

import { AddDefectGroup } from '@/components/Defects/Groups/AddDefectGroup'
import { DefectGroupFilters } from '@/components/Defects/Groups/DefectGroupFilters'
import PendingDefectGroups from '@/components/Defects/Groups/PendingDefectGroups'
import { createDefectGroupColumns } from '@/components/Defects/Groups/columns'
import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import { listDefectGroups, type DefectSort, type SortOrder } from '@/features/defects/defects-api'
import { listEnum, listOrder, listPage, listPageSize, listQuery } from '@/lib/list-search'

const defectTableSorts = ['archived_at', 'code', 'name'] as const

export const Route = createFileRoute('/_layout/admin/defects/groups')({
  validateSearch: validateDefectGroupSearch,
  component: DefectGroups,
  pendingComponent: PendingDefectGroups,
})

function DefectGroups() {
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
    order: sorting[0]?.desc ? 'desc' : ('asc' as SortOrder),
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    query: search.q,
    sort: sortFor(sorting[0]?.id, archived),
  }
  const result = useQuery({
    queryFn: () => listDefectGroups(params),
    queryKey: ['defects', 'groups', params],
    placeholderData: keepPreviousData,
  })
  const columns = useMemo(() => createDefectGroupColumns(archived), [archived])
  const resetList = (nextArchived: boolean) => {
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
    <section className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Группы дефектов</h1>
          <p className="mt-2 text-muted-foreground">Управление классификацией дефектов.</p>
        </div>
        <AddDefectGroup />
      </div>
      <div className="pt-8">
        <div className="@container mb-4">
          <div className="flex flex-col gap-3 @[56rem]:flex-row @[56rem]:items-center @[56rem]:justify-between">
            <div className="flex shrink-0 items-center gap-1">
              <Button
                className="cursor-pointer"
                onClick={() => resetList(false)}
                size="sm"
                variant={!archived ? 'secondary' : 'ghost'}
              >
                Текущие
              </Button>
              <Button
                className="cursor-pointer"
                onClick={() => resetList(true)}
                size="sm"
                variant={archived ? 'secondary' : 'ghost'}
              >
                Архивные
              </Button>
            </div>
            <DefectGroupFilters onQueryChange={setQueryInput} query={queryInput} />
          </div>
        </div>
        {!result.data ? (
          result.isError ? (
            <DataLoadError onRetry={() => void result.refetch()} />
          ) : (
            <PendingDefectGroups />
          )
        ) : result.data.items.length === 0 ? (
          <Empty archived={archived} filtered={Boolean(search.q)} item="групп" />
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

type DefectGroupSearch = Readonly<{
  archived?: true
  order?: SortOrder
  page?: number
  pageSize?: PageSize
  q?: string
  sort?: DefectTableSort
}>

type DefectTableSort = (typeof defectTableSorts)[number]

export function validateDefectGroupSearch(search: Record<string, unknown>): DefectGroupSearch {
  return {
    archived: search.archived === true ? true : undefined,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    q: listQuery(search.q),
    sort: listEnum(defectTableSorts, search.sort),
  }
}

function sortingFromSearch(search: DefectGroupSearch, archived: boolean): DataTableSorting {
  return [
    {
      desc: search.order ? search.order === 'desc' : archived,
      id: search.sort ?? (archived ? 'archived_at' : 'code'),
    },
  ]
}

function searchForSorting(sorting: DataTableSorting, archived: boolean) {
  const [current] = sorting
  const sort = listEnum(defectTableSorts, current?.id) ?? (archived ? 'archived_at' : 'code')
  const desc = current?.desc ?? archived
  const defaultSort = archived ? 'archived_at' : 'code'

  return {
    order: desc === archived && sort === defaultSort ? undefined : desc ? 'desc' : 'asc',
    sort: sort === defaultSort ? undefined : sort,
  } as const
}

function sortFor(id: string | undefined, archived: boolean): DefectSort {
  return listEnum(defectTableSorts, id) ?? (archived ? 'archived_at' : 'code')
}

export function Empty({
  archived,
  filtered,
  item,
}: Readonly<{ archived: boolean; filtered: boolean; item: string }>) {
  return (
    <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed">
      <div className="text-center">
        <p className="font-medium">
          {filtered
            ? 'Ничего не найдено'
            : archived
              ? 'Архив пуст'
              : `${item[0].toUpperCase()}${item.slice(1)} пока нет`}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {filtered
            ? 'Попробуйте изменить параметры поиска.'
            : archived
              ? 'Архивированные записи появятся здесь.'
              : 'Добавьте запись, чтобы она появилась в списке.'}
        </p>
      </div>
    </div>
  )
}
