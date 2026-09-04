import { SearchIcon, XIcon } from 'lucide-react'

import { Input } from '@web-app/ui/components/input'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@web-app/ui/components/select'

import {
  pakKindFilterOptions,
  pakStatusFilterOptions,
  type PakKind,
  type PakStatus,
} from '@/features/paks/paks-api'

type KindFilter = PakKind | 'all'
type StatusFilter = PakStatus | 'all'

export function PakFilters({
  archived,
  kind,
  onKindChange,
  onQueryChange,
  onStatusChange,
  query,
  status,
}: Readonly<{
  archived: boolean
  kind: KindFilter
  onKindChange: (value: KindFilter) => void
  onQueryChange: (value: string) => void
  onStatusChange: (value: StatusFilter) => void
  query: string
  status: StatusFilter
}>) {
  const kindLabel = pakKindFilterOptions.find((item) => item.value === kind)?.label
  const statusLabel = pakStatusFilterOptions.find((item) => item.value === status)?.label

  return (
    <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
      <div className="relative w-full sm:w-72">
        <SearchIcon className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          className="w-full px-8"
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Поиск по коду или клиенту..."
          value={query}
        />
        {query ? (
          <button
            aria-label="Очистить поиск"
            className="absolute right-2 top-1/2 flex size-5 -translate-y-1/2 cursor-pointer items-center justify-center rounded-sm text-muted-foreground hover:text-foreground"
            onClick={() => onQueryChange('')}
            type="button"
          >
            <XIcon className="size-4" />
          </button>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center gap-2 sm:flex-nowrap">
        <Select onValueChange={(value) => onKindChange(value as KindFilter)} value={kind}>
          <SelectTrigger className="w-40 cursor-pointer">
            <SelectValue>{kindLabel}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              {pakKindFilterOptions.map((item) => (
                <SelectItem key={item.value} value={item.value}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
        {!archived ? (
          <Select onValueChange={(value) => onStatusChange(value as StatusFilter)} value={status}>
            <SelectTrigger className="w-40 cursor-pointer">
              <SelectValue>{statusLabel}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {pakStatusFilterOptions.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        ) : null}
      </div>
    </div>
  )
}
