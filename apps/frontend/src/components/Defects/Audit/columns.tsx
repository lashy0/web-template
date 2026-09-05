import { type DataTableColumn } from '@/components/Common/DataTable'
import { TruncatedText } from '@/components/Common/TruncatedText'
import { ChangesAudit } from '@/components/Defects/Audit/ChangesAudit'
import { type DefectAuditEvent } from '@/features/defects/defects-api'
import { formatDateTime } from '@/lib/date'

const actionsWithoutChanges = new Set([
  'defect_group.archived',
  'defect_group.restored',
  'defect_type.archived',
  'defect_type.restored',
])
const maxIdentityDisplayLength = 32

export const defectAuditColumns: readonly DataTableColumn<DefectAuditEvent>[] = [
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
    accessorKey: 'actorDisplayName',
    cell: ({ row }) => <AuditActor event={row.original} />,
    enableSorting: true,
    header: 'Пользователь',
    id: 'actor_display_name',
    meta: { widthClassName: 'w-40 xl:w-1/5' },
    sortDescFirst: false,
  },
  {
    accessorKey: 'action',
    cell: ({ row }) => <TruncatedText value={translateAction(row.original.action)} />,
    enableSorting: false,
    header: 'Действие',
    meta: { widthClassName: 'w-[230px] xl:w-[31%]' },
  },
  {
    accessorKey: 'entityDisplayName',
    cell: ({ row }) => <DefectEntity event={row.original} />,
    enableSorting: false,
    header: 'Объект',
    meta: { widthClassName: 'w-40 xl:w-[28%]' },
  },
  {
    cell: ({ row }) =>
      hasChanges(row.original.action) ? (
        <div className="flex justify-end">
          <ChangesAudit event={row.original} />
        </div>
      ) : null,
    enableSorting: false,
    header: () => <span className="sr-only">Изменения</span>,
    id: 'changes',
    meta: { widthClassName: 'w-[58px] xl:w-[6%]' },
  },
]

function translateAction(action: string): string {
  const actions: Readonly<Record<string, string>> = {
    'defect_group.archived': 'Архивирована группа',
    'defect_group.created': 'Создана группа',
    'defect_group.deleted': 'Удалена группа',
    'defect_group.restored': 'Восстановлена группа',
    'defect_group.updated': 'Обновлена группа',
    'defect_type.archived': 'Архивирован тип',
    'defect_type.created': 'Создан тип',
    'defect_type.deleted': 'Удалён тип',
    'defect_type.restored': 'Восстановлен тип',
    'defect_type.updated': 'Обновлён тип',
  }
  return actions[action] ?? action
}

function hasChanges(action: string): boolean {
  return !actionsWithoutChanges.has(action)
}

function AuditActor({ event }: Readonly<{ event: DefectAuditEvent }>) {
  if (event.actorType === 'system') return 'Система'

  const label =
    event.actorDisplayName ?? (event.actorType === 'user' ? 'Пользователь' : event.actorType)
  return (
    <span className="inline-flex w-48 max-w-full flex-col">
      <TruncatedText maxLength={maxIdentityDisplayLength} value={label} />
      {event.actorIdentifier ? (
        <span className="text-xs text-muted-foreground">
          <TruncatedText maxLength={maxIdentityDisplayLength} value={event.actorIdentifier} />
        </span>
      ) : null}
    </span>
  )
}

function DefectEntity({ event }: Readonly<{ event: DefectAuditEvent }>) {
  const type = event.entityType === 'defect_group' ? 'Группа' : 'Тип'
  const label =
    event.entityDisplayName ??
    dataValue(event.newData, 'name') ??
    dataValue(event.oldData, 'name') ??
    type
  const identifier =
    event.entityIdentifier ?? dataValue(event.newData, 'code') ?? dataValue(event.oldData, 'code')

  return (
    <span className="inline-flex w-80 max-w-full flex-col">
      <TruncatedText maxLength={maxIdentityDisplayLength} value={`${type}: ${label}`} />
      {identifier ? (
        <span className="text-xs text-muted-foreground">
          <TruncatedText maxLength={maxIdentityDisplayLength} value={identifier} />
        </span>
      ) : null}
    </span>
  )
}

function dataValue(data: Record<string, unknown> | null, key: string): string | null {
  const value = data?.[key]
  return typeof value === 'string' ? value : null
}
