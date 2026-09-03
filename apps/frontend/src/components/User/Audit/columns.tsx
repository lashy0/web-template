import { type DataTableColumn } from '@/components/Common/DataTable'
import { TruncatedText } from '@/components/Common/TruncatedText'
import { ChangesAudit } from '@/components/User/Audit/ChangesAudit'
import type { AuditEvent } from '@/features/users/users-api'
import { formatDateTime } from '@/lib/date'

const maxIdentityDisplayLength = 32

export const auditColumns: readonly DataTableColumn<AuditEvent>[] = [
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
    cell: ({ row }) => <UserAccount event={row.original} />,
    enableSorting: false,
    header: 'Учётная запись',
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

function translateAction(action: string) {
  const actions: Record<string, string> = {
    'user.created': 'Создан пользователь',
    'user.updated': 'Обновлён пользователь',
    'user.bootstrap_created': 'Создан начальный администратор',
    'user.bootstrap_completed': 'Завершена настройка начального администратора',
    'user.password_changed': 'Изменён пароль',
    'user.active_changed': 'Изменён статус',
    'user.reconciled': 'Синхронизирована учётная запись',
    'user.archived': 'Архивирован пользователь',
    'user.restored': 'Восстановлен пользователь',
    'user.deleted': 'Удалён пользователь',
  }
  return actions[action] ?? action
}

function AuditActor({ event }: Readonly<{ event: AuditEvent }>) {
  if (event.actorType === 'system') {
    return 'Система'
  }

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

function UserAccount({ event }: Readonly<{ event: AuditEvent }>) {
  const label =
    event.entityDisplayName ??
    dataValue(event.newData, 'name') ??
    dataValue(event.oldData, 'name') ??
    'Учётная запись'
  const identifier =
    event.entityIdentifier ?? dataValue(event.newData, 'login') ?? dataValue(event.oldData, 'login')

  return (
    <span className="inline-flex w-80 max-w-full flex-col">
      <TruncatedText maxLength={maxIdentityDisplayLength} value={label} />
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
