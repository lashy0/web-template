import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react'
import type { ReactNode } from 'react'

import { Button } from '@web-app/ui/components/button'

export function DataTableColumnHeader({
  children,
  disabled,
  onSortingToggle,
  sortDirection,
}: Readonly<{
  children: ReactNode
  disabled: boolean
  onSortingToggle: () => void
  sortDirection: false | 'asc' | 'desc'
}>) {
  return (
    <Button
      className="-ml-3 h-8 cursor-pointer px-3"
      disabled={disabled}
      onClick={() => onSortingToggle()}
      size="sm"
      title="Сортировать"
      variant="ghost"
    >
      {children}
      {sortDirection === 'asc' ? (
        <ArrowUp aria-hidden="true" className="size-4" />
      ) : sortDirection === 'desc' ? (
        <ArrowDown aria-hidden="true" className="size-4" />
      ) : (
        <ChevronsUpDown aria-hidden="true" className="size-4" />
      )}
    </Button>
  )
}
