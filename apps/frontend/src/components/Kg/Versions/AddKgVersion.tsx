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
  createKgVersion,
  kgVersionErrorCode,
  kgVersionErrorMessage,
  type CreateKgVersionInput,
} from '@/features/kg/kg-versions-api'
import { createKgVersionSchema } from '@/features/kg/kg-version-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type CreateKgVersionForm = Readonly<{ code: string; description: string; name: string }>

const initialForm: CreateKgVersionForm = { code: '', description: '', name: '' }
const textLimit = 2000

export function AddKgVersion() {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const form = useForm<CreateKgVersionForm>({
    defaultValues: initialForm,
    mode: 'onBlur',
    reValidateMode: 'onBlur',
    resolver: zodResolver(createKgVersionSchema),
  })
  const mutation = useMutation({
    mutationFn: (data: CreateKgVersionForm) => createKgVersion(toInput(data)),
    onError: (error) => {
      const message = kgVersionErrorMessage(error)
      if (kgVersionErrorCode(error) === 'kg_version_conflict') {
        form.setError('code', { message, type: 'server' }, { shouldFocus: true })
        return
      }
      showErrorToast(
        'Не удалось создать версию КГ',
        message ?? 'Проверьте данные и попробуйте ещё раз.',
      )
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['kg', 'versions'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      close(true)
      showSuccessToast('Версия КГ создана', 'Версия КГ успешно добавлена.')
    },
  })

  function close(force = false) {
    if (mutation.isPending && !force) return
    form.reset(initialForm)
    setOpen(false)
  }

  return (
    <Dialog onOpenChange={(nextOpen) => (nextOpen ? setOpen(true) : close())} open={open}>
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
            <DialogTitle>Новая версия КГ</DialogTitle>
            <DialogDescription>Укажите код, название и описание версии.</DialogDescription>
          </DialogHeader>
          <FieldGroup className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
            <Controller
              control={form.control}
              name="code"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor="new-kg-version-code">
                    Код
                    <span aria-hidden="true" className="ml-0.5 text-destructive">
                      *
                    </span>
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    id="new-kg-version-code"
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
                  <FieldLabel className="cursor-pointer" htmlFor="new-kg-version-name">
                    Название
                    <span aria-hidden="true" className="ml-0.5 text-destructive">
                      *
                    </span>
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    id="new-kg-version-name"
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
                  <FieldLabel className="cursor-pointer" htmlFor="new-kg-version-description">
                    Описание
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupTextarea
                      {...field}
                      aria-invalid={fieldState.invalid}
                      className="field-sizing-fixed h-24"
                      id="new-kg-version-description"
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

function toInput(data: CreateKgVersionForm): CreateKgVersionInput {
  return {
    code: data.code.trim(),
    description: data.description.trim() || null,
    name: data.name.trim(),
  }
}
