import { DiffIcon } from 'lucide-react'

import { AuditChanges, getAuditChanges, type AuditChange } from '@/components/Common/AuditChanges'
import { type DefectAuditEvent } from '@/features/defects/defects-api'
import { formatDateTime } from '@/lib/date'
import { Button } from '@web-app/ui/components/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@web-app/ui/components/sheet'

const fieldLabels: Readonly<Record<string, string>> = {
  archived_at: 'Архивирование',
  code: 'Код',
  description: 'Описание',
  engineer_action: 'Действие инженера',
  group_id: 'Идентификатор группы',
  name: 'Название',
  possible_cause: 'Возможная причина',
}

const longTextFields = new Set(['description', 'engineer_action', 'possible_cause'])
const maxPopoverValueLength = 160

export function ChangesAudit({ event }: Readonly<{ event: DefectAuditEvent }>) {
  const changes = getAuditChanges(event)
  if (shouldUseSheet(changes)) {
    return <ChangesSheet changes={changes} event={event} />
  }

  return <AuditChanges event={event} fieldLabels={fieldLabels} formatValue={formatValue} />
}

function ChangesSheet({
  changes,
  event,
}: Readonly<{ changes: readonly AuditChange[]; event: DefectAuditEvent }>) {
  return (
    <Sheet>
      <SheetTrigger
        aria-label="Показать изменения"
        render={
          <Button
            className="cursor-pointer"
            size="icon-sm"
            title="Показать изменения"
            variant="ghost"
          />
        }
      >
        <DiffIcon />
        <span className="sr-only">Показать изменения</span>
      </SheetTrigger>
      <SheetContent className="w-full gap-0 p-0 sm:max-w-2xl">
        <SheetHeader className="border-b pr-12">
          <SheetTitle>Изменения</SheetTitle>
          <SheetDescription>{entityLabel(event)}</SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">
          {changes.map((change) => (
            <section key={change.key}>
              <h3 className="mb-2 text-sm font-medium">{fieldLabels[change.key] ?? change.key}</h3>
              <ChangeValue kind="old" value={formatValue(change.key, change.oldValue)} />
              <ChangeValue kind="new" value={formatValue(change.key, change.newValue)} />
            </section>
          ))}
        </div>
      </SheetContent>
    </Sheet>
  )
}

function ChangeValue({ kind, value }: Readonly<{ kind: 'old' | 'new'; value: string }>) {
  const isOld = kind === 'old'
  const colorClass = isOld ? 'border-[#e05d67] bg-[#e05d67]/10' : 'border-[#56a95a] bg-[#56a95a]/10'

  return (
    <div className={`border-l-4 px-3 py-2 text-sm ${colorClass}`}>
      <p className="mb-1 text-xs font-medium text-muted-foreground">{isOld ? 'Было' : 'Стало'}</p>
      <p className="whitespace-pre-wrap break-words text-foreground">{value}</p>
    </div>
  )
}

function shouldUseSheet(changes: readonly AuditChange[]): boolean {
  return (
    changes.length > 2 ||
    changes.some(
      (change) =>
        longTextFields.has(change.key) ||
        isLongValue(change.oldValue) ||
        isLongValue(change.newValue),
    )
  )
}

function isLongValue(value: unknown): boolean {
  return typeof value === 'string' && (value.length > maxPopoverValueLength || value.includes('\n'))
}

function entityLabel(event: DefectAuditEvent): string {
  const type = event.entityType === 'defect_group' ? 'Группа' : 'Тип'
  const name = event.entityDisplayName ?? type
  return event.entityIdentifier
    ? `${type}: ${name} (${event.entityIdentifier})`
    : `${type}: ${name}`
}

function formatValue(key: string, value: unknown): string {
  if (key === 'archived_at' && typeof value === 'string') {
    return formatDateTime(value)
  }
  if (value === null || value === undefined || value === '') {
    return '—'
  }
  return typeof value === 'string' ? value : String(value)
}
