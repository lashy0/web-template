import { type DataTableColumn } from '@/components/Common/DataTable'
import { TruncatedText } from '@/components/Common/TruncatedText'
import { ChangesAudit } from '@/components/Kg/Audit/ChangesAudit'
import { type KgAuditEvent } from '@/features/kg/kg-prefixes-api'
import { formatDateTime } from '@/lib/date'

const maxIdentityDisplayLength = 32

export const kgAuditColumns: readonly DataTableColumn<KgAuditEvent>[] = [
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
    cell: ({ row }) => <KgAuditEntity event={row.original} />,
    enableSorting: false,
    header: 'Объект',
    meta: { widthClassName: 'w-40 xl:w-[28%]' },
  },
  {
    cell: ({ row }) => (
      <div className="flex justify-end">
        <ChangesAudit event={row.original} />
      </div>
    ),
    enableSorting: false,
    header: () => <span className="sr-only">Изменения</span>,
    id: 'changes',
    meta: { widthClassName: 'w-[58px] xl:w-[6%]' },
  },
]

function translateAction(action: string): string {
  const actions: Readonly<Record<string, string>> = {
    'kg_prefix.archived': 'Префикс архивирован',
    'kg_prefix.created': 'Префикс создан',
    'kg_prefix.deleted': 'Префикс удалён',
    'kg_prefix.restored': 'Префикс восстановлен',
    'kg_prefix.updated': 'Префикс изменён',
    'kg_version.archived': 'Версия КГ архивирована',
    'kg_version.created': 'Версия КГ создана',
    'kg_version.deleted': 'Версия КГ удалена',
    'kg_version.restored': 'Версия КГ восстановлена',
    'kg_version.updated': 'Версия КГ изменена',
  }
  return actions[action] ?? action
}

function AuditActor({ event }: Readonly<{ event: KgAuditEvent }>) {
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

function KgAuditEntity({ event }: Readonly<{ event: KgAuditEvent }>) {
  const label = event.entityDisplayName ?? dataValue(event.newData, 'name') ?? 'Объект КГ'
  const identifier =
    event.entityIdentifier ??
    dataValue(event.newData, 'code') ??
    dataValue(event.oldData, 'code') ??
    dataValue(event.newData, 'prefix') ??
    dataValue(event.oldData, 'prefix')
  return (
    <span className="inline-flex w-80 max-w-full flex-col">
      <TruncatedText maxLength={maxIdentityDisplayLength} value={label} />
      {identifier ? (
        <span className="font-mono text-xs text-muted-foreground">
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
