import type { AuditLogEntry, ListAuditEntriesData } from '@web-app/api-client'

import type { PageSize } from '@/components/Common/DataTable'
import { toExclusiveUtcDateRange, type DatePeriod } from '@/lib/date'
import { listDate, listEnum, listOrder, listPage, listPageSize } from '@/lib/list-search'

export type AuditEntry = AuditLogEntry
export type AuditSort = 'actor_login' | 'created_at'
export type SortOrder = 'asc' | 'desc'

export const auditSorts = ['actor_login', 'created_at'] as const satisfies readonly AuditSort[]

/** One audit page: the entries of some target types and how to describe them. */
export type AuditSection = Readonly<{
  title: string
  /** Accessible name of the loading table, such as «Загрузка аудита пользователей». */
  loadingLabel: string
  targetTypes: readonly string[]
  /** Header of the target column, such as «Учётная запись». */
  targetHeader: string
  /** Prefix of a target in a section with several target types, such as «Группа». */
  targetTypeLabels?: Readonly<Record<string, string>>
  actionLabels: Readonly<Record<string, string>>
  /** Labels of the `details` fields to show, such as «Логин»; other fields stay hidden. */
  fieldLabels: Readonly<Record<string, string>>
  /** Readable text of a field, such as a role label; `undefined` falls back to the value itself. */
  formatValue?: (field: string, value: unknown) => string | undefined
}>

/** A field an update changed, as readable text; null is an empty value. */
export type AuditChange = Readonly<{
  field: string
  label: string
  from: string | null
  to: string | null
}>
/** A field of a created or deleted record, as readable text. */
export type AuditValue = Readonly<{ field: string; label: string; value: string | null }>

export type AuditSearch = Readonly<{
  from?: string
  order?: SortOrder
  page?: number
  pageSize?: PageSize
  sort?: AuditSort
  to?: string
}>

export function validateAuditSearch(search: Record<string, unknown>): AuditSearch {
  const from = listDate(search.from)
  const to = listDate(search.to)
  const period = from && to && from <= to

  return {
    from: period ? from : undefined,
    order: listOrder(search.order),
    page: listPage(search.page),
    pageSize: listPageSize(search.pageSize),
    sort: listEnum(auditSorts, search.sort),
    to: period ? to : undefined,
  }
}

export function auditQuery(
  section: AuditSection,
  search: AuditSearch,
): NonNullable<ListAuditEntriesData['query']> {
  const period: DatePeriod | null =
    search.from && search.to ? { from: search.from, to: search.to } : null
  const range = period ? toExclusiveUtcDateRange(period) : null

  return {
    createdAfter: range?.from,
    createdBefore: range?.to,
    currentPage: search.page ?? 1,
    orderBy: search.sort ?? 'created_at',
    pageSize: search.pageSize ?? 25,
    sortOrder: search.order ?? (search.sort && search.sort !== 'created_at' ? 'asc' : 'desc'),
    targetTypeIn: [...section.targetTypes],
  }
}

/** Who acted: a user's login, `cli` for `otk` commands, or the code of a PAK. */
export function actorLabel(entry: Pick<AuditEntry, 'actorId' | 'actorLogin'>): string {
  if (entry.actorId === null && entry.actorLogin === 'cli') {
    return 'Командная строка'
  }
  return entry.actorLogin ?? '—'
}

export function actionLabel(section: AuditSection, action: string): string {
  return section.actionLabels[action] ?? action
}

export function targetLabel(section: AuditSection, entry: AuditEntry): string {
  const label = entry.targetLabel ?? entry.targetId ?? '—'
  const type = entry.targetType ? section.targetTypeLabels?.[entry.targetType] : undefined
  return type ? `${type}: ${label}` : label
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** The value as text; null for an empty value, which is shown as «—». */
export function auditValueText(
  section: AuditSection,
  field: string,
  value: unknown,
): string | null {
  if (value === null || value === undefined || value === '') {
    return null
  }
  const formatted = section.formatValue?.(field, value)
  if (formatted !== undefined) {
    return formatted
  }
  if (typeof value === 'boolean') {
    return value ? 'да' : 'нет'
  }
  return typeof value === 'string' ? value : JSON.stringify(value)
}

/**
 * The fields an update changed, from details such as
 * `{"changes": {"name": {"from": "Иван", "to": "Пётр"}}}`, in the section's field order.
 */
export function auditChanges(section: AuditSection, entry: AuditEntry): AuditChange[] {
  const changes = entry.details?.changes
  if (!isRecord(changes)) {
    return []
  }
  return Object.entries(section.fieldLabels).flatMap(([field, label]) => {
    const change = changes[field]
    return isRecord(change)
      ? [
          {
            field,
            label,
            from: auditValueText(section, field, change.from),
            to: auditValueText(section, field, change.to),
          },
        ]
      : []
  })
}

/** The labelled fields of the details of an entry without changes, such as a created record. */
export function auditValues(section: AuditSection, entry: AuditEntry): AuditValue[] {
  const details = entry.details
  if (!details || 'changes' in details) {
    return []
  }
  return Object.entries(section.fieldLabels).flatMap(([field, label]) =>
    field in details
      ? [{ field, label, value: auditValueText(section, field, details[field]) }]
      : [],
  )
}

const browsers = [
  ['Edge', /Edg\/(\d+)/],
  ['Opera', /OPR\/(\d+)/],
  ['Яндекс Браузер', /YaBrowser\/(\d+)/],
  ['Firefox', /Firefox\/(\d+)/],
  ['Chrome', /Chrome\/(\d+)/],
  ['Safari', /Version\/(\d+).*Safari/],
] as const
const systems = [
  ['Android', /Android/],
  ['iOS', /iPhone|iPad/],
  ['Windows', /Windows/],
  ['macOS', /Mac OS X/],
  ['Linux', /Linux/],
] as const

/** «Chrome 141, Windows» for a browser's user agent; other clients as they are. */
export function describeUserAgent(userAgent: string): string {
  const browser = browsers.find(([, pattern]) => pattern.test(userAgent))
  if (!browser) {
    return userAgent
  }
  const [name, pattern] = browser
  const version = pattern.exec(userAgent)?.[1]
  const system = systems.find(([, systemPattern]) => systemPattern.test(userAgent))?.[0]
  return [version ? `${name} ${version}` : name, system].filter(Boolean).join(', ')
}
