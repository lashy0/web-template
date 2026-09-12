import { Badge } from '@web-app/ui/components/badge'

import { type DataTableColumn } from '@/components/Common/DataTable'
import { formatDevEui } from '@/features/kg/kg-prefix-format'
import { kgStatusLabels, type Kg } from '@/features/kg/kg-api'
import { formatDateTime } from '@/lib/date'

export const kgUnitColumns: readonly DataTableColumn<Kg>[] = [
  {
    accessorKey: 'devEui',
    cell: ({ row }) => <code>{formatDevEui(row.original.devEui)}</code>,
    enableSorting: false,
    header: () => <span className="normal-case tracking-normal">DevEUI</span>,
  },
  {
    accessorKey: 'status',
    cell: ({ row }) => <Badge variant="secondary">{kgStatusLabels[row.original.status]}</Badge>,
    enableSorting: false,
    header: () => <span className="normal-case tracking-normal">Статус</span>,
  },
  {
    accessorKey: 'firmwareVersion',
    cell: ({ row }) => row.original.firmwareVersion ?? '—',
    enableSorting: false,
    header: () => <span className="normal-case tracking-normal">Прошивка</span>,
  },
  {
    accessorKey: 'lastVerificationAt',
    cell: ({ row }) =>
      row.original.lastVerificationAt ? formatDateTime(row.original.lastVerificationAt) : '—',
    enableSorting: false,
    header: () => <span className="normal-case tracking-normal">Последняя ОТК</span>,
  },
]
