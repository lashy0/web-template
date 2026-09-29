/** Whether an account or a device may work, as the `active` list filter and the status column show it. */
export type Activity = 'active' | 'inactive'

export const activities = ['active', 'inactive'] as const satisfies readonly Activity[]

export const activityLabels: Readonly<Record<Activity, string>> = {
  active: 'Активен',
  inactive: 'Неактивен',
}

export const activityFilterOptions: readonly Readonly<{
  label: string
  value: Activity | 'all'
}>[] = [
  { label: 'Все статусы', value: 'all' },
  ...activities.map((value) => ({ label: activityLabels[value], value })),
]

export function activityOf(item: Readonly<{ isActive: boolean }>): Activity {
  return item.isActive ? 'active' : 'inactive'
}

/** The `active` query parameter for a status filter; current lists only. */
export function activeFilter(archived: boolean, status: Activity | 'all'): boolean | undefined {
  return !archived && status !== 'all' ? status === 'active' : undefined
}
