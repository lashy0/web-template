import type { AuditSection } from '@/features/audit/audit'
import { roleLabels, type Role } from '@/features/users/users-api'

export const userAudit: AuditSection = {
  title: 'Аудит пользователей',
  loadingLabel: 'Загрузка аудита пользователей',
  targetTypes: ['user'],
  targetHeader: 'Учётная запись',
  actionLabels: {
    'user.activated': 'Активирован пользователь',
    'user.archived': 'Архивирован пользователь',
    'user.created': 'Создан пользователь',
    'user.deactivated': 'Деактивирован пользователь',
    'user.deleted': 'Удалён пользователь',
    'user.password_changed': 'Изменён пароль',
    'user.restored': 'Восстановлен пользователь',
    'user.role_changed': 'Изменена роль',
    'user.updated': 'Обновлён пользователь',
  },
  fieldLabels: {
    login: 'Логин',
    name: 'Имя',
    role: 'Роль',
    is_active: 'Активен',
  },
  formatValue: (field, value) =>
    field === 'role' && typeof value === 'string' && value in roleLabels
      ? roleLabels[value as Role]
      : undefined,
}
