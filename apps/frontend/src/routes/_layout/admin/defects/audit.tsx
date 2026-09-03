import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'

import { AuditFilter } from '@/components/Common/AuditFilter'
import { DataLoadError } from '@/components/Common/DataLoadError'
import {
  DataTable,
  type DataTablePaginationState,
  type DataTableSorting,
  type PageSize,
} from '@/components/Common/DataTable'
import PendingAudit from '@/components/Defects/Audit/PendingAudit'
import { defectAuditColumns } from '@/components/Defects/Audit/columns'
import {
  listDefectAudit,
  type DefectAuditSort,
  type SortOrder,
} from '@/features/defects/defects-api'
import { toExclusiveUtcDateRange, type DatePeriod } from '@/lib/date'

export const Route = createFileRoute('/_layout/admin/defects/audit')({
  component: DefectAudit,
  pendingComponent: () => <PendingAudit showPageHeader />,
})

function DefectAudit() {
  const [pagination, setPagination] = useState<DataTablePaginationState>({
    pageIndex: 0,
    pageSize: 25 as PageSize,
  })
  const [sorting, setSorting] = useState<DataTableSorting>([{ id: 'created_at', desc: true }])
  const [period, setPeriod] = useState<DatePeriod | null>(null)
  const [current] = sorting
  const sort: DefectAuditSort =
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
      listDefectAudit({
        createdFrom: range?.from,
        createdTo: range?.to,
        order,
        page: pagination.pageIndex + 1,
        pageSize: pagination.pageSize,
        sort,
      }),
    queryKey: ['audit', 'defects', range, order, pagination, sort],
    placeholderData: keepPreviousData,
  })

  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 lg:px-12">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Аудит дефектов</h1>
        <p className="mt-2 text-muted-foreground">История действий с группами и типами дефектов.</p>
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
            columns={defectAuditColumns}
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
