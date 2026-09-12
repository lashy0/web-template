import { Badge } from '@web-app/ui/components/badge'

import { type DataTableColumn } from '@/components/Common/DataTable'
import { formatDevEui } from '@/features/kg/kg-prefix-format'
import { kgCurrentStateLabels, type Kg } from '@/features/kg/kg-api'
import { formatDateTime } from '@/lib/date'

export const kgUnitColumns: readonly DataTableColumn<Kg>[] = [
  {
    accessorKey: 'devEui',
    cell: ({ row }) => (
      <code>{formatDevEui(row.original.devEui)}</code>
    ),
    enableSorting: false,
    header: 'DevEUI',
  },
  {
    accessorKey: 'currentState',
    cell: ({ row }) => (
      <Badge variant="secondary">{kgCurrentStateLabels[row.original.currentState]}</Badge>
    ),
    enableSorting: false,
    header: 'Текущее состояние',
  },
  {
    accessorKey: 'firmwareVersion',
    cell: ({ row }) => row.original.firmwareVersion ?? '—',
    enableSorting: false,
    header: 'Прошивка',
  },
  {
    accessorKey: 'lastVerificationAt',
    cell: ({ row }) =>
      row.original.lastVerificationAt ? formatDateTime(row.original.lastVerificationAt) : '—',
    enableSorting: false,
    header: 'Последняя ОТК',
  },
]
