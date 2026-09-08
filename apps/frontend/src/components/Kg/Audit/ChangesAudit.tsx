import { AuditChanges } from '@/components/Common/AuditChanges'
import { type KgAuditEvent } from '@/features/kg/kg-prefixes-api'
import { formatDateTime } from '@/lib/date'

const fieldLabels: Readonly<Record<string, string>> = {
  archived_at: 'Архивирование',
  code: 'Код',
  description: 'Описание',
  name: 'Название',
  prefix: 'Префикс DevEUI',
  short_code: 'Короткий код',
}

export function ChangesAudit({ event }: Readonly<{ event: KgAuditEvent }>) {
  return (
    <AuditChanges
      event={event}
      fieldLabels={fieldLabels}
      formatValue={formatValue}
    />
  )
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
