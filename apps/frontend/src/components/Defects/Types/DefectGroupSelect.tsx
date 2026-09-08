import { useQuery } from '@tanstack/react-query'
import { ChevronDownIcon, SearchIcon, XIcon } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@web-app/ui/components/button'
import {
  Combobox,
  ComboboxContent,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
  ComboboxTrigger,
  ComboboxValue,
} from '@web-app/ui/components/combobox'
import { InputGroup, InputGroupAddon, InputGroupButton } from '@web-app/ui/components/input-group'
import { cn } from '@web-app/ui/lib/utils'

import { defectGroupLabel } from '@/features/defects/defect-format'
import { getDefectGroup, listDefectGroups } from '@/features/defects/defects-api'

const allGroupsValue = '__all_defect_groups__'

export function DefectGroupSelect({
  allowClear = false,
  ariaLabel,
  className,
  disabled = false,
  id,
  onChange,
  placeholder = 'Выберите группу',
  value,
}: Readonly<{
  allowClear?: boolean
  ariaLabel?: string
  className?: string
  disabled?: boolean
  id?: string
  onChange: (value: string | undefined) => void
  placeholder?: string
  value?: string
}>) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const selectedGroup = useQuery({
    enabled: Boolean(value),
    queryFn: () => getDefectGroup(value!),
    queryKey: ['defects', 'group', value],
  })
  const groups = useQuery({
    enabled: open,
    queryFn: () => listDefectGroups({ page: 1, pageSize: 100, query: debouncedQuery || undefined }),
    queryKey: ['defects', 'groups', 'select', debouncedQuery],
  })

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedQuery(query.trim()), 250)
    return () => window.clearTimeout(timeout)
  }, [query])

  const selectedLabel = selectedGroup.data
    ? defectGroupLabel(selectedGroup.data)
    : selectedGroup.isFetching
      ? 'Загрузка группы…'
      : value
        ? 'Группа не найдена'
        : placeholder
  const selectedValue = value ?? (allowClear ? allGroupsValue : null)

  const select = (groupId: string | undefined) => {
    onChange(groupId)
    setOpen(false)
  }

  return (
    <Combobox
      inputValue={query}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen)
        if (!nextOpen) setQuery('')
      }}
      onInputValueChange={setQuery}
      onValueChange={(nextValue) =>
        select(nextValue === allGroupsValue || nextValue === null ? undefined : nextValue)
      }
      open={open}
      value={selectedValue}
    >
      <ComboboxTrigger
        aria-label={ariaLabel ?? selectedLabel}
        disabled={disabled}
        id={id}
        render={<Button className={cn('justify-between font-normal', className)} variant="outline" />}
      >
        <span className="min-w-0 flex-1 truncate text-left">
          <ComboboxValue>{selectedLabel}</ComboboxValue>
        </span>
        <ChevronDownIcon data-icon="inline-end" />
      </ComboboxTrigger>
      <ComboboxContent className="min-w-80 p-2">
        <InputGroup>
          <ComboboxInput
            aria-label="Поиск групп"
            className="flex-1 rounded-none border-0 bg-transparent shadow-none focus-visible:ring-0"
            data-slot="input-group-control"
            placeholder="Поиск по коду или названию..."
          />
          <InputGroupAddon align="inline-start">
            <SearchIcon />
          </InputGroupAddon>
          {query ? (
            <InputGroupAddon align="inline-end">
              <InputGroupButton
                aria-label="Очистить поиск групп"
                onClick={() => setQuery('')}
                size="icon-xs"
              >
                <XIcon data-icon="inline-start" />
              </InputGroupButton>
            </InputGroupAddon>
          ) : null}
        </InputGroup>
        <ComboboxList className="mt-2">
          {allowClear ? <ComboboxItem value={allGroupsValue}>Все группы</ComboboxItem> : null}
          {groups.isFetching ? (
            <p className="px-2 py-3 text-sm text-muted-foreground">Поиск…</p>
          ) : null}
          {!groups.isFetching && groups.data?.items.length === 0 ? (
            <p className="px-2 py-3 text-sm text-muted-foreground">Группы не найдены.</p>
          ) : null}
          {groups.data?.items.map((group) => (
            <ComboboxItem key={group.id} value={group.id}>
              <span className="min-w-0 truncate">{defectGroupLabel(group)}</span>
            </ComboboxItem>
          ))}
        </ComboboxList>
      </ComboboxContent>
    </Combobox>
  )
}
