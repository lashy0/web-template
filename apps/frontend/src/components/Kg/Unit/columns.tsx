import { Badge } from '@web-app/ui/components/badge'

import { type DataTableColumn } from '@/components/Common/DataTable'
import { formatDevEui } from '@/features/kg/kg-prefix-format'
import { kgOtkStatusLabels, kgStateLabels, type KgUnit } from '@/features/kg/kg-api'
import { formatDateTime } from '@/lib/date'

export const kgUnitColumns: readonly DataTableColumn<KgUnit>[] = [
  {
    accessorKey: 'devEui',
    cell: ({ row }) => <code>{formatDevEui(row.original.devEui)}</code>,
    enableSorting: false,
    header: 'DevEUI',
  },
  {
    accessorKey: 'shortId',
    cell: ({ row }) => <code>{row.original.shortId}</code>,
    enableSorting: false,
    header: 'Короткий ID',
  },
  {
    accessorKey: 'state',
    cell: ({ row }) => <Badge variant="secondary">{kgStateLabels[row.original.state]}</Badge>,
    enableSorting: false,
    header: 'Состояние',
  },
  {
    accessorKey: 'otkStatus',
    cell: ({ row }) => kgOtkStatusLabels[row.original.otkStatus],
    enableSorting: false,
    header: 'ОТК',
  },
  {
    accessorKey: 'lastVerificationAt',
    cell: ({ row }) =>
      row.original.lastVerificationAt ? formatDateTime(row.original.lastVerificationAt) : '—',
    enableSorting: false,
    header: 'Последняя ОТК',
  },
  {
    accessorKey: 'packedAt',
    cell: ({ row }) => (row.original.packedAt ? formatDateTime(row.original.packedAt) : '—'),
    enableSorting: false,
    header: 'Упакована',
  },
]
