import { CheckIcon } from 'lucide-react'

import { Separator } from '@web-app/ui/components/separator'

import type { FormStep } from './types'

export function BatchStepIndicator({ activeStep }: Readonly<{ activeStep: FormStep }>) {
  return (
    <ol
      aria-label="Шаги создания партии"
      className="mb-6 flex items-center gap-3 sm:gap-5"
    >
      <li className="flex min-w-0 items-center gap-3">
        <StepNumber complete={activeStep === 2} current={activeStep === 1} number={1} />
        {activeStep === 1 ? (
          <StepDescription subtitle="Основная информация" title="Параметры партии" />
        ) : null}
      </li>
      <li aria-hidden="true" className="w-10 shrink-0 sm:w-16">
        <Separator className="bg-primary" />
      </li>
      <li className="flex min-w-0 items-center gap-3">
        <StepNumber current={activeStep === 2} number={2} />
        {activeStep === 2 ? (
          <StepDescription subtitle="Технические параметры" title="Конфигурация КГ" />
        ) : null}
      </li>
    </ol>
  )
}

function StepNumber({
  complete = false,
  current = false,
  number,
}: Readonly<{ complete?: boolean; current?: boolean; number: number }>) {
  return (
    <span
      aria-current={current ? 'step' : undefined}
      className="flex size-10 shrink-0 items-center justify-center rounded-full border text-sm font-semibold data-[current=true]:border-primary data-[current=true]:bg-primary data-[current=true]:text-primary-foreground sm:size-12"
      data-current={current}
    >
      {complete ? <CheckIcon aria-label="Шаг завершён" /> : number}
    </span>
  )
}

function StepDescription({ subtitle, title }: Readonly<{ subtitle: string; title: string }>) {
  return (
    <div className="min-w-0">
      <p className="truncate text-sm font-medium">{title}</p>
      <p className="truncate text-xs text-muted-foreground sm:text-sm">{subtitle}</p>
    </div>
  )
}
