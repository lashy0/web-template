import { SearchIcon, XIcon } from 'lucide-react'

import { Input } from '@web-app/ui/components/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@web-app/ui/components/select'

import { roleOptions, type AuthState, type Role } from '@/features/users/users-api'

type RoleFilter = Role | 'all'
type AuthStateFilter = AuthState | 'all'

export function UserFilters({
  archived,
  authState,
  onAuthStateChange,
  onQueryChange,
  onRoleChange,
  query,
  role,
}: Readonly<{
  archived: boolean
  authState: AuthStateFilter
  onAuthStateChange: (value: AuthStateFilter) => void
  onQueryChange: (value: string) => void
  onRoleChange: (value: RoleFilter) => void
  query: string
  role: RoleFilter
}>) {
  const roleLabel =
    role === 'all' ? 'Все роли' : roleOptions.find((option) => option.value === role)?.label

  const authStateLabels: Record<AuthStateFilter, string> = {
    all: 'Все статусы',
    active: 'Активен',
    inactive: 'Неактивен',
  }

  return (
    <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
      <div className="relative w-full sm:w-72">
        <SearchIcon className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />

        <Input
          className="w-full px-8"
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Поиск по имени или логину..."
          value={query}
        />

        {query && (
          <button
            aria-label="Очистить поиск"
            className="absolute right-2 top-1/2 flex size-5 -translate-y-1/2 cursor-pointer items-center justify-center rounded-sm text-muted-foreground hover:text-foreground"
            onClick={() => onQueryChange('')}
            type="button"
          >
            <XIcon className="size-4" />
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 sm:flex-nowrap">
        <Select onValueChange={(value) => onRoleChange(value as RoleFilter)} value={role}>
          <SelectTrigger className="w-40 cursor-pointer">
            <SelectValue>{roleLabel}</SelectValue>
          </SelectTrigger>

          <SelectContent>
            <SelectItem value="all">Все роли</SelectItem>

            {roleOptions.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {!archived && (
          <Select
            onValueChange={(value) => onAuthStateChange(value as AuthStateFilter)}
            value={authState}
          >
            <SelectTrigger className="w-40 cursor-pointer">
              <SelectValue>{authStateLabels[authState]}</SelectValue>
            </SelectTrigger>

            <SelectContent>
              <SelectItem value="all">Все статусы</SelectItem>
              <SelectItem value="active">Активен</SelectItem>
              <SelectItem value="inactive">Неактивен</SelectItem>
            </SelectContent>
          </Select>
        )}
      </div>
    </div>
  )
}
