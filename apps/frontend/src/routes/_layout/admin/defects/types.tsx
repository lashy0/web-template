import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute, useLocation } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'

import { Button } from '@web-app/ui/components/button'

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
import {
  listDefectGroups,
  listDefectTypes,
  type DefectSort,
  type SortOrder,
} from '@/features/defects/defects-api'

export const Route = createFileRoute('/_layout/admin/defects/types')({
  component: DefectTypes,
  pendingComponent: PendingDefectTypes,
})

function DefectTypes() {
  const navigationGroupId = useLocation({
    select: (location) => groupIdFrom(location.state),
  })
  const navigationTypesArchived = useLocation({
    select: (location) => typesArchivedFrom(location.state),
  })
  const [pagination, setPagination] = useState<DataTablePaginationState>({
    pageIndex: 0,
    pageSize: 25 as PageSize,
  })
  const [archived, setArchived] = useState(navigationTypesArchived)
  const [groupId, setGroupId] = useState(navigationGroupId)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [sorting, setSorting] = useState<DataTableSorting>(() =>
    defaultSorting(navigationTypesArchived),
  )
  const groupsQuery = useQuery({
    queryFn: () => listDefectGroups({ page: 1, pageSize: 100 }),
    queryKey: ['defects', 'groups', 'filter'],
  })

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setPagination((value) => ({ ...value, pageIndex: 0 }))
      setDebouncedQuery(query.trim())
    }, 300)
    return () => window.clearTimeout(timeout)
  }, [query])

  useEffect(() => {
    setArchived(navigationTypesArchived)
    setGroupId(navigationGroupId)
    setPagination((value) => ({ ...value, pageIndex: 0 }))
    setSorting(defaultSorting(navigationTypesArchived))
  }, [navigationGroupId, navigationTypesArchived])

  const params = {
    archived,
    groupId,
    order: sorting[0]?.desc ? 'desc' : ('asc' as SortOrder),
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    query: debouncedQuery || undefined,
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
    setPagination((value) => ({ ...value, pageIndex: 0 }))
    setSorting([{ id: nextArchived ? 'archived_at' : 'code', desc: nextArchived }])
  }
  const changeGroup = (value: string) => {
    setPagination((state) => ({ ...state, pageIndex: 0 }))
    setGroupId(value === 'all' ? undefined : value)
  }
  const groups = groupsQuery.data?.items ?? []

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
            <DefectTypeFilters
              groupId={groupId}
              groups={groups}
              onGroupChange={changeGroup}
              onQueryChange={setQuery}
              query={query}
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
          <Empty archived={archived} filtered={Boolean(debouncedQuery || groupId)} item="типов" />
        ) : (
          <DataTable
            columns={columns}
            data={result.data.items}
            loading={result.isFetching}
            onPaginationChange={setPagination}
            onSortingChange={(next) => {
              setPagination((value) => ({ ...value, pageIndex: 0 }))
              setSorting(next)
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
  return id === 'code' || id === 'name' || id === 'archived_at'
    ? id
    : archived
      ? 'archived_at'
      : 'code'
}

function defaultSorting(archived: boolean): DataTableSorting {
  return [{ id: archived ? 'archived_at' : 'code', desc: archived }]
}

function groupIdFrom(state: unknown): string | undefined {
  if (typeof state !== 'object' || state === null || !('defectGroupId' in state)) return undefined
  return typeof state.defectGroupId === 'string' ? state.defectGroupId : undefined
}

function typesArchivedFrom(state: unknown): boolean {
  if (typeof state !== 'object' || state === null || !('defectTypesArchived' in state)) return false
  return state.defectTypesArchived === true
}
