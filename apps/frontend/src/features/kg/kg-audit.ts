import type { AuditSection } from '@/features/audit/audit'

export const kgAudit: AuditSection = {
  title: 'Аудит КГ',
  loadingLabel: 'Загрузка аудита КГ',
  targetTypes: ['kg_prefix', 'kg_version'],
  targetHeader: 'Объект',
  targetTypeLabels: { kg_prefix: 'Префикс', kg_version: 'Версия КГ' },
  actionLabels: {
    'kg_prefix.archived': 'Префикс архивирован',
    'kg_prefix.created': 'Префикс создан',
    'kg_prefix.deleted': 'Префикс удалён',
    'kg_prefix.restored': 'Префикс восстановлен',
    'kg_prefix.updated': 'Префикс изменён',
    'kg_version.archived': 'Версия КГ архивирована',
    'kg_version.created': 'Версия КГ создана',
    'kg_version.deleted': 'Версия КГ удалена',
    'kg_version.restored': 'Версия КГ восстановлена',
    'kg_version.updated': 'Версия КГ изменена',
  },
  fieldLabels: {
    name: 'Название',
    short_code: 'Короткий код',
    description: 'Описание',
  },
}
