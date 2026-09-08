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
import {
  InputGroup,
  InputGroupAddon,
  InputGroupText,
  InputGroupTextarea,
} from '@web-app/ui/components/input-group'
import { Spinner } from '@web-app/ui/components/spinner'

import { DefectGroupSelect } from '@/components/Defects/Types/DefectGroupSelect'
import {
  createDefectType,
  defectErrorCode,
  defectErrorMessage,
  type CreateDefectTypeInput,
} from '@/features/defects/defects-api'
import { createDefectTypeSchema } from '@/features/defects/defect-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type CreateDefectTypeForm = Readonly<{
  code: string
  description: string
  engineer_action: string
  group_id: string
  name: string
  possible_cause: string
}>
const initialForm: CreateDefectTypeForm = {
  code: '',
  description: '',
  engineer_action: '',
  group_id: '',
  name: '',
  possible_cause: '',
}
const defectTypeTextLimit = 2000

export function AddDefectType({ groupId }: Readonly<{ groupId?: string }>) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const form = useForm<CreateDefectTypeForm>({
    defaultValues: { ...initialForm, group_id: groupId ?? '' },
    mode: 'onChange',
    resolver: zodResolver(createDefectTypeSchema),
  })
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: (data: CreateDefectTypeForm) => createDefectType(toInput(data)),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['defects'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      resetAndClose()
      showSuccessToast('Тип создан', 'Тип дефекта успешно добавлен.')
    },
    onError: (error) => {
      const message = defectErrorMessage(error)
      if (defectErrorCode(error) === 'defect_type_already_exists') {
        form.setError('code', { message, type: 'server' }, { shouldFocus: true })
        return
      }
      showErrorToast('Не удалось создать тип', message ?? 'Проверьте данные и попробуйте ещё раз.')
    },
  })

  function resetAndClose() {
    form.reset({ ...initialForm, group_id: groupId ?? '' })
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
          onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
        >
          <DialogHeader className="shrink-0 px-4 pt-4">
            <DialogTitle>Новый тип дефекта</DialogTitle>
            <DialogDescription>Укажите группу и параметры типа.</DialogDescription>
          </DialogHeader>
          <FieldGroup className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
            <Controller
              control={form.control}
              name="group_id"
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
              name="possible_cause"
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
              name="engineer_action"
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

function toInput(data: CreateDefectTypeForm): CreateDefectTypeInput {
  return {
    code: data.code,
    description: data.description,
    engineer_action: data.engineer_action.trim() || null,
    group_id: data.group_id,
    name: data.name,
    possible_cause: data.possible_cause.trim() || null,
  }
}
