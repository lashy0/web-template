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

export const Route = createFileRoute('/_layout/admin/defects/groups')({
  component: DefectGroups,
  pendingComponent: PendingDefectGroups,
})

function DefectGroups() {
  const [pagination, setPagination] = useState<DataTablePaginationState>({
    pageIndex: 0,
    pageSize: 25 as PageSize,
  })
  const [archived, setArchived] = useState(false)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [sorting, setSorting] = useState<DataTableSorting>([{ id: 'code', desc: false }])
  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setPagination((value) => ({ ...value, pageIndex: 0 }))
      setDebouncedQuery(query.trim())
    }, 300)
    return () => window.clearTimeout(timeout)
  }, [query])
  const params = {
    archived,
    order: sorting[0]?.desc ? 'desc' : ('asc' as SortOrder),
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    query: debouncedQuery || undefined,
    sort: sortFor(sorting[0]?.id, archived),
  }
  const result = useQuery({
    queryFn: () => listDefectGroups(params),
    queryKey: ['defects', 'groups', params],
    placeholderData: keepPreviousData,
  })
  const columns = useMemo(() => createDefectGroupColumns(archived), [archived])
  const resetList = (nextArchived: boolean) => {
    setArchived(nextArchived)
    setPagination((value) => ({ ...value, pageIndex: 0 }))
    setSorting([{ id: nextArchived ? 'archived_at' : 'code', desc: nextArchived }])
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
            <DefectGroupFilters onQueryChange={setQuery} query={query} />
          </div>
        </div>
        {!result.data ? (
          result.isError ? (
            <DataLoadError onRetry={() => void result.refetch()} />
          ) : (
            <PendingDefectGroups />
          )
        ) : result.data.items.length === 0 ? (
          <Empty archived={archived} filtered={Boolean(debouncedQuery)} item="групп" />
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
