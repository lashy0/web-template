import { DiffIcon } from 'lucide-react'

import { Button } from '@web-app/ui/components/button'
import { Popover, PopoverContent, PopoverTrigger } from '@web-app/ui/components/popover'

export type AuditChangeEvent = Readonly<{
  action: string
  newData: Record<string, unknown> | null
  oldData: Record<string, unknown> | null
}>

export type AuditChange = Readonly<{
  key: string
  newValue: unknown
  oldValue: unknown
}>

export function AuditChanges({
  event,
  fieldLabels,
  formatValue = defaultFormatValue,
  statusChangeAction,
}: Readonly<{
  event: AuditChangeEvent
  fieldLabels: Readonly<Record<string, string>>
  formatValue?: (key: string, value: unknown) => string
  statusChangeAction?: string
}>) {
  const changes = getAuditChanges(event)
  if (!changes.length) {
    return null
  }

  const statusOnly = event.action === statusChangeAction && changes.length === 1

  return (
    <Popover>
      <PopoverTrigger
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
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 max-w-[calc(100vw-2rem)] p-3" side="left">
        <h3 className="mb-3 text-sm font-semibold">
          {statusOnly ? 'Изменение статуса' : 'Изменения'}
        </h3>
        <div className="space-y-3">
          {changes.map((change) => (
            <section key={change.key}>
              {!statusOnly ? (
                <h4 className="mb-1 text-xs font-medium text-muted-foreground">
                  {fieldLabels[change.key] ?? change.key}
                </h4>
              ) : null}
              <ChangeValue kind="old" value={formatValue(change.key, change.oldValue)} />
              <ChangeValue kind="new" value={formatValue(change.key, change.newValue)} />
            </section>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  )
}

function ChangeValue({ kind, value }: Readonly<{ kind: 'old' | 'new'; value: string }>) {
  const isOld = kind === 'old'
  const colorClass = isOld
    ? 'border-l-4 border-[#e05d67] bg-[#e05d67]/10 text-foreground'
    : 'border-l-4 border-[#56a95a] bg-[#56a95a]/10 text-foreground'
  return (
    <div className={`flex items-start gap-2 px-2 py-1.5 text-sm ${colorClass}`}>
      <span aria-hidden="true" className="font-semibold">
        {isOld ? '−' : '+'}
      </span>
      <span className="min-w-0 break-all">{value}</span>
    </div>
  )
}

export function getAuditChanges(event: AuditChangeEvent): AuditChange[] {
  const { newData, oldData } = event
  if (!oldData || !newData) {
    return []
  }

  return Object.keys(oldData)
    .filter((key) => Object.hasOwn(newData, key))
    .filter((key) => !Object.is(oldData[key], newData[key]))
    .map((key) => ({ key, newValue: newData[key], oldValue: oldData[key] }))
}

function defaultFormatValue(_key: string, value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return '—'
  }
  return typeof value === 'string' ? value : String(value)
}
