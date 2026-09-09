import { type DataTableColumn } from '@/components/Common/DataTable'
import { type ProductionOrder } from '@/features/production-orders/production-order-api'
import { formatDateTime } from '@/lib/date'

import { ProductionOrderActionsMenu } from './ProductionOrderActionsMenu'

export function createProductionOrderColumns(
  archived: boolean,
): readonly DataTableColumn<ProductionOrder>[] {
  const columns: DataTableColumn<ProductionOrder>[] = [
    {
      accessorKey: 'name',
      cell: ({ row }) => (
        <span className="block max-w-80 truncate font-medium">{row.original.name}</span>
      ),
      enableSorting: true,
      header: 'Название',
      sortDescFirst: false,
    },
    {
      accessorKey: 'batchesCount',
      cell: ({ row }) => row.original.batchesCount,
      enableSorting: true,
      header: 'Партий',
      id: 'batches_count',
      sortDescFirst: true,
    },
    {
      accessorKey: 'totalPlannedQty',
      cell: ({ row }) => row.original.totalPlannedQty,
      enableSorting: true,
      header: 'Общий план',
      id: 'total_planned_qty',
      sortDescFirst: true,
    },
  ]

  if (archived) {
    columns.push({
      accessorFn: (row) => row.archivedAt,
      cell: ({ row }) =>
        row.original.archivedAt ? (
          <span className="whitespace-nowrap text-muted-foreground">
            {formatDateTime(row.original.archivedAt)}
          </span>
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
      enableSorting: true,
      header: 'Архивирован',
      id: 'archived_at',
      sortDescFirst: true,
    })
  }

  columns.push({
    cell: ({ row }) => (
      <div className="flex justify-end">
        <ProductionOrderActionsMenu order={row.original} />
      </div>
    ),
    enableSorting: false,
    header: () => <span className="sr-only">Действия</span>,
    id: 'actions',
  })
  return columns
}
