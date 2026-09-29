import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@web-app/ui/components/sheet'
import type { ReactNode } from 'react'

import {
  actionLabel,
  actorLabel,
  auditChanges,
  auditValues,
  describeUserAgent,
  targetLabel,
  type AuditChange,
  type AuditEntry,
  type AuditSection,
} from '@/features/audit/audit'
import { formatDateTime } from '@/lib/date'

/** Everything one audit entry records: who, when, from where, and what changed. */
export function AuditEntrySheet({
  entry,
  onOpenChange,
  open,
  section,
}: Readonly<{
  entry: AuditEntry | null
  onOpenChange: (open: boolean) => void
  open: boolean
  section: AuditSection
}>) {
  return (
    <Sheet onOpenChange={onOpenChange} open={open}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-md">
        {entry ? <EntryDetails entry={entry} section={section} /> : null}
      </SheetContent>
    </Sheet>
  )
}

function EntryDetails({ entry, section }: Readonly<{ entry: AuditEntry; section: AuditSection }>) {
  const changes = auditChanges(section, entry)
  const values = auditValues(section, entry)

  return (
    <>
      <SheetHeader className="pr-12">
        <SheetTitle className="text-lg font-semibold">
          {actionLabel(section, entry.action)}
        </SheetTitle>
        <SheetDescription>{targetLabel(section, entry)}</SheetDescription>
      </SheetHeader>
      <div className="flex flex-col gap-6 px-4 pb-6">
        <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2">
          <Row label="Время">{formatDateTime(entry.createdAt)}</Row>
          <Row label="Пользователь">{actorLabel(entry)}</Row>
          <Row label={section.targetHeader}>{targetLabel(section, entry)}</Row>
          {entry.ipAddress ? <Row label="IP-адрес">{entry.ipAddress}</Row> : null}
          {entry.userAgent ? (
            <Row label="Браузер">
              <span title={entry.userAgent}>{describeUserAgent(entry.userAgent)}</span>
            </Row>
          ) : null}
        </dl>
        {changes.length > 0 ? (
          <DetailsSection title="Изменения">
            <div className="flex flex-col gap-4">
              {changes.map((change) => (
                <ChangeBlock change={change} key={change.field} />
              ))}
            </div>
          </DetailsSection>
        ) : null}
        {values.length > 0 ? (
          <DetailsSection
            title={entry.action.endsWith('.deleted') ? 'На момент удаления' : 'Значения'}
          >
            <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2">
              {values.map((item) => (
                <Row key={item.field} label={item.label}>
                  <Value value={item.value} />
                </Row>
              ))}
            </dl>
          </DetailsSection>
        ) : null}
      </div>
    </>
  )
}

function Row({ children, label }: Readonly<{ children: ReactNode; label: string }>) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </>
  )
}

function DetailsSection({ children, title }: Readonly<{ children: ReactNode; title: string }>) {
  return (
    <section className="flex flex-col gap-3 border-t pt-4">
      <h3 className="font-medium">{title}</h3>
      {children}
    </section>
  )
}

function ChangeBlock({ change }: Readonly<{ change: AuditChange }>) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="font-medium">{change.label}</div>
      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 pl-3">
        <Row label="Было">
          <Value value={change.from} />
        </Row>
        <Row label="Стало">
          <Value value={change.to} />
        </Row>
      </dl>
    </div>
  )
}

/** A value with its line breaks kept; an empty value is a muted «—». */
function Value({ value }: Readonly<{ value: string | null }>) {
  return value === null ? (
    <span className="text-muted-foreground">—</span>
  ) : (
    <span className="whitespace-pre-wrap">{value}</span>
  )
}
