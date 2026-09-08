import { SearchIcon, XIcon } from 'lucide-react'

import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@web-app/ui/components/input-group'

export function KgVersionFilters({
  onQueryChange,
  query,
}: Readonly<{
  onQueryChange: (value: string) => void
  query: string
}>) {
  return (
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
  )
}
