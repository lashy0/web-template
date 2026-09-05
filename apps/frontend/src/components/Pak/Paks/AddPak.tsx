import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CopyIcon, PlusIcon } from 'lucide-react'
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
import {
  Field,
  FieldContent,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '@web-app/ui/components/field'
import { Input } from '@web-app/ui/components/input'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@web-app/ui/components/select'
import { Spinner } from '@web-app/ui/components/spinner'
import { Switch } from '@web-app/ui/components/switch'

import {
  createPak,
  isPakAlreadyExistsError,
  pakKindLabels,
  pakKindOptions,
  type CreatePakResult,
  type PakKind,
} from '@/features/paks/paks-api'
import { pakCodeForMessage } from '@/features/paks/pak-format'
import { createPakSchema } from '@/features/paks/pak-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type CreatePakForm = Readonly<{ active: boolean; code: string; kind: PakKind }>

const initialForm: CreatePakForm = { active: true, code: '', kind: 'otk_line' }

export function AddPak() {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [created, setCreated] = useState<CreatePakResult | null>(null)
  const form = useForm<CreatePakForm>({
    defaultValues: initialForm,
    mode: 'onChange',
    resolver: zodResolver(createPakSchema),
  })
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: createPak,
    onSuccess: async (result) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['paks'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      form.reset(initialForm)
      setCreated(result)
      showSuccessToast('ПАК создан', `ПАК «${pakCodeForMessage(result.pak.code)}» добавлен.`)
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
      showErrorToast('Не удалось создать ПАК', 'Проверьте данные и попробуйте ещё раз.')
    },
  })

  function resetAndClose() {
    form.reset(initialForm)
    setCreated(null)
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
      <DialogContent className="sm:max-w-lg" showCloseButton={!mutation.isPending}>
        {created ? (
          <CreatedAccessKey result={created} onClose={resetAndClose} />
        ) : (
          <form
            autoComplete="off"
            className="flex flex-col gap-5"
            noValidate
            onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
          >
            <DialogHeader>
              <DialogTitle>Новый ПАК</DialogTitle>
              <DialogDescription>
                Задайте код, тип и начальное состояние комплекса.
              </DialogDescription>
            </DialogHeader>
            <FieldGroup>
              <Controller
                control={form.control}
                name="code"
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel className="cursor-pointer" htmlFor="new-pak-code">
                      Код ПАК
                    </FieldLabel>
                    <Input
                      {...field}
                      aria-invalid={fieldState.invalid}
                      autoComplete="off"
                      id="new-pak-code"
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
                    <FieldLabel className="cursor-pointer" htmlFor="new-pak-kind">
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
                        id="new-pak-kind"
                      >
                        <SelectValue>
                          {(kind: PakKind | null) => (kind ? pakKindLabels[kind] : 'Выберите тип')}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          {pakKindOptions.map((item) => (
                            <SelectItem key={item.value} value={item.value}>
                              {item.label}
                            </SelectItem>
                          ))}
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                    {fieldState.invalid ? <FieldError errors={[fieldState.error]} /> : null}
                  </Field>
                )}
              />
              <Controller
                control={form.control}
                name="active"
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid} orientation="horizontal">
                    <FieldContent>
                      <FieldLabel className="cursor-pointer" htmlFor="new-pak-active">
                        Разрешить работу ПАК
                      </FieldLabel>
                    </FieldContent>
                    <Switch
                      aria-invalid={fieldState.invalid}
                      checked={field.value ?? true}
                      id="new-pak-active"
                      onCheckedChange={field.onChange}
                    />
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
        )}
      </DialogContent>
    </Dialog>
  )
}

function CreatedAccessKey({
  onClose,
  result,
}: Readonly<{ onClose: () => void; result: CreatePakResult }>) {
  const { showSuccessToast } = useCustomToast()
  const copy = async () => {
    await navigator.clipboard?.writeText(result.accessKey)
    showSuccessToast('Ключ скопирован')
  }

  return (
    <div className="flex flex-col gap-5">
      <DialogHeader>
        <DialogTitle>ПАК создан</DialogTitle>
        <DialogDescription>
          Сохраните ключ доступа: после закрытия этого окна он больше не будет показан.
        </DialogDescription>
      </DialogHeader>
      <div className="rounded-md border bg-muted p-3 font-mono text-sm break-all">
        {result.accessKey}
      </div>
      <DialogFooter>
        <Button onClick={() => void copy()} type="button" variant="outline">
          <CopyIcon data-icon="inline-start" />
          Копировать
        </Button>
        <Button onClick={onClose} type="button">
          Готово
        </Button>
      </DialogFooter>
    </div>
  )
}
