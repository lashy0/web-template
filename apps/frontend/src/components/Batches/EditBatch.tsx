import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { updateBatch } from '@web-app/api-client'
import { useEffect, useMemo } from 'react'
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
} from '@web-app/ui/components/dialog'
import { Field, FieldError, FieldGroup, FieldLabel } from '@web-app/ui/components/field'
import { Input } from '@web-app/ui/components/input'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupText,
  InputGroupTextarea,
} from '@web-app/ui/components/input-group'
import { Spinner } from '@web-app/ui/components/spinner'

import {
  invalidateBatchQueries,
  isBatchEditWindowExpiredError,
  type Batch,
} from '@/features/batches/batches-api'
import {
  editBatchFormSchema,
  normalizePositiveIntegerInput,
} from '@/features/batches/batch-form-schema'
import useCustomToast from '@/hooks/useCustomToast'
import { changedFields, hasChanges } from '@/lib/changes'

type EditBatchForm = z.input<typeof editBatchFormSchema>

const textLimit = 2000

export function EditBatch({
  batch,
  onOpenChange,
  onSuccess,
  open,
}: Readonly<{
  batch: Batch
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
}>) {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const initialValues = useMemo(
    () => ({
      dayPlanQty: String(batch.dayPlanQty),
      description: batch.description ?? '',
      name: batch.name,
    }),
    [batch.dayPlanQty, batch.description, batch.name],
  )
  const form = useForm<EditBatchForm, unknown, z.output<typeof editBatchFormSchema>>({
    defaultValues: initialValues,
    mode: 'onChange',
    reValidateMode: 'onChange',
    resolver: zodResolver(editBatchFormSchema),
  })
  useEffect(() => {
    if (open) form.reset(initialValues)
  }, [form, initialValues, open])
  const mutation = useMutation({
    mutationFn: async (data: z.output<typeof editBatchFormSchema>) => {
      const body = changedFields(batch, data)
      if (hasChanges(body)) {
        await updateBatch({ body, path: { batch_id: batch.id }, throwOnError: true })
      }
    },
    onError: (error) =>
      showErrorToast(
        'Не удалось изменить партию',
        isBatchEditWindowExpiredError(error)
          ? 'Партию можно изменить только в течение часа после создания.'
          : 'Проверьте данные и попробуйте ещё раз.',
      ),
    onSuccess: async () => {
      await invalidateBatchQueries(queryClient)
      onOpenChange(false)
      onSuccess()
      showSuccessToast('Партия изменена', `Данные «${batch.name}» сохранены.`)
    },
  })

  function close() {
    if (!mutation.isPending) onOpenChange(false)
  }

  return (
    <Dialog onOpenChange={(nextOpen) => (nextOpen ? onOpenChange(true) : close())} open={open}>
      <DialogContent
        className="flex max-h-[calc(100dvh-2rem)] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg"
        showCloseButton={!mutation.isPending}
      >
        <form
          autoComplete="off"
          className="flex min-h-0 flex-1 flex-col"
          noValidate
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
        >
          <DialogHeader className="shrink-0 px-4 pt-4">
            <DialogTitle>Изменить партию</DialogTitle>
            <DialogDescription>
              Измените доступные параметры партии «{batch.name}».
            </DialogDescription>
          </DialogHeader>
          <FieldGroup className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
            <Controller
              control={form.control}
              name="name"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor={`batch-${batch.id}-name`}>
                    Название
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    id={`batch-${batch.id}-name`}
                    required
                  />
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
            />
            <Controller
              control={form.control}
              name="dayPlanQty"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor={`batch-${batch.id}-day-plan`}>
                    Дневной план
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    id={`batch-${batch.id}-day-plan`}
                    inputMode="numeric"
                    onChange={(event) =>
                      field.onChange(normalizePositiveIntegerInput(event.currentTarget.value))
                    }
                    required
                  />
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
            />
            <Controller
              control={form.control}
              name="description"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor={`batch-${batch.id}-description`}>
                    Описание
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupTextarea
                      {...field}
                      aria-invalid={fieldState.invalid}
                      className="field-sizing-fixed h-24"
                      id={`batch-${batch.id}-description`}
                      maxLength={textLimit}
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
          <DialogFooter className="mx-0 mb-0 shrink-0 rounded-b-xl px-4 py-4">
            <Button disabled={mutation.isPending} onClick={close} type="button" variant="outline">
              Отмена
            </Button>
            <Button disabled={mutation.isPending || !form.formState.isDirty} type="submit">
              {mutation.isPending ? <Spinner data-icon="inline-start" /> : null}
              {mutation.isPending ? 'Сохранение…' : 'Сохранить'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
