import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'

import { Tabs, TabsList, TabsTrigger } from '@web-app/ui/components/tabs'

import { AddKgPrefix } from '@/components/Kg/Prefixes/AddKgPrefix'
import { kgPrefixColumns } from '@/components/Kg/Prefixes/columns'
import { KgPrefixFilters } from '@/components/Kg/Prefixes/KgPrefixFilters'
import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type PageSize,
} from '@/components/Common/DataTable'
import { listKgPrefixes } from '@/features/kg/kg-prefixes-api'

export const Route = createFileRoute('/_layout/admin/kg/prefixes')({
  component: KgPrefixes,
})

function KgPrefixes() {
  const [pagination, setPagination] = useState<DataTablePaginationState>({
    pageIndex: 0,
    pageSize: 25 as PageSize,
  })
  const [archived, setArchived] = useState(false)
  const [queryInput, setQueryInput] = useState('')
  const [query, setQuery] = useState('')
  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setQuery(queryInput.trim())
      setPagination((current) => ({ ...current, pageIndex: 0 }))
    }, 300)
    return () => window.clearTimeout(timeout)
  }, [queryInput])
  const params = {
    archived,
    order: archived ? ('desc' as const) : ('asc' as const),
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    query,
    sort: archived ? ('archived_at' as const) : ('prefix' as const),
  }
  const result = useQuery({
    queryFn: () => listKgPrefixes(params),
    queryKey: ['kg', 'prefixes', params],
    placeholderData: keepPreviousData,
  })
  const prefixes = result.data?.items ?? []

  return (
    <section className="mx-auto w-full max-w-[82.5rem] px-4 py-8 sm:px-8 lg:px-12">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">DevEUI-префиксы</h1>
        <p className="mt-2 text-muted-foreground">Управление префиксами DevEUI для КГ.</p>
      </div>
      <Tabs
        className="mt-8"
        onValueChange={(value) => {
          setArchived(value === 'archived')
          setPagination((current) => ({ ...current, pageIndex: 0 }))
        }}
        value={archived ? 'archived' : 'current'}
      >
        <TabsList>
          <TabsTrigger value="current">Текущие</TabsTrigger>
          <TabsTrigger value="archived">Архивные</TabsTrigger>
        </TabsList>
      </Tabs>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <KgPrefixFilters onQueryChange={setQueryInput} query={queryInput} />
        <AddKgPrefix />
      </div>
      <div className="mt-4">
        {!result.data ? (
          result.isError ? (
            <DataLoadError onRetry={() => void result.refetch()} />
          ) : (
            <PendingKgPrefixes />
          )
        ) : prefixes.length === 0 ? (
          <EmptyState />
        ) : (
          <DataTable
            columns={kgPrefixColumns}
            data={prefixes}
            loading={result.isFetching}
            onPaginationChange={setPagination}
            onSortingChange={() => undefined}
            pagination={pagination}
            sorting={[]}
            total={result.data?.total ?? 0}
          />
        )}
      </div>
    </section>
  )
}

function EmptyState() {
  return (
    <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed">
      <div className="text-center">
        <p className="font-medium">Префиксов пока нет</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Добавьте префикс, чтобы он появился в списке.
        </p>
      </div>
    </div>
  )
}

function PendingKgPrefixes() {
  return (
    <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed">
      <p className="text-sm text-muted-foreground">Загрузка префиксов…</p>
    </div>
  )
}
