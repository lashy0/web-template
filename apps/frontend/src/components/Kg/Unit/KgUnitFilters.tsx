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

import { kgStatusFilterOptions, type KgStatus } from '@/features/kg/kg-api'

type StatusFilter = KgStatus | 'all'

export function KgUnitFilters({
  onQueryChange,
  onStatusChange,
  query,
  status,
}: Readonly<{
  onQueryChange: (value: string) => void
  onStatusChange: (value: StatusFilter) => void
  query: string
  status: StatusFilter
}>) {
  const statusLabel = kgStatusFilterOptions.find((item) => item.value === status)?.label

  return (
    <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
      <InputGroup className="w-full sm:w-72">
        <InputGroupInput
          aria-label="Поиск по DevEUI"
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Поиск по DevEUI..."
          value={query}
        />
        <InputGroupAddon align="inline-start">
          <SearchIcon />
        </InputGroupAddon>
        {query ? (
          <InputGroupAddon align="inline-end">
            <InputGroupButton
              aria-label="Очистить поиск"
              onClick={() => onQueryChange('')}
              size="icon-xs"
            >
              <XIcon data-icon="inline-start" />
            </InputGroupButton>
          </InputGroupAddon>
        ) : null}
      </InputGroup>
      <Select onValueChange={(value) => onStatusChange(value as StatusFilter)} value={status}>
        <SelectTrigger className="w-64 cursor-pointer">
          <SelectValue>{statusLabel}</SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            {kgStatusFilterOptions.map((item) => (
              <SelectItem key={item.value} value={item.value}>
                {item.label}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
    </div>
  )
}
