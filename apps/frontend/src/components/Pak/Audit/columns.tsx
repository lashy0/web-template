import { type DataTableColumn } from '@/components/Common/DataTable'
import { TruncatedText } from '@/components/Common/TruncatedText'
import { ChangesAudit } from '@/components/Pak/Audit/ChangesAudit'
import { type PakAuditEvent } from '@/features/paks/paks-api'
import { formatDateTime } from '@/lib/date'

const maxIdentityDisplayLength = 32

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
    cell: ({ row }) => <PakEntity event={row.original} />,
    enableSorting: false,
    header: 'ПАК',
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
    <span className="inline-flex w-80 max-w-full flex-col">
      <TruncatedText maxLength={maxIdentityDisplayLength} value={code} />
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
