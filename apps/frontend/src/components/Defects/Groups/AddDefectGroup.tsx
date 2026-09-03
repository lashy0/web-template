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
  createDefectGroup,
  defectErrorMessage,
  type CreateDefectGroupInput,
} from '@/features/defects/defects-api'
import { createDefectGroupSchema } from '@/features/defects/defect-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type CreateDefectGroupForm = Readonly<{ code: string; description: string; name: string }>
const initialForm: CreateDefectGroupForm = { code: '', description: '', name: '' }

export function AddDefectGroup() {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const form = useForm<CreateDefectGroupForm>({
    defaultValues: initialForm,
    mode: 'onChange',
    resolver: zodResolver(createDefectGroupSchema),
  })
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: (data: CreateDefectGroupForm) => createDefectGroup(toInput(data)),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['defects'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      resetAndClose()
      showSuccessToast('Группа создана', 'Группа дефектов успешно добавлена.')
    },
    onError: (error) => {
      const message = defectErrorMessage(error)

      if (message?.includes('таким кодом')) {
        form.setError('code', { message, type: 'server' }, { shouldFocus: true })
        return
      }

      showErrorToast(
        'Не удалось создать группу',
        message ?? 'Проверьте данные и попробуйте ещё раз.',
      )
    },
  })

  function resetAndClose() {
    form.reset(initialForm)
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
      <DialogTrigger render={<Button className="my-4 cursor-pointer" />}>
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
            <DialogTitle>Новая группа дефектов</DialogTitle>
            <DialogDescription>Задайте код, название и описание группы.</DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Controller
              control={form.control}
              name="code"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor="new-defect-group-code">
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
                    id="new-defect-group-code"
                    onChange={(event) => {
                      if (fieldState.error?.type === 'server') form.clearErrors('code')
                      field.onChange(event)
                    }}
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
                  <FieldLabel className="cursor-pointer" htmlFor="new-defect-group-name">
                    <span>
                      Название
                      <span aria-hidden="true" className="ml-0.5 text-destructive">
                        *
                      </span>
                    </span>
                  </FieldLabel>
                  <Input {...field} aria-invalid={fieldState.invalid} id="new-defect-group-name" />
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
            />
            <Controller
              control={form.control}
              name="description"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor="new-defect-group-description">
                    <span>Описание</span>
                  </FieldLabel>
                  <textarea
                    {...field}
                    aria-invalid={fieldState.invalid}
                    className="border-input bg-transparent focus-visible:border-ring focus-visible:ring-ring/50 min-h-20 w-full rounded-md border px-3 py-2 text-sm shadow-xs outline-none focus-visible:ring-[3px]"
                    id="new-defect-group-description"
                  />
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
            />
          </FieldGroup>
          <DialogFooter>
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

function toInput(data: CreateDefectGroupForm): CreateDefectGroupInput {
  return { code: data.code, description: data.description.trim() || null, name: data.name }
}
