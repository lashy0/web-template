import { type DataTableColumn } from '@/components/Common/DataTable'
import { ChangesAudit } from '@/components/Pak/Audit/ChangesAudit'
import { type PakAuditEvent } from '@/features/paks/paks-api'
import { formatDateTime } from '@/lib/date'

export const pakAuditColumns: readonly DataTableColumn<PakAuditEvent>[] = [
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
    sortDescFirst: true,
  },
  {
    accessorKey: 'actorDisplayName',
    cell: ({ row }) => <AuditActor event={row.original} />,
    enableSorting: true,
    header: 'Пользователь',
    id: 'actor_display_name',
    sortDescFirst: false,
  },
  {
    accessorKey: 'action',
    cell: ({ row }) => translateAction(row.original.action),
    enableSorting: false,
    header: 'Действие',
  },
  {
    accessorKey: 'entityDisplayName',
    cell: ({ row }) => <PakEntity event={row.original} />,
    enableSorting: false,
    header: 'ПАК',
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
  },
]

function translateAction(action: string) {
  const actions: Record<string, string> = {
    'pak.active_changed': 'Изменён статус',
    'pak.access_key_rotated': 'Ключ доступа ротирован',
    'pak.access_key_viewed': 'Ключ доступа просмотрен',
    'pak.archived': 'Архивирован ПАК',
    'pak.created': 'Создан ПАК',
    'pak.deleted': 'Удалён ПАК',
    'pak.restored': 'Восстановлен ПАК',
    'pak.updated': 'Обновлён ПАК',
  }
  return actions[action] ?? action
}

function hasChanges(action: string): boolean {
  return action !== 'pak.archived' && action !== 'pak.restored'
}

function AuditActor({ event }: Readonly<{ event: PakAuditEvent }>) {
  if (event.actorType === 'system') return 'Система'
  const label =
    event.actorDisplayName ?? (event.actorType === 'user' ? 'Пользователь' : event.actorType)
  return (
    <span className="inline-flex flex-col">
      <span>{label}</span>
      {event.actorIdentifier ? (
        <span className="text-xs text-muted-foreground">{event.actorIdentifier}</span>
      ) : null}
    </span>
  )
}

function PakEntity({ event }: Readonly<{ event: PakAuditEvent }>) {
  const code =
    event.entityDisplayName ??
    dataValue(event.newData, 'code') ??
    dataValue(event.oldData, 'code') ??
    'ПАК'
  const identifier =
    event.entityIdentifier ??
    dataValue(event.newData, 'oauth_client_id') ??
    dataValue(event.oldData, 'oauth_client_id')
  return (
    <span className="inline-flex flex-col">
      <span>{code}</span>
      {identifier ? <span className="text-xs text-muted-foreground">{identifier}</span> : null}
    </span>
  )
}

function dataValue(data: Record<string, unknown> | null, key: string): string | null {
  const value = data?.[key]
  return typeof value === 'string' ? value : null
}
