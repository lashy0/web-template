import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Controller, useForm } from 'react-hook-form'

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
import { Spinner } from '@web-app/ui/components/spinner'

import {
  defectErrorMessage,
  updateDefectType,
  type DefectType,
} from '@/features/defects/defects-api'
import { updateDefectTypeSchema } from '@/features/defects/defect-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type EditDefectTypeForm = Readonly<{
  description: string
  engineer_action: string
  name: string
  possible_cause: string
}>
function toForm(type: DefectType): EditDefectTypeForm {
  return {
    description: type.description,
    engineer_action: type.engineerAction ?? '',
    name: type.name,
    possible_cause: type.possibleCause ?? '',
  }
}
export function EditDefectType({
  onOpenChange,
  onSuccess,
  open,
  type,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
  type: DefectType
}>) {
  const queryClient = useQueryClient()
  const form = useForm<EditDefectTypeForm>({
    defaultValues: toForm(type),
    mode: 'onChange',
    resolver: zodResolver(updateDefectTypeSchema),
  })
  const { showErrorToast, showSuccessToast } = useCustomToast()
  useEffect(() => {
    if (open) form.reset(toForm(type))
  }, [form, open, type])
  const mutation = useMutation({
    mutationFn: (data: EditDefectTypeForm) =>
      updateDefectType(type.id, {
        description: data.description,
        engineer_action: data.engineer_action.trim() || null,
        name: data.name,
        possible_cause: data.possible_cause.trim() || null,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['defects'] })
      close(true)
      onSuccess()
      showSuccessToast('Тип изменён', `Данные «${type.code}» сохранены.`)
    },
    onError: (error) =>
      showErrorToast(
        'Не удалось изменить тип',
        defectErrorMessage(error) ?? 'Проверьте данные и попробуйте ещё раз.',
      ),
  })
  function close(force = false) {
    if (!mutation.isPending || force) onOpenChange(false)
  }
  return (
    <Dialog onOpenChange={(nextOpen) => (nextOpen ? onOpenChange(true) : close())} open={open}>
      <DialogContent className="sm:max-w-lg" showCloseButton={!mutation.isPending}>
        <form
          autoComplete="off"
          className="flex flex-col gap-5"
          noValidate
          onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
        >
          <DialogHeader>
            <DialogTitle>Изменить тип дефекта</DialogTitle>
            <DialogDescription>Код «{type.code}» и группу типа изменить нельзя.</DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <TextInput
              control={form.control}
              id={`defect-type-${type.id}-name`}
              label="Название"
              name="name"
            />
            <TextArea
              control={form.control}
              id={`defect-type-${type.id}-description`}
              label="Описание"
              name="description"
            />
            <TextArea
              control={form.control}
              id={`defect-type-${type.id}-cause`}
              label="Возможная причина"
              name="possible_cause"
            />
            <TextArea
              control={form.control}
              id={`defect-type-${type.id}-action`}
              label="Действие инженера"
              name="engineer_action"
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
function TextInput({
  control,
  id,
  label,
  name,
}: Readonly<{ control: any; id: string; label: string; name: string }>) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => (
        <Field data-invalid={fieldState.invalid}>
          <FieldLabel className="cursor-pointer" htmlFor={id}>
            <span>{label}</span>
          </FieldLabel>
          <Input {...field} aria-invalid={fieldState.invalid} id={id} />
          {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
        </Field>
      )}
    />
  )
}
function TextArea({
  control,
  id,
  label,
  name,
}: Readonly<{ control: any; id: string; label: string; name: string }>) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => (
        <Field data-invalid={fieldState.invalid}>
          <FieldLabel className="cursor-pointer" htmlFor={id}>
            <span>{label}</span>
          </FieldLabel>
          <textarea
            {...field}
            aria-invalid={fieldState.invalid}
            className="border-input bg-transparent focus-visible:border-ring focus-visible:ring-ring/50 min-h-20 w-full rounded-md border px-3 py-2 text-sm shadow-xs outline-none focus-visible:ring-[3px]"
            id={id}
          />
          {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
        </Field>
      )}
    />
  )
}
