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
import {
  InputGroup,
  InputGroupAddon,
  InputGroupText,
  InputGroupTextarea,
} from '@web-app/ui/components/input-group'
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
const textLimit = 2000
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
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['defects'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
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
            <DialogTitle>Изменить тип дефекта</DialogTitle>
            <DialogDescription>Код «{type.code}» и группу типа изменить нельзя.</DialogDescription>
          </DialogHeader>
          <FieldGroup className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
            <Controller
              control={form.control}
              name="name"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor={`defect-type-${type.id}-name`}>
                    Название
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    id={`defect-type-${type.id}-name`}
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
                  <FieldLabel
                    className="cursor-pointer"
                    htmlFor={`defect-type-${type.id}-description`}
                  >
                    Описание
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupTextarea
                      {...field}
                      aria-invalid={fieldState.invalid}
                      className="field-sizing-fixed h-24"
                      id={`defect-type-${type.id}-description`}
                      maxLength={textLimit}
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
                  <FieldLabel className="cursor-pointer" htmlFor={`defect-type-${type.id}-cause`}>
                    Возможная причина
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupTextarea
                      {...field}
                      aria-invalid={fieldState.invalid}
                      className="field-sizing-fixed h-24"
                      id={`defect-type-${type.id}-cause`}
                      maxLength={textLimit}
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
                  <FieldLabel className="cursor-pointer" htmlFor={`defect-type-${type.id}-action`}>
                    Действие инженера
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupTextarea
                      {...field}
                      aria-invalid={fieldState.invalid}
                      className="field-sizing-fixed h-24"
                      id={`defect-type-${type.id}-action`}
                      maxLength={textLimit}
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

function CharacterCount({ value }: Readonly<{ value: string }>) {
  const limitReached = value.length === textLimit

  return (
    <InputGroupAddon align="block-end">
      <InputGroupText
        className="text-xs font-normal tabular-nums data-[limit-reached=true]:text-destructive"
        data-limit-reached={limitReached ? 'true' : undefined}
      >
        {value.length} / {textLimit}
      </InputGroupText>
    </InputGroupAddon>
  )
}
