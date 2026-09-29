import { Button } from '@web-app/ui/components/button'
import { ChevronRightIcon } from 'lucide-react'

import { type DataTableColumn } from '@/components/Common/DataTable'
import { TruncatedText } from '@/components/Common/TruncatedText'
import {
  actionLabel,
  actorLabel,
  targetLabel,
  type AuditEntry,
  type AuditSection,
} from '@/features/audit/audit'
import { formatDateTime } from '@/lib/date'

const maxIdentityDisplayLength = 32

export function createAuditColumns(
  section: AuditSection,
  onOpen: (entry: AuditEntry) => void,
): readonly DataTableColumn<AuditEntry>[] {
  return [
    {
      accessorFn: (row) => row.createdAt,
      cell: ({ row }) => (
        <span className="whitespace-nowrap text-muted-foreground">
          {formatDateTime(row.original.createdAt)}
        </span>
      ),
      enableSorting: true,
      header: 'Время',
      id: 'created_at',
      meta: { widthClassName: 'w-40 xl:w-[15%]' },
      sortDescFirst: true,
    },
    {
      accessorFn: (row) => row.actorLogin,
      cell: ({ row }) => (
        <TruncatedText maxLength={maxIdentityDisplayLength} value={actorLabel(row.original)} />
      ),
      enableSorting: true,
      header: 'Пользователь',
      id: 'actor_login',
      meta: { widthClassName: 'w-40 xl:w-[17%]' },
      sortDescFirst: false,
    },
    {
      accessorKey: 'action',
      cell: ({ row }) => <TruncatedText value={actionLabel(section, row.original.action)} />,
      enableSorting: false,
      header: 'Действие',
      meta: { widthClassName: 'w-[230px] xl:w-[30%]' },
    },
    {
      accessorKey: 'targetLabel',
      cell: ({ row }) => (
        <TruncatedText
          maxLength={maxIdentityDisplayLength}
          value={targetLabel(section, row.original)}
        />
      ),
      enableSorting: false,
      header: section.targetHeader,
      meta: { widthClassName: 'w-40 xl:w-[30%]' },
    },
    {
      cell: ({ row }) => (
        <div className="flex justify-end">
          <Button
            aria-label="Подробности записи"
            onClick={(event) => {
              // The row opens the same entry; one open is enough.
              event.stopPropagation()
              onOpen(row.original)
            }}
            size="icon-sm"
            variant="ghost"
          >
            <ChevronRightIcon />
          </Button>
        </div>
      ),
      enableSorting: false,
      header: '',
      id: 'open',
      meta: { widthClassName: 'w-14' },
    },
  ]
}
