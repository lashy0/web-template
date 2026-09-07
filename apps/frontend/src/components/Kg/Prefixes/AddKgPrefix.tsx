import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { PlusIcon } from 'lucide-react'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'

import { Button } from '@web-app/ui/components/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@web-app/ui/components/dialog'
import { Field, FieldError, FieldGroup, FieldLabel } from '@web-app/ui/components/field'
import { Input } from '@web-app/ui/components/input'
import { Spinner } from '@web-app/ui/components/spinner'

import {
  createKgPrefix,
  kgPrefixErrorCode,
  kgPrefixErrorMessage,
  type CreateKgPrefixInput,
} from '@/features/kg/kg-prefixes-api'
import { createKgPrefixSchema } from '@/features/kg/kg-prefix-form-schema'
import { formatDevEuiPrefix, normalizeDevEuiPrefix } from '@/features/kg/kg-prefix-format'
import useCustomToast from '@/hooks/useCustomToast'

type CreateKgPrefixForm = Readonly<{ name: string; prefix: string; short_code: string }>

const initialForm: CreateKgPrefixForm = { name: '', prefix: '', short_code: '' }

export function AddKgPrefix() {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const form = useForm<CreateKgPrefixForm>({
    defaultValues: initialForm,
    mode: 'onBlur',
    reValidateMode: 'onBlur',
    resolver: zodResolver(createKgPrefixSchema),
  })
  const mutation = useMutation({
    mutationFn: (data: CreateKgPrefixForm) => createKgPrefix(toInput(data)),
    onError: (error) => {
      const message = kgPrefixErrorMessage(error)
      if (kgPrefixErrorCode(error) === 'kg_dev_eui_prefix_conflict') {
        form.setError('prefix', { message, type: 'server' }, { shouldFocus: true })
        form.setError('short_code', { message, type: 'server' })
        return
      }
      showErrorToast(
        'Не удалось создать префикс',
        message ?? 'Проверьте данные и попробуйте ещё раз.',
      )
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['kg', 'prefixes'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      close(true)
      showSuccessToast('Префикс создан', 'DevEUI-префикс успешно добавлен.')
    },
  })

  function close(force = false) {
    if (mutation.isPending && !force) return
    form.reset(initialForm)
    setOpen(false)
  }

  return (
    <Dialog onOpenChange={(nextOpen) => (nextOpen ? setOpen(true) : close())} open={open}>
      <DialogTrigger render={<Button className="cursor-pointer self-start sm:self-auto" />}>
        <PlusIcon data-icon="inline-start" />
        Добавить
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg" showCloseButton={!mutation.isPending}>
        <form
          autoComplete="off"
          className="flex flex-col gap-5"
          noValidate
          onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
        >
          <DialogHeader>
            <DialogTitle>Новый DevEUI-префикс</DialogTitle>
            <DialogDescription>Задайте название, префикс и короткий код.</DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <FormInput
              clearErrors={form.clearErrors}
              control={form.control}
              id="new-kg-prefix-name"
              label="Название"
              name="name"
            />
            <DevEuiPrefixInput
              clearErrors={form.clearErrors}
              control={form.control}
              id="new-kg-prefix-prefix"
            />
            <FormInput
              clearErrors={form.clearErrors}
              control={form.control}
              id="new-kg-prefix-short-code"
              label="Короткий код"
              name="short_code"
              required
            />
          </FieldGroup>
          <DialogFooter>
            <Button
              disabled={mutation.isPending}
              onClick={() => close()}
              type="button"
              variant="outline"
            >
              Отмена
            </Button>
            <Button disabled={mutation.isPending} type="submit">
              {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
              {mutation.isPending ? 'Создание…' : 'Создать'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function DevEuiPrefixInput({
  clearErrors,
  control,
  id,
}: Readonly<{
  clearErrors: (name: keyof CreateKgPrefixForm) => void
  control: ReturnType<typeof useForm<CreateKgPrefixForm>>['control']
  id: string
}>) {
  return (
    <Controller
      control={control}
      name="prefix"
      render={({ field, fieldState }) => (
        <Field data-invalid={fieldState.invalid}>
          <FieldLabel className="cursor-pointer" htmlFor={id}>
            <span>
              Префикс DevEUI
              <span aria-hidden="true" className="ml-0.5 text-destructive">
                *
              </span>
            </span>
          </FieldLabel>
          <Input
            {...field}
            aria-invalid={fieldState.invalid}
            autoCapitalize="none"
            className="font-mono tracking-[0.16em]"
            id={id}
            inputMode="text"
            onChange={(event) => {
              if (fieldState.error?.type === 'server') clearErrors('prefix')
              field.onChange(normalizeDevEuiPrefix(event.currentTarget.value))
            }}
            placeholder="aa bb cc dd ee"
            spellCheck={false}
            value={formatDevEuiPrefix(field.value)}
          />
          {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
        </Field>
      )}
    />
  )
}

function FormInput({
  clearErrors,
  control,
  id,
  label,
  name,
  required = false,
}: Readonly<{
  clearErrors: (name: keyof CreateKgPrefixForm) => void
  control: ReturnType<typeof useForm<CreateKgPrefixForm>>['control']
  id: string
  label: string
  name: keyof CreateKgPrefixForm
  required?: boolean
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
              {required ? (
                <span aria-hidden="true" className="ml-0.5 text-destructive">
                  *
                </span>
              ) : null}
            </span>
          </FieldLabel>
          <Input
            {...field}
            aria-invalid={fieldState.invalid}
            id={id}
            onChange={(event) => {
              if (fieldState.error?.type === 'server') clearErrors(name)
              field.onChange(event)
            }}
          />
          {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
        </Field>
      )}
    />
  )
}

function toInput(data: CreateKgPrefixForm): CreateKgPrefixInput {
  return {
    name: data.name.trim() || null,
    prefix: data.prefix.trim().toLowerCase(),
    short_code: data.short_code.trim().toLowerCase(),
  }
}
