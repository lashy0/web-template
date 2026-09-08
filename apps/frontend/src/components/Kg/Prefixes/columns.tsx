import { type DataTableColumn } from '@/components/Common/DataTable'
import { KgPrefixActionsMenu } from '@/components/Kg/Prefixes/KgPrefixActionsMenu'
import { formatDevEuiPrefix } from '@/features/kg/kg-prefix-format'
import { type KgPrefix } from '@/features/kg/kg-prefixes-api'
import { formatDateTime } from '@/lib/date'

export function createKgPrefixColumns(archived: boolean): readonly DataTableColumn<KgPrefix>[] {
  const columns: DataTableColumn<KgPrefix>[] = [
    {
      accessorKey: 'name',
      cell: ({ row }) => <span className="font-medium">{row.original.name || '—'}</span>,
      enableSorting: true,
      header: 'Название',
      sortDescFirst: false,
    },
    {
      accessorKey: 'prefix',
      cell: ({ row }) => (
        <code className="font-medium">{formatDevEuiPrefix(row.original.prefix)}</code>
      ),
      enableSorting: true,
      header: 'Префикс',
      sortDescFirst: false,
    },
    {
      accessorKey: 'shortCode',
      cell: ({ row }) => <code>{row.original.shortCode}</code>,
      enableSorting: true,
      header: 'Короткий код',
      id: 'short_code',
      sortDescFirst: false,
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
          '—'
        ),
      enableSorting: true,
      header: 'Архивирован',
      id: 'archived_at',
      sortDescFirst: true,
    })
  } else {
    columns.push({
      accessorKey: 'batchCount',
      cell: ({ row }) => row.original.batchCount,
      enableSorting: false,
      header: 'В партиях',
    })
  }
  columns.push({
    cell: ({ row }) => (
      <div className="flex justify-end">
        <KgPrefixActionsMenu prefix={row.original} />
      </div>
    ),
    enableSorting: false,
    header: () => <span className="sr-only">Действия</span>,
    id: 'actions',
  })
  return columns
}
