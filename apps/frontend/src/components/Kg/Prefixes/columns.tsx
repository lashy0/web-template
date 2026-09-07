import { type DataTableColumn } from '@/components/Common/DataTable'
import { KgPrefixActionsMenu } from '@/components/Kg/Prefixes/KgPrefixActionsMenu'
import { formatDevEuiPrefix } from '@/features/kg/kg-prefix-format'
import { type KgPrefix } from '@/features/kg/kg-prefixes-api'
import { formatDateTime } from '@/lib/date'

export const kgPrefixColumns: readonly DataTableColumn<KgPrefix>[] = [
  {
    accessorKey: 'name',
    cell: ({ row }) => <span className="font-medium">{row.original.name || '—'}</span>,
    enableSorting: false,
    header: 'Название',
  },
  {
    accessorKey: 'prefix',
    cell: ({ row }) => (
      <code className="font-medium">{formatDevEuiPrefix(row.original.prefix)}</code>
    ),
    enableSorting: false,
    header: 'Префикс',
  },
  {
    accessorKey: 'shortCode',
    cell: ({ row }) => <code>{row.original.shortCode}</code>,
    enableSorting: false,
    header: 'Короткий код',
  },
  {
    accessorKey: 'createdAt',
    cell: ({ row }) => (
      <span className="whitespace-nowrap text-muted-foreground">
        {formatDateTime(row.original.createdAt)}
      </span>
    ),
    enableSorting: false,
    header: 'Дата создания',
  },
  {
    cell: ({ row }) => (
      <div className="flex justify-end">
        <KgPrefixActionsMenu prefix={row.original} />
      </div>
    ),
    enableSorting: false,
    header: () => <span className="sr-only">Действия</span>,
    id: 'actions',
  },
]
