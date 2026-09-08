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

import {
  createDefectGroup,
  defectErrorCode,
  defectErrorMessage,
  type CreateDefectGroupInput,
} from '@/features/defects/defects-api'
import { createDefectGroupSchema } from '@/features/defects/defect-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type CreateDefectGroupForm = Readonly<{ code: string; description: string; name: string }>
const initialForm: CreateDefectGroupForm = { code: '', description: '', name: '' }
const textLimit = 2000

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

      if (defectErrorCode(error) === 'defect_group_already_exists') {
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
            <DialogTitle>Новая группа дефектов</DialogTitle>
            <DialogDescription>Задайте код, название и описание группы.</DialogDescription>
          </DialogHeader>
          <FieldGroup className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
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
                  <InputGroup>
                    <InputGroupTextarea
                      {...field}
                      aria-invalid={fieldState.invalid}
                      className="field-sizing-fixed h-24"
                      id="new-defect-group-description"
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

function toInput(data: CreateDefectGroupForm): CreateDefectGroupInput {
  return {
    code: data.code,
    description: data.description.trim() || null,
    name: data.name,
  }
}
