import { CalendarRangeIcon } from 'lucide-react'
import { useState, useSyncExternalStore } from 'react'

import { Button } from '@web-app/ui/components/button'
import { Calendar, calendarRuLocale } from '@web-app/ui/components/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@web-app/ui/components/popover'
import { Separator } from '@web-app/ui/components/separator'
import {
  formatDatePeriod,
  getDatePeriodPreset,
  toCalendarDateRange,
  toDatePeriod,
  type DatePeriod,
  type DatePeriodSelection,
} from '@/lib/date'

const compactQuery = '(max-width: 767px)'
function subscribeToViewport(callback: () => void) {
  const media = window.matchMedia(compactQuery)
  media.addEventListener('change', callback)
  return () => media.removeEventListener('change', callback)
}
function getCompactSnapshot() {
  return window.matchMedia(compactQuery).matches
}
function getServerSnapshot() {
  return true
}

function getPresets() {
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const monthStart = new Date(today.getFullYear(), today.getMonth(), 1)
  const previousStart = new Date(today.getFullYear(), today.getMonth() - 1, 1)
  const previousEnd = new Date(today.getFullYear(), today.getMonth(), 0)
  return [
    { label: 'Сегодня', period: getDatePeriodPreset(1, today) },
    { label: 'Вчера', period: getDatePeriodPreset(1, yesterday) },
    { label: 'Последние 7 дней', period: getDatePeriodPreset(7, today) },
    { label: 'Последние 30 дней', period: getDatePeriodPreset(30, today) },
    {
      label: 'Текущий месяц',
      period: {
        from: getDatePeriodPreset(1, monthStart).from,
        to: getDatePeriodPreset(1, today).to,
      },
    },
    {
      label: 'Прошлый месяц',
      period: {
        from: getDatePeriodPreset(1, previousStart).from,
        to: getDatePeriodPreset(1, previousEnd).to,
      },
    },
  ]
}

export function AuditFilter({
  onApply,
  value,
}: Readonly<{
  onApply: (period: DatePeriod | null) => void
  value: DatePeriod | null
}>) {
  const [open, setOpen] = useState(false)
  const [from, setFrom] = useState(value?.from ?? '')
  const [to, setTo] = useState(value?.to ?? '')
  const [month, setMonth] = useState(
    () => toCalendarDateRange(value?.from ?? '', '')?.from ?? new Date(),
  )
  const compact = useSyncExternalStore(subscribeToViewport, getCompactSnapshot, getServerSnapshot)
  const isCompletePeriod = Boolean(from && to && from <= to)
  const selected = toCalendarDateRange(from, to)
  const presets = getPresets()
  const appliedLabel = value ? formatDatePeriod(value) : 'Период'

  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) {
      setFrom(value?.from ?? '')
      setTo(value?.to ?? '')
      setMonth(toCalendarDateRange(value?.from ?? '', '')?.from ?? new Date())
    }
    setOpen(nextOpen)
  }

  const selectPeriod = (period: DatePeriodSelection | null) => {
    setFrom(period?.from ?? '')
    setTo(period?.to ?? '')
  }

  const reset = () => {
    selectPeriod(null)
    onApply(null)
    setOpen(false)
  }

  const apply = () => {
    if (!isCompletePeriod) return
    onApply({ from, to })
    setOpen(false)
  }

  return (
    <Popover onOpenChange={handleOpenChange} open={open}>
      <PopoverTrigger
        aria-label={value ? `Период: ${formatDatePeriod(value)}` : 'Период'}
        render={
          <Button className="cursor-pointer" variant="outline">
            <CalendarRangeIcon data-icon="inline-start" />
            {appliedLabel}
          </Button>
        }
      />
      <PopoverContent
        align="start"
        aria-label="Выбор периода"
        className="w-fit max-w-[calc(100vw-2rem)] overflow-y-auto p-0 max-h-[calc(100dvh-2rem)]"
      >
        <div className="flex flex-col md:flex-row">
          <div className="flex flex-col gap-3 p-3 md:w-44 md:shrink-0 md:p-4">
            <h2 className="text-sm font-semibold">Период</h2>
            <div
              className="grid grid-cols-2 gap-1 md:grid-cols-1"
              aria-label="Быстрый выбор периода"
            >
              {presets.map(({ label, period }) => (
                <Button
                  key={label}
                  className="cursor-pointer justify-start"
                  onClick={() => {
                    selectPeriod(period)
                    setMonth(toCalendarDateRange(period.from, period.to)!.from!)
                  }}
                  size="sm"
                  variant="ghost"
                >
                  {label}
                </Button>
              ))}
            </div>
          </div>
          <Separator orientation={compact ? 'horizontal' : 'vertical'} />
          <div className="flex justify-center p-3">
            <Calendar
              classNames={{
                months: 'relative flex flex-row gap-6',
                range_start: 'rounded-l-full bg-primary/10',
                range_middle: 'rounded-none bg-primary/10',
                range_end: 'rounded-r-full bg-primary/10',
              }}
              className="[&_[data-range-start=true]]:rounded-full [&_[data-range-end=true]]:rounded-full [&_[data-range-middle=true]]:bg-primary/10"
              fixedWeeks
              locale={calendarRuLocale}
              mode="range"
              month={month}
              numberOfMonths={compact ? 1 : 2}
              onMonthChange={setMonth}
              onSelect={(range) => selectPeriod(toDatePeriod(range))}
              selected={selected}
              showOutsideDays={false}
              timeZone={Intl.DateTimeFormat().resolvedOptions().timeZone}
              weekStartsOn={1}
            />
          </div>
        </div>
        <Separator />
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 md:px-4">
          <p aria-live="polite" className="text-sm text-muted-foreground">
            {isCompletePeriod
              ? formatDatePeriod({ from, to })
              : from
                ? 'Выберите конечную дату'
                : 'Выберите начало и конец периода'}
          </p>
          <div className="ml-auto flex items-center gap-2">
            <Button className="cursor-pointer" onClick={reset} size="sm" variant="ghost">
              Сбросить
            </Button>
            <Button
              className="cursor-pointer disabled:cursor-not-allowed"
              disabled={!isCompletePeriod}
              onClick={apply}
              size="sm"
            >
              Применить
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
