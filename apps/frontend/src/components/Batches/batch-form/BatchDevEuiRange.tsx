import {
  ArrowRightIcon,
  CpuIcon,
  InfoIcon,
} from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@web-app/ui/components/alert'
import { Spinner } from '@web-app/ui/components/spinner'

import { formatDevEui } from '@/features/kg/kg-prefix-format'

import type { DevEuiRangePreview } from '@/features/batches/batches-api'

export function BatchDevEuiRange({
  plannedCount,
  prefix,
  range,
  rangeLoading,
}: Readonly<{
  plannedCount: number
  prefix: string
  range: DevEuiRangePreview | undefined
  rangeLoading: boolean
}>) {
  const isReady = prefix.length > 0 && Number.isInteger(plannedCount) && plannedCount > 0

  if (!isReady) {
    return (
      <Alert>
        <InfoIcon />
        <AlertDescription>
          Выберите DevEUI-префикс, чтобы рассчитать диапазон.
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <section aria-labelledby="dev-eui-range-heading" className="rounded-xl border bg-muted/30 p-4">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-base font-semibold" id="dev-eui-range-heading">
          Предварительный диапазон DevEUI
        </h3>
        {range ? (
          <p className="shrink-0 text-sm text-muted-foreground">
            {plannedCount.toLocaleString('ru-RU')} {deviceCountLabel(plannedCount)}
          </p>
        ) : null}
      </div>
      {range ? (
        <dl className="mt-4 grid grid-cols-1 items-end gap-3 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
          <div className="min-w-0">
            <dt className="text-xs font-medium text-muted-foreground">Первый DevEUI</dt>
            <dd className="mt-1 rounded-md bg-muted px-2 py-1.5 font-mono text-xs whitespace-nowrap">
              {formatDevEui(range.firstDevEui)}
            </dd>
          </div>
          <div aria-hidden="true" className="mb-1 hidden text-muted-foreground sm:block">
            <ArrowRightIcon />
          </div>
          <div className="min-w-0">
            <dt className="text-xs font-medium text-muted-foreground">Последний DevEUI</dt>
            <dd className="mt-1 rounded-md bg-muted px-2 py-1.5 font-mono text-xs whitespace-nowrap">
              {formatDevEui(range.lastDevEui)}
            </dd>
          </div>
        </dl>
      ) : (
        <Alert className="mt-4">
          {rangeLoading ? <Spinner /> : <CpuIcon />}
          <AlertTitle>
            {rangeLoading ? 'Рассчитываем диапазон' : 'Не удалось рассчитать диапазон'}
          </AlertTitle>
          <AlertDescription>
            {rangeLoading
              ? 'Проверяем свободные DevEUI для выбранного префикса.'
              : 'Повторите выбор префикса или попробуйте снова позже.'}
          </AlertDescription>
        </Alert>
      )}
    </section>
  )
}

function deviceCountLabel(count: number): string {
  const lastTwoDigits = count % 100
  const lastDigit = count % 10

  if (lastTwoDigits >= 11 && lastTwoDigits <= 14) return 'устройств'
  if (lastDigit === 1) return 'устройство'
  if (lastDigit >= 2 && lastDigit <= 4) return 'устройства'
  return 'устройств'
}
