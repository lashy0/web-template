import { useQuery } from '@tanstack/react-query'
import { ChevronsUpDownIcon, SearchIcon, XIcon } from 'lucide-react'
import { useEffect, useState } from 'react'

import {
  Combobox,
  ComboboxContent,
  ComboboxIcon,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
  ComboboxTrigger,
  ComboboxValue,
} from '@web-app/ui/components/combobox'

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
        className={className}
        disabled={disabled}
        id={id}
      >
        <span className="min-w-0 flex-1 truncate text-left">
          <ComboboxValue>{selectedLabel}</ComboboxValue>
        </span>
        <ComboboxIcon>
          <ChevronsUpDownIcon className="size-4" />
        </ComboboxIcon>
      </ComboboxTrigger>
      <ComboboxContent className="min-w-80 p-2">
        <div className="relative">
          <SearchIcon className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <ComboboxInput
            autoFocus
            className="pl-8 pr-8"
            placeholder="Поиск по коду или названию..."
          />
          {query ? (
            <button
              aria-label="Очистить поиск групп"
              className="absolute top-1/2 right-2 flex size-5 -translate-y-1/2 cursor-pointer items-center justify-center text-muted-foreground hover:text-foreground"
              onClick={() => setQuery('')}
              type="button"
            >
              <XIcon className="size-4" />
            </button>
          ) : null}
        </div>
        <ComboboxList className="mt-2">
          {allowClear ? (
            <ComboboxItem value={allGroupsValue}>Все группы</ComboboxItem>
          ) : null}
          {groups.isFetching ? <p className="px-2 py-3 text-sm text-muted-foreground">Поиск…</p> : null}
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
