import { Avatar, AvatarFallback } from '@web-app/ui/components/avatar'

import type { AuthenticatedUser } from '@/features/auth/auth-api'

const roleLabels: Record<AuthenticatedUser['role'], string> = {
  administrator: 'Администратор',
  manager: 'Менеджер',
  engineer: 'Инженер',
  packer: 'Упаковщик',
  operator: 'Оператор',
}

export function AccountSummary({
  compact,
  details = 'role',
  user,
}: Readonly<{
  compact?: boolean
  details?: 'login' | 'role'
  user: Pick<AuthenticatedUser, 'login' | 'name' | 'role'>
}>) {
  return (
    <div className="flex w-full min-w-0 items-center gap-2.5">
      <Avatar className="size-8">
        <AvatarFallback>{initials(user.name)}</AvatarFallback>
      </Avatar>
      <div
        className={
          compact
            ? 'hidden min-w-0 flex-col items-start sm:flex'
            : 'flex min-w-0 flex-col items-start'
        }
      >
        <p className="w-full truncate text-sm font-medium">{user.name}</p>
        <p className="w-full truncate text-xs text-muted-foreground">
          {details === 'login' ? user.login : roleLabels[user.role]}
        </p>
      </div>
    </div>
  )
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}
