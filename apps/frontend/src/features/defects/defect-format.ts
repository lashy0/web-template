import { type DefectGroup } from '@/features/defects/defects-api'

export function defectGroupLabel(group: Pick<DefectGroup, 'code' | 'name'>): string {
  return `${group.code} (${group.name})`
}
