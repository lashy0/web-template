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
  kgVersionErrorMessage,
  updateKgVersion,
  type KgVersion,
} from '@/features/kg/kg-versions-api'
import { updateKgVersionSchema } from '@/features/kg/kg-version-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type EditKgVersionForm = Readonly<{ description: string; name: string }>
const textLimit = 2000

function toForm(version: KgVersion): EditKgVersionForm {
  return { description: version.description ?? '', name: version.name }
}

export function EditKgVersion({
  onOpenChange,
  onSuccess,
  open,
  version,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
  version: KgVersion
}>) {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const form = useForm<EditKgVersionForm>({
    defaultValues: toForm(version),
    mode: 'onChange',
    resolver: zodResolver(updateKgVersionSchema),
  })
  useEffect(() => {
    if (open) form.reset(toForm(version))
  }, [form, open, version])
  const mutation = useMutation({
    mutationFn: (data: EditKgVersionForm) =>
      updateKgVersion(version.id, {
        description: data.description.trim() || null,
        name: data.name.trim(),
      }),
    onError: (error) =>
      showErrorToast(
        'Не удалось изменить версию КГ',
        kgVersionErrorMessage(error) ?? 'Проверьте данные и попробуйте ещё раз.',
      ),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['kg', 'versions'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      close(true)
      onSuccess()
      showSuccessToast('Версия КГ изменена', `Данные «${version.code}» сохранены.`)
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
            <DialogTitle>Изменить версию КГ</DialogTitle>
            <DialogDescription>Код версии изменить нельзя.</DialogDescription>
          </DialogHeader>
          <FieldGroup className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
            <Field>
              <FieldLabel htmlFor={`kg-version-${version.id}-code`}>Код</FieldLabel>
              <Input id={`kg-version-${version.id}-code`} readOnly value={version.code} />
            </Field>
            <Controller
              control={form.control}
              name="name"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor={`kg-version-${version.id}-name`}>
                    Название
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    id={`kg-version-${version.id}-name`}
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
                    htmlFor={`kg-version-${version.id}-description`}
                  >
                    Описание
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupTextarea
                      {...field}
                      aria-invalid={fieldState.invalid}
                      className="field-sizing-fixed h-24"
                      id={`kg-version-${version.id}-description`}
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
