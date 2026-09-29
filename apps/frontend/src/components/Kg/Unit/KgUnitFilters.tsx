import type { KgOtkStatus, KgState } from '@web-app/api-client'
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

import { kgOtkStatusFilterOptions, kgStateFilterOptions } from '@/features/kg/kg-api'

type StateFilter = KgState | 'all'
type OtkStatusFilter = KgOtkStatus | 'all'

export function KgUnitFilters({
  onOtkStatusChange,
  onQueryChange,
  onStateChange,
  otkStatus,
  query,
  state,
}: Readonly<{
  onOtkStatusChange: (value: OtkStatusFilter) => void
  onQueryChange: (value: string) => void
  onStateChange: (value: StateFilter) => void
  otkStatus: OtkStatusFilter
  query: string
  state: StateFilter
}>) {
  const stateLabel = kgStateFilterOptions.find((item) => item.value === state)?.label
  const otkStatusLabel = kgOtkStatusFilterOptions.find((item) => item.value === otkStatus)?.label

  return (
    <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
      <InputGroup className="w-full sm:w-72">
        <InputGroupInput
          aria-label="Поиск по DevEUI или короткому ID"
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Поиск по DevEUI или ID..."
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
      <div className="flex flex-wrap items-center gap-2 sm:flex-nowrap">
        <Select onValueChange={(value) => onStateChange(value as StateFilter)} value={state}>
          <SelectTrigger className="w-48 cursor-pointer">
            <SelectValue>{stateLabel}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              {kgStateFilterOptions.map((item) => (
                <SelectItem key={item.value} value={item.value}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
        <Select
          onValueChange={(value) => onOtkStatusChange(value as OtkStatusFilter)}
          value={otkStatus}
        >
          <SelectTrigger className="w-52 cursor-pointer">
            <SelectValue>{otkStatusLabel}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              {kgOtkStatusFilterOptions.map((item) => (
                <SelectItem key={item.value} value={item.value}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
