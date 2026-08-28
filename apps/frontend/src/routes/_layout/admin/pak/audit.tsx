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
import { AuditFilter } from '@/components/Common/AuditFilter'
import PendingAudit from '@/components/Pak/Audit/PendingAudit'
import { pakAuditColumns } from '@/components/Pak/Audit/columns'
import { listPakAudit, type PakAuditSort, type SortOrder } from '@/features/paks/paks-api'
import { toExclusiveUtcDateRange, type DatePeriod } from '@/lib/date'

export const Route = createFileRoute('/_layout/admin/pak/audit')({
  component: PakAudit,
  pendingComponent: () => <PendingAudit showPageHeader />,
})

function PakAudit() {
  const [pagination, setPagination] = useState<DataTablePaginationState>({
    pageIndex: 0,
    pageSize: 25 as PageSize,
  })
  const [sorting, setSorting] = useState<DataTableSorting>([{ id: 'created_at', desc: true }])
  const [period, setPeriod] = useState<DatePeriod | null>(null)
  const [current] = sorting
  const sort: PakAuditSort =
    current?.id === 'actor_display_name' || current?.id === 'created_at' ? current.id : 'created_at'
  const order: SortOrder = current?.desc ? 'desc' : 'asc'
  const range = period ? toExclusiveUtcDateRange(period) : undefined
  const {
    data: audit,
    isError,
    isFetching,
    refetch,
  } = useQuery({
    queryFn: () =>
      listPakAudit({
        createdFrom: range?.from,
        createdTo: range?.to,
        order,
        page: pagination.pageIndex + 1,
        pageSize: pagination.pageSize,
        sort,
      }),
    queryKey: ['audit', 'pak', range, order, pagination, sort],
    placeholderData: keepPreviousData,
  })
  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 lg:px-12">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Аудит ПАК</h1>
        <p className="mt-2 text-muted-foreground">
          История действий с программно-аппаратными комплексами.
        </p>
      </div>
      <div className="pt-8">
        <div className="mb-4 flex justify-end">
          <AuditFilter
            onApply={(next) => {
              setPagination((state) => ({ ...state, pageIndex: 0 }))
              setPeriod(next)
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
            columns={pakAuditColumns}
            data={audit.items}
            loading={isFetching}
            onPaginationChange={setPagination}
            onSortingChange={(next) => {
              setPagination((state) => ({ ...state, pageIndex: 0 }))
              setSorting(next)
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
