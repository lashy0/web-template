import type { AuditSection } from '@/features/audit/audit'
import { pakKindLabels, pakKinds } from '@/features/paks/paks-api'

export const pakAudit: AuditSection = {
  title: 'Аудит ПАК',
  loadingLabel: 'Загрузка аудита ПАК',
  targetTypes: ['pak'],
  targetHeader: 'ПАК',
  actionLabels: {
    'pak.access_key_rotated': 'Ключ доступа ротирован',
    'pak.activated': 'Активирован ПАК',
    'pak.archived': 'Архивирован ПАК',
    'pak.created': 'Создан ПАК',
    'pak.deactivated': 'Деактивирован ПАК',
    'pak.deleted': 'Удалён ПАК',
    'pak.restored': 'Восстановлен ПАК',
    'pak.updated': 'Обновлён ПАК',
  },
  fieldLabels: {
    code: 'Код',
    kind: 'Тип',
    is_active: 'Активен',
  },
  formatValue: (field, value) => {
    const kind = field === 'kind' ? pakKinds.find((item) => item === value) : undefined
    return kind ? pakKindLabels[kind] : undefined
  },
}
