import { AuditChanges } from '@/components/Common/AuditChanges'
import { roleLabels, type AuditEvent, type Role } from '@/features/users/users-api'

const fieldLabels: Record<string, string> = {
  active: 'Статус',
  login: 'Логин',
  name: 'Имя',
  role: 'Роль',
}

export function ChangesAudit({ event }: Readonly<{ event: AuditEvent }>) {
  return (
    <AuditChanges
      event={event}
      fieldLabels={fieldLabels}
      formatValue={formatValue}
      statusChangeAction="user.active_changed"
    />
  )
}

function formatValue(key: string, value: unknown): string {
  if (key === 'role' && typeof value === 'string' && value in roleLabels) {
    return roleLabels[value as Role]
  }
  if (key === 'active' && typeof value === 'boolean') {
    return value ? 'Активен' : 'Неактивен'
  }
  if (value === null || value === undefined || value === '') {
    return '—'
  }
  return typeof value === 'string' ? value : String(value)
}
