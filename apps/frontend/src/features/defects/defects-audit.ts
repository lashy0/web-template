import type { AuditSection } from '@/features/audit/audit'

export const defectAudit: AuditSection = {
  title: 'Аудит дефектов',
  loadingLabel: 'Загрузка аудита дефектов',
  targetTypes: ['defect_group', 'defect_type'],
  targetHeader: 'Объект',
  targetTypeLabels: { defect_group: 'Группа', defect_type: 'Тип' },
  actionLabels: {
    'defect_group.archived': 'Архивирована группа',
    'defect_group.created': 'Создана группа',
    'defect_group.deleted': 'Удалена группа',
    'defect_group.restored': 'Восстановлена группа',
    'defect_group.updated': 'Обновлена группа',
    'defect_type.archived': 'Архивирован тип',
    'defect_type.created': 'Создан тип',
    'defect_type.deleted': 'Удалён тип',
    'defect_type.restored': 'Восстановлен тип',
    'defect_type.updated': 'Обновлён тип',
  },
  fieldLabels: {
    name: 'Название',
    description: 'Описание',
    possible_cause: 'Возможная причина',
    engineer_action: 'Действия инженера',
  },
}
