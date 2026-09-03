import { Badge } from '@web-app/ui/components/badge'
import { Tooltip, TooltipContent, TooltipTrigger } from '@web-app/ui/components/tooltip'

import { type DataTableColumn } from '@/components/Common/DataTable'
import { DefectTypeActionsMenu } from '@/components/Defects/Types/DefectTypeActionsMenu'
import { type DefectType } from '@/features/defects/defects-api'
import { formatDateTime } from '@/lib/date'

import { HoverCard, HoverCardContent, HoverCardTrigger } from '@web-app/ui/components/hover-card'

export function createDefectTypeColumns(archived: boolean): readonly DataTableColumn<DefectType>[] {
  const columns: DataTableColumn<DefectType>[] = [
    {
      accessorKey: 'code',
      cell: ({ row }) => <span className="font-medium">{row.original.code}</span>,
      enableSorting: true,
      header: 'Код',
      sortDescFirst: false,
    },
    {
      accessorKey: 'name',
      cell: ({ row }) => (
        <HoverCard>
          <HoverCardTrigger
            aria-label={`Показать описание типа «${row.original.name}»`}
            className="cursor-help rounded-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring"
            delay={250}
            render={<button type="button" />}
          >
            {row.original.name}
          </HoverCardTrigger>
          <HoverCardContent className="max-w-[calc(100vw-2rem)] overflow-hidden">
            <p className="font-medium">Описание</p>
            <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground [overflow-wrap:anywhere]">
              {row.original.description}
            </p>
          </HoverCardContent>
        </HoverCard>
      ),
      enableSorting: true,
      header: 'Название',
      sortDescFirst: false,
    },
    {
      cell: ({ row }) => <DefectTypeGroup group={row.original.group} />,
      enableSorting: false,
      header: 'Группа',
      id: 'group',
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
  }
  columns.push({
    cell: ({ row }) => (
      <div className="flex justify-end">
        <DefectTypeActionsMenu type={row.original} />
      </div>
    ),
    enableSorting: false,
    header: () => <span className="sr-only">Действия</span>,
    id: 'actions',
  })
  return columns
}

function DefectTypeGroup({ group }: Readonly<{ group: DefectType['group'] }>) {
  return (
    <Tooltip>
      <TooltipTrigger render={<Badge className="cursor-default" variant="secondary" />}>
        {group.code}
      </TooltipTrigger>
      <TooltipContent>{group.name}</TooltipContent>
    </Tooltip>
  )
}
