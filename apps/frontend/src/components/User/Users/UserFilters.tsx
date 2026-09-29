import { SearchIcon, XIcon } from 'lucide-react'

import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@web-app/ui/components/input-group'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@web-app/ui/components/select'

import { roleFilterOptions, type Role } from '@/features/users/users-api'
import { activityFilterOptions, type Activity } from '@/lib/activity'

type RoleFilter = Role | 'all'
type StatusFilter = Activity | 'all'

export function UserFilters({
  archived,
  onQueryChange,
  onRoleChange,
  onStatusChange,
  query,
  role,
  status,
}: Readonly<{
  archived: boolean
  onQueryChange: (value: string) => void
  onRoleChange: (value: RoleFilter) => void
  onStatusChange: (value: StatusFilter) => void
  query: string
  role: RoleFilter
  status: StatusFilter
}>) {
  const roleLabel = roleFilterOptions.find((option) => option.value === role)?.label
  const statusLabel = activityFilterOptions.find((option) => option.value === status)?.label

  return (
    <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
      <InputGroup className="w-full sm:w-72">
        <InputGroupInput
          aria-label="Поиск по имени или логину"
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Поиск по имени или логину..."
          value={query}
        />
        <InputGroupAddon align="inline-start">
          <SearchIcon />
        </InputGroupAddon>
        {query && (
          <InputGroupAddon align="inline-end">
            <InputGroupButton
              aria-label="Очистить поиск"
              onClick={() => onQueryChange('')}
              size="icon-xs"
            >
              <XIcon data-icon="inline-start" />
            </InputGroupButton>
          </InputGroupAddon>
        )}
      </InputGroup>

      <div className="flex flex-wrap items-center gap-2 sm:flex-nowrap">
        <Select onValueChange={(value) => onRoleChange(value as RoleFilter)} value={role}>
          <SelectTrigger className="w-40 cursor-pointer">
            <SelectValue>{roleLabel}</SelectValue>
          </SelectTrigger>

          <SelectContent>
            <SelectGroup>
              {roleFilterOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>

        {!archived && (
          <Select onValueChange={(value) => onStatusChange(value as StatusFilter)} value={status}>
            <SelectTrigger className="w-40 cursor-pointer">
              <SelectValue>{statusLabel}</SelectValue>
            </SelectTrigger>

            <SelectContent>
              <SelectGroup>
                {activityFilterOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        )}
      </div>
    </div>
  )
}
