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

import { batchStatusFilterOptions, type BatchStatus } from '@/features/batches/batches-api'

type StatusFilter = BatchStatus | 'all'

export function BatchFilters({
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
  const statusLabel = batchStatusFilterOptions.find((item) => item.value === status)?.label

  return (
    <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
      <InputGroup className="w-full sm:w-72">
        <InputGroupInput
          aria-label="Поиск по названию или описанию"
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Поиск по названию или описанию..."
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
        <SelectTrigger className="w-40 cursor-pointer">
          <SelectValue>{statusLabel}</SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            {batchStatusFilterOptions.map((item) => (
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
