import { Badge } from '@web-app/ui/components/badge'
import { Link } from '@tanstack/react-router'

import { type DataTableColumn } from '@/components/Common/DataTable'
import { batchStatusLabels, type Batch } from '@/features/batches/batches-api'
import { formatDateTime } from '@/lib/date'

import { BatchActionsMenu } from './BatchActionsMenu'

export function createBatchColumns(): readonly DataTableColumn<Batch>[] {
  return [
    {
      accessorKey: 'name',
      cell: ({ row }) => {
        const batch = row.original
        return (
          <div className="flex flex-col gap-1">
            <Link
              className="font-medium hover:underline"
              params={{ batchId: batch.id }}
              to="/admin/production/batches/$batchId"
            >
              {batch.name}
            </Link>
            <span className="text-muted-foreground">
              {batch.productionOrder ? `Заказ: ${batch.productionOrder.name}` : 'Без заказа'}
            </span>
          </div>
        )
      },
      enableSorting: true,
      header: 'Название',
      sortDescFirst: false,
    },
    {
      accessorKey: 'plannedQty',
      cell: ({ row }) => row.original.plannedQty,
      enableSorting: true,
      header: 'План',
      id: 'planned_qty',
      sortDescFirst: true,
    },
    {
      accessorKey: 'status',
      cell: ({ row }) => <BatchStatusBadge status={row.original.status} />,
      enableSorting: true,
      header: 'Статус',
      id: 'status',
      sortDescFirst: true,
    },
    {
      accessorKey: 'createdAt',
      cell: ({ row }) => (
        <span className="whitespace-nowrap text-muted-foreground">
          {formatDateTime(row.original.createdAt)}
        </span>
      ),
      enableSorting: true,
      header: 'Дата',
      id: 'created_at',
      sortDescFirst: true,
    },
    {
      cell: ({ row }) => (
        <div className="flex justify-end">
          <BatchActionsMenu batch={row.original} />
        </div>
      ),
      enableSorting: false,
      header: () => <span className="sr-only">Действия</span>,
      id: 'actions',
    },
  ]
}

function BatchStatusBadge({ status }: Readonly<{ status: Batch['status'] }>) {
  return <Badge variant="secondary">{batchStatusLabels[status]}</Badge>
}
