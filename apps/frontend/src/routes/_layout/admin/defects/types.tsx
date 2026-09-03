import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'

import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

import { AddDefectType } from '@/components/Defects/Types/AddDefectType'
import { DefectTypeFilters } from '@/components/Defects/Types/DefectTypeFilters'
import PendingDefectTypes from '@/components/Defects/Types/PendingDefectTypes'
import { createDefectTypeColumns } from '@/components/Defects/Types/columns'
import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import { Empty } from '@/routes/_layout/admin/defects/groups'
import { listDefectTypes, type DefectSort, type SortOrder } from '@/features/defects/defects-api'
import { listEnum, listOrder, listPage, listPageSize, listQuery } from '@/lib/list-search'
import { z } from 'zod'

const defectTableSorts = ['archived_at', 'code', 'name'] as const
const groupIdSchema = z.uuid()

export const Route = createFileRoute('/_layout/admin/defects/types')({
  validateSearch: validateDefectTypeSearch,
  component: DefectTypes,
  pendingComponent: PendingDefectTypes,
})

function DefectTypes() {
  const search = Route.useSearch()
  const navigate = Route.useNavigate()
  const archived = search.archived ?? false
  const groupId = search.group
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
  const setGroupId = (nextGroupId: string | undefined) => {
    navigate({ search: (previous) => ({ ...previous, group: nextGroupId, page: undefined }) })
  }

  const params = {
    archived,
    groupId,
    order: sorting[0]?.desc ? 'desc' : ('asc' as SortOrder),
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    query: search.q,
    sort: sortFor(sorting[0]?.id, archived),
  }
  const result = useQuery({
    queryFn: () => listDefectTypes(params),
    queryKey: ['defects', 'types', params],
    placeholderData: keepPreviousData,
  })
  const columns = useMemo(() => createDefectTypeColumns(archived), [archived])
  const resetList = (nextArchived: boolean) => {
    setArchived(nextArchived)
  }
  const changeGroup = (value: string) => {
    setGroupId(value === 'all' ? undefined : value)
  }

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Типы дефектов</h1>
          <p className="mt-2 text-muted-foreground">
            Управление типами дефектов и действиями инженера.
          </p>
        </div>
        <AddDefectType groupId={groupId} />
      </div>
      <div className="pt-8">
        <div className="@container mb-4">
          <div className="flex flex-col gap-3 @[56rem]:flex-row @[56rem]:items-center @[56rem]:justify-between">
            <Tabs
              className="shrink-0"
              onValueChange={(value) => resetList(value === 'archived')}
              value={archived ? 'archived' : 'current'}
            >
              <TabsList>
                <TabsTrigger value="current">Текущие</TabsTrigger>
                <TabsTrigger value="archived">Архивные</TabsTrigger>
              </TabsList>
            </Tabs>
            <DefectTypeFilters
              groupId={groupId}
              onGroupChange={changeGroup}
              onQueryChange={setQueryInput}
              query={queryInput}
            />
          </div>
        </div>
        {!result.data ? (
          result.isError ? (
            <DataLoadError onRetry={() => void result.refetch()} />
          ) : (
            <PendingDefectTypes />
          )
        ) : result.data.items.length === 0 ? (
          <Empty archived={archived} filtered={Boolean(search.q || groupId)} item="типов" />
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

function sortFor(id: string | undefined, archived: boolean): DefectSort {
  return listEnum(defectTableSorts, id) ?? (archived ? 'archived_at' : 'code')
}

export function validateDefectTypeSearch(search: Record<string, unknown>): DefectTypeSearch {
  return {
    archived: search.archived === true ? true : undefined,
    group: groupIdSchema.safeParse(search.group).data,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    q: listQuery(search.q),
    sort: listEnum(defectTableSorts, search.sort),
  }
}

type DefectTypeSearch = Readonly<{
  archived?: true
  group?: string
  order?: SortOrder
  page?: number
  pageSize?: PageSize
  q?: string
  sort?: DefectTableSort
}>

type DefectTableSort = (typeof defectTableSorts)[number]

function sortingFromSearch(search: DefectTypeSearch, archived: boolean): DataTableSorting {
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
