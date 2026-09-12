import { DataTable, type DataTablePaginationState, type DataTableSorting } from '@/components/Common/DataTable'
import { type Kg } from '@/features/kg/kg-api'

import { kgUnitColumns } from './columns'

const sorting: DataTableSorting = []

export function KgUnitTable({
  items,
  loading,
  onPaginationChange,
  pagination,
  total,
}: Readonly<{
  items: readonly Kg[]
  loading: boolean
  onPaginationChange: (pagination: DataTablePaginationState) => void
  pagination: DataTablePaginationState
  total: number
}>) {
  return (
    <DataTable
      columns={kgUnitColumns}
      data={items}
      loading={loading}
      onPaginationChange={onPaginationChange}
      onSortingChange={() => undefined}
      pagination={pagination}
      showPageSize={false}
      sorting={sorting}
      total={total}
    />
  )
}
