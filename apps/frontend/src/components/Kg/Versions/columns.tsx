import { type DataTableColumn } from '@/components/Common/DataTable'
import { KgVersionActionsMenu } from '@/components/Kg/Versions/KgVersionActionsMenu'
import { type KgVersion } from '@/features/kg/kg-versions-api'
import { formatDateTime } from '@/lib/date'

export function createKgVersionColumns(archived: boolean): readonly DataTableColumn<KgVersion>[] {
  const columns: DataTableColumn<KgVersion>[] = [
    {
      accessorKey: 'code',
      cell: ({ row }) => <span className="font-medium">{row.original.code}</span>,
      enableSorting: true,
      header: 'Код',
      sortDescFirst: false,
    },
    {
      accessorKey: 'name',
      cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
      enableSorting: true,
      header: 'Название',
      sortDescFirst: false,
    },
  ]
  if (!archived) {
    columns.push({
      accessorKey: 'batchCount',
      cell: ({ row }) => row.original.batchCount,
      enableSorting: false,
      header: 'В партиях',
    })
  } else {
    columns.push({
      accessorFn: (row) => row.archivedAt,
      cell: ({ row }) =>
        row.original.archivedAt ? (
          <span className="whitespace-nowrap text-muted-foreground">
            {formatDateTime(row.original.archivedAt)}
          </span>
        ) : (
          '—'
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
        <KgVersionActionsMenu version={row.original} />
      </div>
    ),
    enableSorting: false,
    header: () => <span className="sr-only">Действия</span>,
    id: 'actions',
  })
  return columns
}
