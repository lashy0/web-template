import { cn } from '@web-app/ui/lib/utils'

import { Badge } from '@web-app/ui/components/badge'
import { type DataTableColumn } from '@/components/Common/DataTable'
import { UserActionsMenu } from '@/components/User/Users/UserActionsMenu'
import {
  authStateLabels,
  roleLabels,
  type AuthState,
  type Role,
  type User,
} from '@/features/users/users-api'
import { formatDateTime } from '@/lib/date'

export function createUserColumns(
  currentUserId: string,
  archived: boolean,
): readonly DataTableColumn<User>[] {
  const columns: DataTableColumn<User>[] = [
    {
      accessorKey: 'name',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{row.original.name}</span>
          {row.original.id === currentUserId ? <CurrentUserBadge /> : null}
        </div>
      ),
      enableSorting: true,
      header: 'Имя',
      sortDescFirst: false,
    },
    {
      accessorKey: 'login',
      cell: ({ row }) => <span className="text-muted-foreground">{row.original.login ?? '—'}</span>,
      enableSorting: true,
      header: 'Логин',
      sortDescFirst: false,
    },
    {
      accessorKey: 'role',
      cell: ({ row }) => <RoleBadge role={row.original.role} />,
      enableSorting: false,
      header: 'Роль',
    },
  ]

  if (archived) {
    columns.push({
      accessorFn: (row) => row.archivedAt,
      cell: ({ row }) => <ArchivedAt value={row.original.archivedAt} />,
      enableSorting: true,
      header: 'Архивирован',
      id: 'archived_at',
      sortDescFirst: true,
    })
  } else {
    columns.push({
      id: 'status',
      cell: ({ row }) => <Status state={row.original.authState} />,
      enableSorting: false,
      header: 'Статус',
    })
  }

  columns.push({
    cell: ({ row }) => (
      <div className="flex justify-end">
        <UserActionsMenu user={row.original} />
      </div>
    ),
    header: () => <span className="sr-only">Действия</span>,
    id: 'actions',
    enableSorting: false,
  })

  return columns
}

function CurrentUserBadge() {
  return <Badge variant="outline">Вы</Badge>
}

function RoleBadge({ role }: Readonly<{ role: Role }>) {
  return <Badge variant="secondary">{roleLabels[role]}</Badge>
}

function Status({ state }: Readonly<{ state: AuthState }>) {
  return (
    <span className="inline-flex items-center gap-2">
      <span
        aria-hidden="true"
        className={cn(
          'size-2 rounded-full',
          state === 'active' && 'bg-green-500',
          state === 'inactive' && 'bg-red-500',
        )}
      />
      {authStateLabels[state]}
    </span>
  )
}

function ArchivedAt({ value }: Readonly<{ value: string | null }>) {
  if (!value) {
    return <span className="text-muted-foreground">—</span>
  }

  return <span className="text-muted-foreground">{formatDateTime(value)}</span>
}
