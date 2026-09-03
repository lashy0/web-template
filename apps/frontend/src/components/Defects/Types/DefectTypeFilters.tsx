import { SearchIcon, XIcon } from 'lucide-react'

import { Input } from '@web-app/ui/components/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@web-app/ui/components/select'

import { labelFor } from '@/components/Defects/Types/AddDefectType'
import { type DefectGroup } from '@/features/defects/defects-api'

export function DefectTypeFilters({
  groupId,
  groups,
  onGroupChange,
  onQueryChange,
  query,
}: Readonly<{
  groupId?: string
  groups: readonly DefectGroup[]
  onGroupChange: (value: string) => void
  onQueryChange: (value: string) => void
  query: string
}>) {
  const selectedGroup = groups.find((group) => group.id === groupId)
  return (
    <div className="flex w-full flex-col gap-2 @[40rem]:flex-row @[56rem]:w-auto">
      <div className="relative w-full @[56rem]:w-72">
        <SearchIcon className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          className="w-full px-8"
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Поиск по коду или названию..."
          value={query}
        />
        {query ? (
          <button
            aria-label="Очистить поиск"
            className="absolute top-1/2 right-2 flex size-5 -translate-y-1/2 cursor-pointer items-center justify-center text-muted-foreground hover:text-foreground"
            onClick={() => onQueryChange('')}
            type="button"
          >
            <XIcon className="size-4" />
          </button>
        ) : null}
      </div>
      <Select onValueChange={(value) => value && onGroupChange(value)} value={groupId ?? 'all'}>
        <SelectTrigger className="w-full cursor-pointer @[40rem]:w-60">
          <SelectValue
            className="min-w-0 truncate"
            title={selectedGroup ? labelFor(selectedGroup) : 'Все группы'}
          >
            {selectedGroup ? labelFor(selectedGroup) : 'Все группы'}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Все группы</SelectItem>
          {groups.map((group) => (
            <SelectItem key={group.id} value={group.id}>
              <span className="block min-w-0 truncate" title={labelFor(group)}>
                {labelFor(group)}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
