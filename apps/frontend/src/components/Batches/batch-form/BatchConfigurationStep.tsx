import { FieldGroup } from '@web-app/ui/components/field'

import { BatchDevEuiRange } from './BatchDevEuiRange'
import { SelectField } from './BatchFormFields'
import {
  activationTypeOptions,
  lorawanVersionOptions,
  type BatchFormControl,
  type SelectOptionsState,
} from './types'

import type { DevEuiRangePreview } from '@/features/batches/batches-api'

export function BatchConfigurationStep({
  control,
  plannedQty,
  prefixes,
  range,
  rangeLoading,
  selectedPrefix,
  versions,
}: Readonly<{
  control: BatchFormControl
  plannedQty: number
  prefixes: SelectOptionsState
  range: DevEuiRangePreview | undefined
  rangeLoading: boolean
  selectedPrefix: string
  versions: SelectOptionsState
}>) {
  return (
    <div className="flex flex-col gap-4">
      <FieldGroup className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <SelectField
          control={control}
          id="new-batch-prefix"
          {...prefixes}
          label="DevEUI-префикс"
          name="devEuiPrefix"
          placeholder="Выберите префикс"
        />
        <SelectField
          control={control}
          id="new-batch-version"
          {...versions}
          label="Версия КГ"
          name="kgVersionId"
          placeholder="Не выбрана"
        />
        <SelectField
          control={control}
          id="new-batch-activation-type"
          items={activationTypeOptions}
          label="Тип активации"
          name="activationType"
          placeholder="Не выбран"
        />
        <SelectField
          control={control}
          id="new-batch-lorawan-version"
          items={lorawanVersionOptions}
          label="Версия LoRaWAN"
          name="lorawanVersion"
          placeholder="Не выбрана"
        />
      </FieldGroup>
      <BatchDevEuiRange
        plannedCount={plannedQty}
        prefix={selectedPrefix}
        range={range}
        rangeLoading={rangeLoading}
      />
    </div>
  )
}
