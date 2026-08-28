import { AuditChanges } from '@/components/Common/AuditChanges'
import { pakKindLabels, type PakAuditEvent, type PakKind } from '@/features/paks/paks-api'

const fieldLabels: Readonly<Record<string, string>> = {
  active: 'Статус',
  code: 'Код ПАК',
  kind: 'Тип',
}

export function ChangesAudit({ event }: Readonly<{ event: PakAuditEvent }>) {
  return (
    <AuditChanges
      event={event}
      fieldLabels={fieldLabels}
      formatValue={formatValue}
      statusChangeAction="pak.active_changed"
    />
  )
}

function formatValue(key: string, value: unknown): string {
  if (key === 'kind' && typeof value === 'string' && value in pakKindLabels) {
    return pakKindLabels[value as PakKind]
  }
  if (key === 'active' && typeof value === 'boolean') {
    return value ? 'Разрешён' : 'Отключён'
  }
  if (value === null || value === undefined || value === '') {
    return '—'
  }
  return typeof value === 'string' ? value : String(value)
}
