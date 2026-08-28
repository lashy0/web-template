import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'

import { Button } from '@web-app/ui/components/button'

import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import { AddPak } from '@/components/Pak/Paks/AddPak'
import { PakFilters } from '@/components/Pak/Paks/PakFilters'
import PendingPaks from '@/components/Pak/Paks/PendingPaks'
import { createPakColumns } from '@/components/Pak/Paks/columns'
import { listPaks, type PakKind, type PakSort, type SortOrder } from '@/features/paks/paks-api'

export const Route = createFileRoute('/_layout/admin/pak/paks')({
  component: Paks,
  pendingComponent: () => <PendingPaks showPageHeader />,
})

type PaksQuery = Readonly<{
  active?: boolean
  archived: boolean
  kind?: PakKind
  order: SortOrder
  page: number
  pageSize: number
  query?: string
  sort: PakSort
}>
type StatusFilter = 'active' | 'all' | 'inactive'

function defaultSorting(archived: boolean): DataTableSorting {
  return [{ id: archived ? 'archived_at' : 'code', desc: archived }]
}
function sortParams(sorting: DataTableSorting): Readonly<{ order: SortOrder; sort: PakSort }> {
  const [current] = sorting
  if (
    current?.id === 'archived_at' ||
    current?.id === 'code' ||
    current?.id === 'kind' ||
    current?.id === 'last_seen_at'
  )
    return { order: current.desc ? 'desc' : 'asc', sort: current.id }
  return { order: 'asc', sort: 'code' }
}
function queryOptions(params: PaksQuery) {
  return { queryFn: () => listPaks(params), queryKey: ['paks', params] }
}

function Paks() {
  const [pagination, setPagination] = useState<DataTablePaginationState>({
    pageIndex: 0,
    pageSize: 25 as PageSize,
  })
  const [archived, setArchived] = useState(false)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [kind, setKind] = useState<PakKind | 'all'>('all')
  const [status, setStatus] = useState<StatusFilter>('all')
  const [sorting, setSorting] = useState<DataTableSorting>(() => defaultSorting(false))
  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setPagination((current) => ({ ...current, pageIndex: 0 }))
      setDebouncedQuery(query.trim())
    }, 300)
    return () => window.clearTimeout(timeout)
  }, [query])
  const paksQuery: PaksQuery = {
    active: !archived && status !== 'all' ? status === 'active' : undefined,
    archived,
    kind: kind !== 'all' ? kind : undefined,
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    query: debouncedQuery || undefined,
    ...sortParams(sorting),
  }
  const columns = useMemo(() => createPakColumns(archived), [archived])
  const {
    data: paks,
    isError,
    isFetching,
    refetch,
  } = useQuery({ ...queryOptions(paksQuery), placeholderData: keepPreviousData })
  const hasFilters = debouncedQuery !== '' || kind !== 'all' || (!archived && status !== 'all')
  const resetList = (nextArchived: boolean) => {
    setPagination((current) => ({ ...current, pageIndex: 0 }))
    setArchived(nextArchived)
    setSorting(defaultSorting(nextArchived))
  }
  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 lg:px-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">ПАК</h1>
          <p className="mt-2 text-muted-foreground">
            Управление программно-аппаратными комплексами.
          </p>
        </div>
        <AddPak />
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
            <PakFilters
              archived={archived}
              kind={kind}
              onKindChange={(value) => {
                setPagination((current) => ({ ...current, pageIndex: 0 }))
                setKind(value)
              }}
              onQueryChange={(value) => {
                setPagination((current) => ({ ...current, pageIndex: 0 }))
                setQuery(value)
              }}
              onStatusChange={(value) => {
                setPagination((current) => ({ ...current, pageIndex: 0 }))
                setStatus(value)
              }}
              query={query}
              status={status}
            />
          </div>
        </div>
        {!paks ? (
          isError ? (
            <DataLoadError onRetry={() => void refetch()} />
          ) : (
            <PendingPaks />
          )
        ) : paks.items.length === 0 ? (
          <EmptyState archived={archived} hasFilters={hasFilters} />
        ) : (
          <DataTable
            columns={columns}
            data={paks.items}
            loading={isFetching}
            onPaginationChange={setPagination}
            onSortingChange={(nextSorting) => {
              setPagination((current) => ({ ...current, pageIndex: 0 }))
              setSorting(nextSorting)
            }}
            pagination={pagination}
            sorting={sorting}
            total={paks.total}
          />
        )}
      </div>
    </section>
  )
}

function EmptyState({
  archived,
  hasFilters,
}: Readonly<{ archived: boolean; hasFilters: boolean }>) {
  return (
    <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed">
      <div className="text-center">
        <p className="font-medium">
          {hasFilters ? 'Ничего не найдено' : archived ? 'Архив пуст' : 'ПАК пока нет'}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {hasFilters
            ? 'Попробуйте изменить параметры поиска.'
            : archived
              ? 'Архивированные ПАК появятся здесь.'
              : 'Добавьте ПАК, чтобы он появился в списке.'}
        </p>
      </div>
    </div>
  )
}
