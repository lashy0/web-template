import { SearchIcon, XIcon } from 'lucide-react'

import { Input } from '@web-app/ui/components/input'

import { DefectGroupSelect } from '@/components/Defects/Types/DefectGroupSelect'

export function DefectTypeFilters({
  groupId,
  onGroupChange,
  onQueryChange,
  query,
}: Readonly<{
  groupId?: string
  onGroupChange: (value: string) => void
  onQueryChange: (value: string) => void
  query: string
}>) {
  return (
    <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
      <div className="relative w-full sm:w-72">
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
      <DefectGroupSelect
        allowClear
        ariaLabel="Группа дефектов"
        className="w-full cursor-pointer sm:w-60"
        onChange={(value) => onGroupChange(value ?? 'all')}
        placeholder="Все группы"
        value={groupId}
      />
    </div>
  )
}
