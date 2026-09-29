import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createKgPrefixMutation } from '@web-app/api-client'
import { PlusIcon } from 'lucide-react'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import type { z } from 'zod'

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
  invalidateKgPrefixQueries,
  isKgPrefixShortCodeTakenError,
  isKgPrefixTakenError,
} from '@/features/kg/kg-prefixes-api'
import { createKgPrefixSchema, kgPrefixFormMessages } from '@/features/kg/kg-prefix-form-schema'
import { formatDevEuiPrefix, normalizeDevEuiPrefix } from '@/features/kg/kg-prefix-format'
import useCustomToast from '@/hooks/useCustomToast'

type CreateKgPrefixForm = z.input<typeof createKgPrefixSchema>

const initialForm: CreateKgPrefixForm = { name: '', prefix: '', shortCode: '' }

export function AddKgPrefix() {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const form = useForm<CreateKgPrefixForm, unknown, z.output<typeof createKgPrefixSchema>>({
    defaultValues: initialForm,
    mode: 'onBlur',
    reValidateMode: 'onBlur',
    resolver: zodResolver(createKgPrefixSchema, { error: kgPrefixFormMessages }),
  })
  const mutation = useMutation({
    ...createKgPrefixMutation(),
    onError: (error) => {
      if (isKgPrefixTakenError(error)) {
        form.setError(
          'prefix',
          { message: 'Такой префикс уже зарегистрирован.', type: 'server' },
          { shouldFocus: true },
        )
        return
      }
      if (isKgPrefixShortCodeTakenError(error)) {
        form.setError(
          'shortCode',
          { message: 'Такой короткий код уже используется.', type: 'server' },
          { shouldFocus: true },
        )
        return
      }
      showErrorToast('Не удалось создать префикс', 'Проверьте данные и попробуйте ещё раз.')
    },
    onSuccess: async () => {
      await invalidateKgPrefixQueries(queryClient)
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
      <DialogContent
        className="flex max-h-[calc(100dvh-2rem)] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg"
        showCloseButton={!mutation.isPending}
      >
        <form
          autoComplete="off"
          className="flex min-h-0 flex-1 flex-col"
          noValidate
          onSubmit={form.handleSubmit((body) => mutation.mutate({ body }))}
        >
          <DialogHeader className="shrink-0 px-4 pt-4">
            <DialogTitle>Новый DevEUI-префикс</DialogTitle>
            <DialogDescription>
              Задайте название, префикс и короткий код. Префикс и код потом не изменить.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
            <Controller
              control={form.control}
              name="name"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor="new-kg-prefix-name">
                    Название
                  </FieldLabel>
                  <Input {...field} aria-invalid={fieldState.invalid} id="new-kg-prefix-name" />
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
            />
            <Controller
              control={form.control}
              name="prefix"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor="new-kg-prefix-prefix">
                    <RequiredLabel>Префикс DevEUI</RequiredLabel>
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    autoCapitalize="none"
                    className="font-mono tracking-[0.16em]"
                    id="new-kg-prefix-prefix"
                    inputMode="text"
                    onChange={(event) => {
                      if (fieldState.error?.type === 'server') form.clearErrors('prefix')
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
            <Controller
              control={form.control}
              name="shortCode"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor="new-kg-prefix-short-code">
                    <RequiredLabel>Короткий код</RequiredLabel>
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    id="new-kg-prefix-short-code"
                    onChange={(event) => {
                      if (fieldState.error?.type === 'server') form.clearErrors('shortCode')
                      field.onChange(event)
                    }}
                    required
                  />
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
            />
          </FieldGroup>
          <DialogFooter className="mx-0 mb-0 shrink-0 rounded-b-xl px-4 py-4">
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

function RequiredLabel({ children }: Readonly<{ children: string }>) {
  return (
    <span>
      {children}
      <span aria-hidden="true" className="ml-0.5 text-destructive">
        *
      </span>
    </span>
  )
}
