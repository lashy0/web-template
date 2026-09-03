import { Link } from '@tanstack/react-router'

import { HoverCard, HoverCardContent, HoverCardTrigger } from '@web-app/ui/components/hover-card'

import { type DataTableColumn } from '@/components/Common/DataTable'
import { DefectGroupActionsMenu } from '@/components/Defects/Groups/DefectGroupActionsMenu'
import { type DefectGroup } from '@/features/defects/defects-api'
import { formatDateTime } from '@/lib/date'

export function createDefectGroupColumns(
  archived: boolean,
): readonly DataTableColumn<DefectGroup>[] {
  const columns: DataTableColumn<DefectGroup>[] = [
    {
      accessorKey: 'code',
      cell: ({ row }) => <span className="font-medium">{row.original.code}</span>,
      enableSorting: true,
      header: 'Код',
      sortDescFirst: false,
    },
    {
      accessorKey: 'name',
      cell: ({ row }) => <DefectGroupName group={row.original} />,
      enableSorting: true,
      header: 'Название',
      sortDescFirst: false,
    },
    {
      cell: ({ row }) => (
        <Link
          className="text-sm text-primary underline-offset-4 hover:underline"
          search={{
            archived:
              row.original.activeTypesCount === 0 && row.original.typesCount > 0 ? true : undefined,
            group: row.original.id,
          }}
          to="/admin/defects/types"
        >
          Типы группы
        </Link>
      ),
      enableSorting: false,
      header: 'Типы',
      id: 'types',
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
        <DefectGroupActionsMenu group={row.original} />
      </div>
    ),
    enableSorting: false,
    header: () => <span className="sr-only">Действия</span>,
    id: 'actions',
  })
  return columns
}

function DefectGroupName({ group }: Readonly<{ group: DefectGroup }>) {
  if (!group.description) return <span className="font-medium">{group.name}</span>
  return (
    <HoverCard>
      <HoverCardTrigger
        aria-label={`Показать описание группы «${group.name}»`}
        className="cursor-help rounded-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring"
        delay={250}
        render={<button type="button" />}
      >
        {group.name}
      </HoverCardTrigger>
      <HoverCardContent className="max-w-[calc(100vw-2rem)] overflow-hidden">
        <p className="font-medium">Описание</p>
        <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground [overflow-wrap:anywhere]">
          {group.description}
        </p>
      </HoverCardContent>
    </HoverCard>
  )
}
