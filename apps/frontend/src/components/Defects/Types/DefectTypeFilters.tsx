import { SearchIcon, XIcon } from 'lucide-react'

import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@web-app/ui/components/input-group'

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
      <InputGroup className="w-full sm:w-72">
        <InputGroupInput
          aria-label="Поиск по коду или названию"
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Поиск по коду или названию..."
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
