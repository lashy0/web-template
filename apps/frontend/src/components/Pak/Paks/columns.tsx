import { Badge } from '@web-app/ui/components/badge'
import { cn } from '@web-app/ui/lib/utils'

import { type DataTableColumn } from '@/components/Common/DataTable'
import { PakActionsMenu } from '@/components/Pak/Paks/PakActionsMenu'
import { pakKindLabels, pakStatusLabels, type Pak } from '@/features/paks/paks-api'
import { formatDateTime } from '@/lib/date'

export function createPakColumns(archived: boolean): readonly DataTableColumn<Pak>[] {
  const columns: DataTableColumn<Pak>[] = [
    {
      accessorKey: 'code',
      cell: ({ row }) => <span className="font-medium">{row.original.code}</span>,
      enableSorting: true,
      header: 'Код ПАК',
      sortDescFirst: false,
    },
    {
      accessorKey: 'kind',
      cell: ({ row }) => <Badge variant="secondary">{pakKindLabels[row.original.kind]}</Badge>,
      enableSorting: true,
      header: 'Тип',
      sortDescFirst: false,
    },
    {
      accessorFn: (row) => row.lastSeenAt,
      cell: ({ row }) => <LastSeen value={row.original.lastSeenAt} />,
      enableSorting: true,
      header: 'Последняя связь',
      id: 'last_seen_at',
      sortDescFirst: true,
    },
  ]
  if (archived) {
    columns.push({
      accessorFn: (row) => row.archivedAt,
      cell: ({ row }) => <ArchivedAt value={row.original.archivedAt} />,
      enableSorting: true,
      header: 'Архивирован',
      id: 'archived_at',
      sortDescFirst: true,
    })
  } else {
    columns.splice(2, 0, {
      cell: ({ row }) => <PakStatus status={row.original.status} />,
      enableSorting: false,
      header: 'Статус',
      id: 'status',
    })
  }
  columns.push({
    cell: ({ row }) => (
      <div className="flex justify-end">
        <PakActionsMenu pak={row.original} />
      </div>
    ),
    enableSorting: false,
    header: () => <span className="sr-only">Действия</span>,
    id: 'actions',
  })
  return columns
}

function PakStatus({ status }: Readonly<{ status: Pak['status'] }>) {
  return (
    <span className="inline-flex items-center gap-2">
      <span
        aria-hidden="true"
        className={cn('size-2 rounded-full', status === 'active' ? 'bg-green-500' : 'bg-red-500')}
      />
      {pakStatusLabels[status]}
    </span>
  )
}

function LastSeen({ value }: Readonly<{ value: string | null }>) {
  return value ? (
    <span className="whitespace-nowrap text-muted-foreground">{formatDateTime(value)}</span>
  ) : (
    <span className="text-muted-foreground">Ещё не было связи</span>
  )
}

function ArchivedAt({ value }: Readonly<{ value: string | null }>) {
  return value ? (
    <span className="whitespace-nowrap text-muted-foreground">{formatDateTime(value)}</span>
  ) : (
    <span className="text-muted-foreground">—</span>
  )
}
