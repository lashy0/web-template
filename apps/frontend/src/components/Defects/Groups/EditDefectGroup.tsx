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
  updateDefectGroup,
  type DefectGroup,
} from '@/features/defects/defects-api'
import { updateDefectGroupSchema } from '@/features/defects/defect-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type EditDefectGroupForm = Readonly<{ description: string; name: string }>
function toForm(group: DefectGroup): EditDefectGroupForm {
  return { description: group.description ?? '', name: group.name }
}

export function EditDefectGroup({
  onOpenChange,
  onSuccess,
  open,
  group,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
  group: DefectGroup
}>) {
  const queryClient = useQueryClient()
  const form = useForm<EditDefectGroupForm>({
    defaultValues: toForm(group),
    mode: 'onChange',
    resolver: zodResolver(updateDefectGroupSchema),
  })
  const { showErrorToast, showSuccessToast } = useCustomToast()
  useEffect(() => {
    if (open) form.reset(toForm(group))
  }, [form, group, open])
  const mutation = useMutation({
    mutationFn: (data: EditDefectGroupForm) =>
      updateDefectGroup(group.id, {
        description: data.description.trim() || null,
        name: data.name,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['defects'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      close(true)
      onSuccess()
      showSuccessToast('Группа изменена', `Данные «${group.code}» сохранены.`)
    },
    onError: (error) =>
      showErrorToast(
        'Не удалось изменить группу',
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
            <DialogTitle>Изменить группу</DialogTitle>
            <DialogDescription>Код группы «{group.code}» изменить нельзя.</DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Controller
              control={form.control}
              name="name"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor={`defect-group-${group.id}-name`}>
                    <span>Название</span>
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    id={`defect-group-${group.id}-name`}
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
                    htmlFor={`defect-group-${group.id}-description`}
                  >
                    <span>Описание</span>
                  </FieldLabel>
                  <textarea
                    {...field}
                    aria-invalid={fieldState.invalid}
                    className="border-input bg-transparent focus-visible:border-ring focus-visible:ring-ring/50 min-h-20 w-full rounded-md border px-3 py-2 text-sm shadow-xs outline-none focus-visible:ring-[3px]"
                    id={`defect-group-${group.id}-description`}
                  />
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
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
