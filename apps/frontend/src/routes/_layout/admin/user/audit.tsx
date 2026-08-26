import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'

import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import { AuditFilter } from '@/components/User/Audit/AuditFilter'
import { auditColumns } from '@/components/User/Audit/columns'
import PendingAudit from '@/components/User/Audit/PendingAudit'
import { listUserAudit, type AuditSort, type SortOrder } from '@/features/users/users-api'
import { toExclusiveUtcDateRange, type DatePeriod } from '@/lib/date'

export const Route = createFileRoute('/_layout/admin/user/audit')({
  component: Audit,
})

type AuditQuery = Readonly<{
  createdFrom?: string
  createdTo?: string
  order: SortOrder
  page: number
  pageSize: number
  sort: AuditSort
}>

function auditSortParams(
  sorting: DataTableSorting,
): Readonly<{ order: SortOrder; sort: AuditSort }> {
  const [current] = sorting
  if (current?.id === 'actor_display_name' || current?.id === 'created_at') {
    return { order: current.desc ? 'desc' : 'asc', sort: current.id }
  }
  return { order: 'desc', sort: 'created_at' }
}

function getUserAuditQueryOptions(params: AuditQuery) {
  return {
    queryFn: () => listUserAudit(params),
    queryKey: ['audit', 'user', params],
  }
}

export function Audit() {
  const [pagination, setPagination] = useState<DataTablePaginationState>({
    pageIndex: 0,
    pageSize: 25 as PageSize,
  })
  const [sorting, setSorting] = useState<DataTableSorting>([{ id: 'created_at', desc: true }])
  const [period, setPeriod] = useState<DatePeriod | null>(null)
  const auditQuery = {
    ...(period ? toAuditPeriodQuery(period) : {}),
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
    ...auditSortParams(sorting),
  }
  const {
    data: audit,
    isError,
    isFetching,
    refetch,
  } = useQuery({
    ...getUserAuditQueryOptions(auditQuery),
    placeholderData: keepPreviousData,
  })

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 lg:px-12">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Аудит пользователей</h1>
        <p className="mt-2 text-muted-foreground">История действий с учётными записями.</p>
      </div>
      <div className="pt-8">
        <div className="mb-4 flex justify-end">
          <AuditFilter
            onApply={(nextPeriod) => {
              setPagination((current) => ({ ...current, pageIndex: 0 }))
              setPeriod(nextPeriod)
            }}
            value={period}
          />
        </div>
        {!audit ? (
          isError ? (
            <DataLoadError onRetry={() => void refetch()} />
          ) : (
            <PendingAudit />
          )
        ) : audit.items.length === 0 && period ? (
          <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed">
            <div className="text-center">
              <p className="font-medium">Ничего не найдено</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Попробуйте изменить параметры поиска.
              </p>
            </div>
          </div>
        ) : (
          <DataTable
            columns={auditColumns}
            data={audit.items}
            loading={isFetching}
            onPaginationChange={setPagination}
            onSortingChange={(nextSorting) => {
              setPagination((current) => ({ ...current, pageIndex: 0 }))
              setSorting(nextSorting)
            }}
            pagination={pagination}
            sorting={sorting}
            total={audit.total}
          />
        )}
      </div>
    </section>
  )
}

function toAuditPeriodQuery(
  period: DatePeriod,
): Readonly<{ createdFrom: string; createdTo: string }> {
  const range = toExclusiveUtcDateRange(period)

  return {
    createdFrom: range.from,
    createdTo: range.to,
  }
}
