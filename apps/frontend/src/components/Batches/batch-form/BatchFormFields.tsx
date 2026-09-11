import { Button } from '@web-app/ui/components/button'
import { Controller } from 'react-hook-form'

import { Field, FieldDescription, FieldError, FieldLabel } from '@web-app/ui/components/field'
import { Input } from '@web-app/ui/components/input'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@web-app/ui/components/select'

import type { BatchFormControl, SelectOption } from './types'

import { normalizePositiveIntegerInput } from '@/features/batches/batch-form-schema'

export function TextField({
  control,
  id,
  label,
  name,
  placeholder,
  required = false,
  type = 'text',
}: Readonly<{
  control: BatchFormControl
  id: string
  label: string
  name: 'name' | 'plannedQty' | 'dayPlanQty'
  placeholder?: string
  required?: boolean
  type?: 'number' | 'text'
}>) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => (
        <Field data-invalid={fieldState.invalid}>
          <FieldLabel className="cursor-pointer" htmlFor={id}>
            <span>
              {label}
              {required ? <RequiredMark /> : null}
            </span>
          </FieldLabel>
          <Input
            {...field}
            aria-invalid={fieldState.invalid}
            id={id}
            inputMode={type === 'number' ? 'numeric' : undefined}
            onChange={(event) =>
              field.onChange(
                type === 'number'
                  ? normalizePositiveIntegerInput(event.currentTarget.value)
                  : event,
              )
            }
            pattern={type === 'number' ? '[1-9][0-9]*' : undefined}
            placeholder={placeholder}
            required={required}
            type={type === 'number' ? 'text' : type}
          />
          {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
        </Field>
      )}
    />
  )
}

export function SelectField({
  control,
  id,
  items,
  label,
  loading = false,
  error = false,
  retry,
  name,
  placeholder,
  required = true,
}: Readonly<{
  control: BatchFormControl
  id: string
  items: readonly SelectOption[]
  label: string
  loading?: boolean
  error?: boolean
  retry?: () => void
  name: 'activationType' | 'devEuiPrefix' | 'kgVersionId' | 'lorawanVersion' | 'productionOrderId'
  placeholder: string
  required?: boolean
}>) {
  const options = required ? items : [{ label: placeholder, value: '' }, ...items]
  const disabled = loading || (required && items.length === 0)
  const status = loading
    ? 'Загрузка…'
    : error
      ? 'Не удалось загрузить список.'
      : items.length === 0
        ? 'Нет доступных вариантов.'
        : undefined

  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => (
        <Field data-disabled={disabled} data-invalid={fieldState.invalid}>
          <FieldLabel className="cursor-pointer" htmlFor={id}>
            <span>
              {label}
              {required ? <RequiredMark /> : null}
            </span>
          </FieldLabel>
          <Select
            disabled={disabled}
            items={options}
            name={field.name}
            onValueChange={(value) => {
              field.onChange(value ?? '')
              field.onBlur()
            }}
            value={field.value || (required ? null : '')}
          >
            <SelectTrigger
              aria-describedby={status ? id + '-status' : undefined}
              aria-invalid={fieldState.invalid}
              aria-required={required}
              className="w-full"
              id={id}
              ref={field.ref}
            >
              <SelectValue className="min-w-0 truncate" placeholder={placeholder} />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {options.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
          {status ? (
            <FieldDescription id={id + '-status'} aria-live="polite">
              {status}
              {error && !loading && retry ? (
                <Button className="ml-1" onClick={retry} size="sm" type="button" variant="link">
                  Повторить
                </Button>
              ) : null}
            </FieldDescription>
          ) : null}
          {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
        </Field>
      )}
    />
  )
}

export function RequiredMark() {
  return (
    <span aria-hidden="true" className="ml-0.5 text-destructive">
      *
    </span>
  )
}
