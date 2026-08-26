import { type DataTableColumn } from '@/components/Common/DataTable'
import { ChangesAudit } from '@/components/User/Audit/ChangesAudit'
import type { AuditEvent } from '@/features/users/users-api'
import { formatDateTime } from '@/lib/date'

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
    cell: ({ row }) => <UserAccount event={row.original} />,
    enableSorting: false,
    header: 'Учётная запись',
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
    <span className="inline-flex flex-col">
      <span>{label}</span>
      {event.actorIdentifier ? (
        <span className="text-xs text-muted-foreground">{event.actorIdentifier}</span>
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
    <span className="inline-flex flex-col">
      <span>{label}</span>
      {identifier ? <span className="text-xs text-muted-foreground">{identifier}</span> : null}
    </span>
  )
}

function dataValue(data: Record<string, unknown> | null, key: string): string | null {
  const value = data?.[key]
  return typeof value === 'string' ? value : null
}
