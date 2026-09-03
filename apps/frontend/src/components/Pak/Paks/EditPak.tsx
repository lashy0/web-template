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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@web-app/ui/components/select'
import { Spinner } from '@web-app/ui/components/spinner'

import {
  isPakAlreadyExistsError,
  pakKindLabels,
  pakKindOptions,
  updatePak,
  type Pak,
  type PakKind,
} from '@/features/paks/paks-api'
import { editPakSchema } from '@/features/paks/pak-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type EditPakForm = Readonly<{ code: string; kind: PakKind }>

function toForm(pak: Pak): EditPakForm {
  return { code: pak.code, kind: pak.kind }
}

export function EditPak({
  onOpenChange,
  onSuccess,
  open,
  pak,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
  pak: Pak
}>) {
  const queryClient = useQueryClient()
  const form = useForm<EditPakForm>({
    defaultValues: toForm(pak),
    mode: 'onChange',
    resolver: zodResolver(editPakSchema),
  })
  const { showErrorToast, showSuccessToast } = useCustomToast()

  useEffect(() => {
    if (open) form.reset(toForm(pak))
  }, [form, open, pak])

  const mutation = useMutation({
    mutationFn: (data: EditPakForm) => updatePak(pak.id, data),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['paks'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      close(true)
      onSuccess()
      showSuccessToast('ПАК изменён', `Данные «${pak.code}» сохранены.`)
    },
    onError: (error) => {
      if (isPakAlreadyExistsError(error)) {
        form.setError(
          'code',
          { message: 'ПАК с таким кодом уже существует.', type: 'server' },
          { shouldFocus: true },
        )
        return
      }
      showErrorToast('Не удалось обновить ПАК', 'Проверьте данные и попробуйте ещё раз.')
    },
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
            <DialogTitle>Изменить ПАК</DialogTitle>
            <DialogDescription>Измените параметры комплекса «{pak.code}».</DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Controller
              control={form.control}
              name="code"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor={`pak-${pak.id}-code`}>
                    Код ПАК
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    id={`pak-${pak.id}-code`}
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
              name="kind"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor={`pak-${pak.id}-kind`}>
                    Тип
                  </FieldLabel>
                  <Select
                    items={pakKindOptions}
                    name={field.name}
                    onValueChange={field.onChange}
                    value={field.value}
                  >
                    <SelectTrigger
                      aria-invalid={fieldState.invalid}
                      className="w-full"
                      id={`pak-${pak.id}-kind`}
                    >
                      <SelectValue>
                        {(kind: PakKind | null) => (kind ? pakKindLabels[kind] : 'Выберите тип')}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {pakKindOptions.map((item) => (
                        <SelectItem key={item.value} value={item.value}>
                          {item.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
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
