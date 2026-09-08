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

import { kgPrefixErrorMessage, updateKgPrefix, type KgPrefix } from '@/features/kg/kg-prefixes-api'
import { updateKgPrefixSchema } from '@/features/kg/kg-prefix-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type EditKgPrefixForm = Readonly<{ name: string }>

function toForm(prefix: KgPrefix): EditKgPrefixForm {
  return { name: prefix.name ?? '' }
}

export function EditKgPrefix({
  onOpenChange,
  onSuccess,
  open,
  prefix,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
  prefix: KgPrefix
}>) {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const form = useForm<EditKgPrefixForm>({
    defaultValues: toForm(prefix),
    mode: 'onChange',
    resolver: zodResolver(updateKgPrefixSchema),
  })
  useEffect(() => {
    if (open) form.reset(toForm(prefix))
  }, [form, open, prefix])
  const mutation = useMutation({
    mutationFn: (data: EditKgPrefixForm) =>
      updateKgPrefix(prefix.prefix, { name: data.name.trim() || null }),
    onError: (error) =>
      showErrorToast(
        'Не удалось изменить префикс',
        kgPrefixErrorMessage(error) ?? 'Проверьте данные и попробуйте ещё раз.',
      ),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['kg', 'prefixes'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      close(true)
      onSuccess()
      showSuccessToast('Префикс изменён', `Данные «${prefix.prefix}» сохранены.`)
    },
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
            <DialogTitle>Изменить DevEUI-префикс</DialogTitle>
            <DialogDescription>Измените название префикса.</DialogDescription>
          </DialogHeader>
          <FieldGroup className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
            <Controller
              control={form.control}
              name="name"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel
                    className="cursor-pointer"
                    htmlFor={`kg-prefix-${prefix.prefix}-name`}
                  >
                    Название
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    id={`kg-prefix-${prefix.prefix}-name`}
                  />
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
