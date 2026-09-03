import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@web-app/ui/components/select'
import { Spinner } from '@web-app/ui/components/spinner'

import {
  createDefectType,
  defectErrorMessage,
  listDefectGroups,
  type CreateDefectTypeInput,
  type DefectGroup,
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
export function AddDefectType({ groupId }: Readonly<{ groupId?: string }>) {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const groups = useQuery({
    enabled: isOpen,
    queryFn: () => listDefectGroups({ page: 1, pageSize: 100 }),
    queryKey: ['defects', 'groups', 'select'],
  })
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
      if (message?.includes('таким кодом')) {
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
  const groupItems = groups.data?.items ?? []
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
            <DialogTitle>Новый тип дефекта</DialogTitle>
            <DialogDescription>Укажите группу и параметры типа.</DialogDescription>
          </DialogHeader>
          <FieldGroup>
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
                  <Select
                    disabled={groups.isLoading}
                    onValueChange={field.onChange}
                    value={field.value}
                  >
                    <SelectTrigger
                      aria-invalid={fieldState.invalid}
                      className="w-full"
                      id="new-defect-type-group"
                    >
                      <SelectValue>
                        {(id: string | null) =>
                          labelFor(groupItems.find((group) => group.id === id))
                        }
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {groupItems.map((group) => (
                        <SelectItem key={group.id} value={group.id}>
                          {labelFor(group)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                </Field>
              )}
            />
            <TextInput
              control={form.control}
              id="new-defect-type-code"
              label="Код"
              name="code"
              onChange={() => form.clearErrors('code')}
              required
            />
            <TextInput
              control={form.control}
              id="new-defect-type-name"
              label="Название"
              name="name"
              required
            />
            <TextArea
              control={form.control}
              id="new-defect-type-description"
              label="Описание"
              name="description"
              required
            />
            <TextArea
              control={form.control}
              id="new-defect-type-cause"
              label="Возможная причина"
              name="possible_cause"
            />
            <TextArea
              control={form.control}
              id="new-defect-type-action"
              label="Действие инженера"
              name="engineer_action"
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
function TextInput({
  control,
  id,
  label,
  name,
  onChange,
  required = false,
}: Readonly<{
  control: any
  id: string
  label: string
  name: string
  onChange?: () => void
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
              onChange?.()
              field.onChange(event)
            }}
          />
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
  required = false,
}: Readonly<{ control: any; id: string; label: string; name: string; required?: boolean }>) {
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
export function labelFor(group: DefectGroup | undefined): string {
  return group ? `${group.code} (${group.name})` : 'Выберите группу'
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
