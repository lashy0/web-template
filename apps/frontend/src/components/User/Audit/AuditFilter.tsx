import { CalendarRangeIcon } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@web-app/ui/components/button'
import { Calendar, calendarRuLocale } from '@web-app/ui/components/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@web-app/ui/components/popover'
import {
  formatDatePeriod,
  getDatePeriodPreset,
  toCalendarDateRange,
  toDatePeriod,
  type DatePeriod,
  type DatePeriodSelection,
} from '@/lib/date'

export type { DatePeriod as AuditPeriod } from '@/lib/date'

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
  const isCompletePeriod = Boolean(from && to && from <= to)
  const selected = toCalendarDateRange(from, to)

  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) {
      setFrom(value?.from ?? '')
      setTo(value?.to ?? '')
    }
    setOpen(nextOpen)
  }

  const reset = () => {
    setFrom('')
    setTo('')
    onApply(null)
    setOpen(false)
  }

  const apply = () => {
    if (!isCompletePeriod) {
      return
    }
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
            {value ? formatDatePeriod(value) : 'Период'}
          </Button>
        }
      />
      <PopoverContent align="start" className="w-fit max-w-[calc(100vw-2rem)] p-4">
        <div className="flex flex-col gap-4">
          <div>
            <h2 className="text-sm font-semibold">Период</h2>
            <p className="mt-1 text-sm text-muted-foreground">Выберите даты для журнала.</p>
          </div>
          <div className="grid grid-cols-2 gap-2" aria-label="Быстрый выбор периода">
            <Button
              className="cursor-pointer"
              onClick={() => setPeriod(getDatePeriodPreset(1), setFrom, setTo)}
              size="sm"
              variant="secondary"
            >
              Сегодня
            </Button>
            <Button
              className="cursor-pointer"
              onClick={() => setPeriod(getDatePeriodPreset(7), setFrom, setTo)}
              size="sm"
              variant="secondary"
            >
              Последние 7 дней
            </Button>
            <Button
              className="col-span-2 justify-self-start cursor-pointer"
              onClick={() => setPeriod(getDatePeriodPreset(30), setFrom, setTo)}
              size="sm"
              variant="secondary"
            >
              Последние 30 дней
            </Button>
          </div>
          <Calendar
            captionLayout="dropdown"
            defaultMonth={selected?.from}
            locale={calendarRuLocale}
            mode="range"
            onSelect={(range) => setPeriod(toDatePeriod(range), setFrom, setTo)}
            selected={selected}
            timeZone={Intl.DateTimeFormat().resolvedOptions().timeZone}
          />
          <div className="flex items-center justify-end gap-3">
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

function setPeriod(
  period: DatePeriodSelection | null,
  setFrom: (value: string) => void,
  setTo: (value: string) => void,
) {
  setFrom(period?.from ?? '')
  setTo(period?.to ?? '')
}
