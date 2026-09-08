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
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@web-app/ui/components/select'
import { Spinner } from '@web-app/ui/components/spinner'

import {
  isLoginAlreadyExistsError,
  roleLabels,
  roleOptions,
  updateUser,
  type Role,
  type User,
} from '@/features/users/users-api'
import { editUserSchema } from '@/features/users/user-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type EditForm = {
  login: string
  name: string
  role: Role
}

function toEditForm(user: User): EditForm {
  return {
    login: user.login ?? '',
    name: user.name,
    role: user.role,
  }
}

export function EditUser({
  onOpenChange,
  onSuccess,
  open,
  user,
}: Readonly<{
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  open: boolean
  user: User
}>) {
  const queryClient = useQueryClient()
  const form = useForm<EditForm>({
    defaultValues: toEditForm(user),
    mode: 'onChange',
    resolver: zodResolver(editUserSchema),
  })
  const { showErrorToast, showSuccessToast } = useCustomToast()

  useEffect(() => {
    if (open) {
      form.reset(toEditForm(user))
    }
  }, [form, open, user])

  const mutation = useMutation({
    mutationFn: (nextForm: EditForm) => updateUser(user.id, nextForm),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['users'] }),
        queryClient.invalidateQueries({ queryKey: ['audit'] }),
      ])
      closeDialog(true)
      onSuccess()
      showSuccessToast('Пользователь изменён', `Данные «${user.name}» сохранены.`)
    },
    onError: (error) => {
      if (isLoginAlreadyExistsError(error)) {
        form.setError(
          'login',
          { message: 'Этот логин уже занят. Выберите другой.', type: 'server' },
          { shouldFocus: true },
        )
        return
      }
      showErrorToast('Не удалось обновить пользователя', 'Проверьте данные и попробуйте ещё раз.')
    },
  })

  function closeDialog(force = false) {
    if (mutation.isPending && !force) return
    onOpenChange(false)
  }

  function handleOpenChange(nextOpen: boolean) {
    if (nextOpen) {
      onOpenChange(true)
      return
    }
    closeDialog()
  }

  function submit(data: EditForm) {
    mutation.mutate(data)
  }

  return (
    <Dialog onOpenChange={handleOpenChange} open={open}>
      <DialogContent
        className="flex max-h-[calc(100dvh-2rem)] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg"
        showCloseButton={!mutation.isPending}
      >
        <form
          autoComplete="off"
          className="flex min-h-0 flex-1 flex-col"
          noValidate
          onSubmit={form.handleSubmit(submit)}
        >
          <DialogHeader className="shrink-0 px-4 pt-4">
            <DialogTitle>Изменить пользователя</DialogTitle>
            <DialogDescription>Измените данные учётной записи «{user.name}».</DialogDescription>
          </DialogHeader>
          <FieldGroup className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
            <Controller
              control={form.control}
              name="name"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor={`user-${user.id}-name`}>
                    Имя
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    autoComplete="off"
                    id={`user-${user.id}-name`}
                  />
                  {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
                </Field>
              )}
            />
            <Controller
              control={form.control}
              name="login"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor={`user-${user.id}-login`}>
                    Логин
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    autoCapitalize="none"
                    autoComplete="off"
                    id={`user-${user.id}-login`}
                    onChange={(event) => {
                      if (fieldState.error?.type === 'server') {
                        form.clearErrors('login')
                      }
                      field.onChange(event)
                    }}
                  />
                  {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
                </Field>
              )}
            />
            <Controller
              control={form.control}
              name="role"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor={`user-${user.id}-role`}>
                    Роль
                  </FieldLabel>
                  <Select
                    items={roleOptions}
                    name={field.name}
                    onValueChange={field.onChange}
                    value={field.value}
                  >
                    <SelectTrigger
                      aria-invalid={fieldState.invalid}
                      className="w-full"
                      id={`user-${user.id}-role`}
                    >
                      <SelectValue>
                        {(role: Role | null) => (role ? roleLabels[role] : 'Выберите роль')}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        {roleOptions.map((role) => (
                          <SelectItem key={role.value} value={role.value}>
                            {role.label}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                  {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
                </Field>
              )}
            />
          </FieldGroup>
          <DialogFooter className="mx-0 mb-0 shrink-0 rounded-b-xl px-4 py-4">
            <Button
              disabled={mutation.isPending}
              onClick={() => closeDialog()}
              type="button"
              variant="outline"
            >
              Отмена
            </Button>
            <Button disabled={mutation.isPending || !form.formState.isDirty} type="submit">
              {mutation.isPending && <Spinner data-icon="inline-start" />}
              {mutation.isPending ? 'Сохранение…' : 'Сохранить'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
