import { Controller } from 'react-hook-form'

import { Field, FieldError, FieldGroup, FieldLabel } from '@web-app/ui/components/field'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupText,
  InputGroupTextarea,
} from '@web-app/ui/components/input-group'
import { SelectField, TextField } from './BatchFormFields'
import type { BatchFormControl, SelectOptionsState } from './types'

const textLimit = 2000

export function BatchParametersStep({
  control,
  orders,
}: Readonly<{
  control: BatchFormControl
  orders: SelectOptionsState
}>) {
  return (
    <FieldGroup>
      <TextField
        control={control}
        id="new-batch-name"
        label="Название"
        name="name"
        placeholder="Например, Партия сентябрь 2026"
        required
      />
      <SelectField
        control={control}
        id="new-batch-order"
        label="Производственный заказ"
        name="productionOrderId"
        placeholder="Не выбран"
        required={false}
        {...orders}
      />
      <FieldGroup className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TextField
          control={control}
          id="new-batch-plan"
          label="План"
          name="plannedQty"
          required
          type="number"
        />
        <TextField
          control={control}
          id="new-batch-day-plan"
          label="Дневной план"
          name="dayPlanQty"
          required
          type="number"
        />
      </FieldGroup>
      <Controller
        control={control}
        name="description"
        render={({ field, fieldState }) => (
          <Field data-invalid={fieldState.invalid}>
            <FieldLabel className="cursor-pointer" htmlFor="new-batch-description">
              Описание
            </FieldLabel>
            <InputGroup>
              <InputGroupTextarea
                {...field}
                aria-invalid={fieldState.invalid}
                className="field-sizing-fixed h-24"
                id="new-batch-description"
                maxLength={textLimit}
                placeholder="Введите описание партии, цели, особенности…"
              />
              <InputGroupAddon align="block-end">
                <InputGroupText className="text-xs font-normal tabular-nums">
                  {field.value.length} / {textLimit}
                </InputGroupText>
              </InputGroupAddon>
            </InputGroup>
            {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
          </Field>
        )}
      />
    </FieldGroup>
  )
}
