export type DatePeriod = Readonly<{
  from: string
  to: string
}>

export type DatePeriodSelection = Readonly<{
  from: string
  to?: string
}>

export type CalendarDateRange = Readonly<{
  from: Date | undefined
  to?: Date
}>

const dateFormatter = new Intl.DateTimeFormat('ru-RU', {
  day: 'numeric',
  month: 'short',
})

const dateTimeFormatter = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

export function formatDatePeriod(period: DatePeriod): string {
  return `${formatDate(period.from)} — ${formatDate(period.to)}`
}

export function formatDateTime(value: string): string {
  return dateTimeFormatter.format(new Date(value))
}

export function getDatePeriodPreset(days: number, today = new Date()): DatePeriod {
  const to = new Date(today)
  const from = new Date(today)
  from.setDate(from.getDate() - days + 1)

  return {
    from: toDateInput(from),
    to: toDateInput(to),
  }
}

export function toCalendarDateRange(from: string, to: string): CalendarDateRange | undefined {
  if (!from) {
    return undefined
  }

  return {
    from: toLocalDate(from),
    to: to ? toLocalDate(to) : undefined,
  }
}

export function toDatePeriod(range: CalendarDateRange | undefined): DatePeriodSelection | null {
  if (!range?.from) {
    return null
  }

  return {
    from: toDateInput(range.from),
    to: range.to ? toDateInput(range.to) : undefined,
  }
}

export function toExclusiveUtcDateRange(
  period: DatePeriod,
): Readonly<{ from: string; to: string }> {
  const from = new Date(`${period.from}T00:00:00`)
  const to = new Date(`${period.to}T00:00:00`)
  to.setDate(to.getDate() + 1)

  return {
    from: from.toISOString(),
    to: to.toISOString(),
  }
}

function formatDate(value: string): string {
  return dateFormatter.format(toLocalDate(value))
}

function toDateInput(value: Date): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')

  return `${year}-${month}-${day}`
}

function toLocalDate(value: string): Date {
  return new Date(`${value}T12:00:00`)
}
