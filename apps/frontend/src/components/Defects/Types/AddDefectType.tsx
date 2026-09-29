import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createDefectTypeMutation } from '@web-app/api-client'
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
import {
  InputGroup,
  InputGroupAddon,
  InputGroupText,
  InputGroupTextarea,
} from '@web-app/ui/components/input-group'
import { Spinner } from '@web-app/ui/components/spinner'

import { DefectGroupSelect } from '@/components/Defects/Types/DefectGroupSelect'
import {
  invalidateDefectQueries,
  isDefectGroupArchivedError,
  isDefectTypeCodeTakenError,
} from '@/features/defects/defects-api'
import { createDefectTypeSchema, defectFormMessages } from '@/features/defects/defect-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type CreateDefectTypeForm = z.input<typeof createDefectTypeSchema>
const initialForm: CreateDefectTypeForm = {
  code: '',
  description: '',
  engineerAction: '',
  groupId: '',
  name: '',
  possibleCause: '',
}
const defectTypeTextLimit = 2000

export function AddDefectType({ groupId }: Readonly<{ groupId?: string }>) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const form = useForm<CreateDefectTypeForm, unknown, z.output<typeof createDefectTypeSchema>>({
    defaultValues: { ...initialForm, groupId: groupId ?? '' },
    mode: 'onChange',
    resolver: zodResolver(createDefectTypeSchema, { error: defectFormMessages }),
  })
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const mutation = useMutation({
    ...createDefectTypeMutation(),
    onSuccess: async () => {
      await invalidateDefectQueries(queryClient)
      resetAndClose()
      showSuccessToast('Тип создан', 'Тип дефекта успешно добавлен.')
    },
    onError: (error) => {
      if (isDefectTypeCodeTakenError(error)) {
        form.setError(
          'code',
          { message: 'Тип с таким кодом уже существует.', type: 'server' },
          { shouldFocus: true },
        )
        return
      }
      if (isDefectGroupArchivedError(error)) {
        form.setError(
          'groupId',
          { message: 'Группа архивирована. Выберите другую.', type: 'server' },
          { shouldFocus: true },
        )
        return
      }
      showErrorToast('Не удалось создать тип', 'Проверьте данные и попробуйте ещё раз.')
    },
  })

  function resetAndClose() {
    form.reset({ ...initialForm, groupId: groupId ?? '' })
    setIsOpen(false)
  }
  return (
    <Dialog
      onOpenChange={(open) => {
        setIsOpen(open)
        if (!open && !mutation.isPending) resetAndClose()
      }}
      open={isOpen}
    >
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
            <DialogTitle>Новый тип дефекта</DialogTitle>
            <DialogDescription>Укажите группу и параметры типа.</DialogDescription>
          </DialogHeader>
          <FieldGroup className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
            <Controller
              control={form.control}
              name="groupId"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor="new-defect-type-group">
                    <span>
                      Группа
                      <span aria-hidden="true" className="ml-0.5 text-destructive">
                        *
                      </span>
                    </span>
                  </FieldLabel>
                  <DefectGroupSelect
                    ariaLabel="Группа"
                    className="w-full"
                    id="new-defect-type-group"
                    onChange={(value) => field.onChange(value ?? '')}
                    value={field.value || undefined}
                  />
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
            />
            <Controller
              control={form.control}
              name="code"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor="new-defect-type-code">
                    <span>
                      Код
                      <span aria-hidden="true" className="ml-0.5 text-destructive">
                        *
                      </span>
                    </span>
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    id="new-defect-type-code"
                    onChange={(event) => {
                      if (fieldState.error?.type === 'server') form.clearErrors('code')
                      field.onChange(event)
                    }}
                    required
                  />
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
            />
            <Controller
              control={form.control}
              name="name"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor="new-defect-type-name">
                    <span>
                      Название
                      <span aria-hidden="true" className="ml-0.5 text-destructive">
                        *
                      </span>
                    </span>
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    id="new-defect-type-name"
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
                  <FieldLabel className="cursor-pointer" htmlFor="new-defect-type-description">
                    <span>
                      Описание
                      <span aria-hidden="true" className="ml-0.5 text-destructive">
                        *
                      </span>
                    </span>
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupTextarea
                      {...field}
                      aria-invalid={fieldState.invalid}
                      className="field-sizing-fixed h-24"
                      id="new-defect-type-description"
                      maxLength={defectTypeTextLimit}
                      required
                    />
                    <CharacterCount value={field.value} />
                  </InputGroup>
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
            />
            <Controller
              control={form.control}
              name="possibleCause"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor="new-defect-type-cause">
                    Возможная причина
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupTextarea
                      {...field}
                      aria-invalid={fieldState.invalid}
                      className="field-sizing-fixed h-24"
                      id="new-defect-type-cause"
                      maxLength={defectTypeTextLimit}
                    />
                    <CharacterCount value={field.value} />
                  </InputGroup>
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
            />
            <Controller
              control={form.control}
              name="engineerAction"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor="new-defect-type-action">
                    Действие инженера
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupTextarea
                      {...field}
                      aria-invalid={fieldState.invalid}
                      className="field-sizing-fixed h-24"
                      id="new-defect-type-action"
                      maxLength={defectTypeTextLimit}
                    />
                    <CharacterCount value={field.value} />
                  </InputGroup>
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
            />
          </FieldGroup>
          <DialogFooter className="mx-0 mb-0 shrink-0 rounded-b-xl px-4 py-4">
            <Button
              disabled={mutation.isPending}
              onClick={resetAndClose}
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

function CharacterCount({ value }: Readonly<{ value: string }>) {
  const limitReached = value.length === defectTypeTextLimit

  return (
    <InputGroupAddon align="block-end">
      <InputGroupText
        className="text-xs font-normal tabular-nums data-[limit-reached=true]:text-destructive"
        data-limit-reached={limitReached ? 'true' : undefined}
      >
        {value.length} / {defectTypeTextLimit}
      </InputGroupText>
    </InputGroupAddon>
  )
}
