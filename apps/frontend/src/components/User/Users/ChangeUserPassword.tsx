import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { EyeIcon, EyeOffIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'

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
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@web-app/ui/components/input-group'
import { Spinner } from '@web-app/ui/components/spinner'

import { updateUserPassword, type User } from '@/features/users/users-api'
import { changeUserPasswordSchema } from '@/features/users/user-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

type ChangePasswordForm = z.infer<typeof changeUserPasswordSchema>

const initialForm: ChangePasswordForm = { password: '', passwordConfirmation: '' }

export function ChangeUserPassword({
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
  const [showPassword, setShowPassword] = useState(false)
  const [showPasswordConfirmation, setShowPasswordConfirmation] = useState(false)
  const form = useForm<ChangePasswordForm>({
    defaultValues: initialForm,
    mode: 'onChange',
    resolver: zodResolver(changeUserPasswordSchema),
  })
  const { showErrorToast, showSuccessToast } = useCustomToast()

  useEffect(() => {
    if (open) {
      form.reset(initialForm)
      setShowPassword(false)
      setShowPasswordConfirmation(false)
    }
  }, [form, open])

  const mutation = useMutation({
    mutationFn: ({ password }: ChangePasswordForm) => updateUserPassword(user.id, password),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['users'] })
      closeDialog(true)
      onSuccess()
      showSuccessToast('Пароль изменён', `Пароль пользователя «${user.name}» успешно обновлён.`)
    },
    onError: () => {
      showErrorToast('Не удалось изменить пароль', 'Проверьте данные и попробуйте ещё раз.')
    },
  })

  function closeDialog(force = false) {
    if (mutation.isPending && !force) return
    onOpenChange(false)
  }

  function submit(data: ChangePasswordForm) {
    mutation.mutate(data)
  }

  return (
    <Dialog onOpenChange={closeDialog} open={open}>
      <DialogContent className="sm:max-w-md" showCloseButton={!mutation.isPending}>
        <form
          autoComplete="off"
          className="flex flex-col gap-5"
          noValidate
          onSubmit={form.handleSubmit(submit)}
        >
          <DialogHeader>
            <DialogTitle>Сменить пароль</DialogTitle>
            <DialogDescription>
              Укажите новый пароль для учётной записи «{user.name}».
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Controller
              control={form.control}
              name="password"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={`user-${user.id}-new-password`}>Новый пароль</FieldLabel>
                  <InputGroup>
                    <InputGroupInput
                      {...field}
                      aria-invalid={fieldState.invalid}
                      autoComplete="new-password"
                      id={`user-${user.id}-new-password`}
                      type={showPassword ? 'text' : 'password'}
                    />
                    <InputGroupAddon align="inline-end">
                      <InputGroupButton
                        aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
                        aria-pressed={showPassword}
                        onClick={() => setShowPassword((current) => !current)}
                        size="icon-xs"
                        type="button"
                      >
                        {showPassword ? (
                          <EyeOffIcon data-icon="inline-end" />
                        ) : (
                          <EyeIcon data-icon="inline-end" />
                        )}
                      </InputGroupButton>
                    </InputGroupAddon>
                  </InputGroup>
                  {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
                </Field>
              )}
            />
            <Controller
              control={form.control}
              name="passwordConfirmation"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={`user-${user.id}-password-confirmation`}>
                    Повторите пароль
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupInput
                      {...field}
                      aria-invalid={fieldState.invalid}
                      autoComplete="new-password"
                      id={`user-${user.id}-password-confirmation`}
                      type={showPasswordConfirmation ? 'text' : 'password'}
                    />
                    <InputGroupAddon align="inline-end">
                      <InputGroupButton
                        aria-label={
                          showPasswordConfirmation
                            ? 'Скрыть подтверждение пароля'
                            : 'Показать подтверждение пароля'
                        }
                        aria-pressed={showPasswordConfirmation}
                        onClick={() => setShowPasswordConfirmation((current) => !current)}
                        size="icon-xs"
                        type="button"
                      >
                        {showPasswordConfirmation ? (
                          <EyeOffIcon data-icon="inline-end" />
                        ) : (
                          <EyeIcon data-icon="inline-end" />
                        )}
                      </InputGroupButton>
                    </InputGroupAddon>
                  </InputGroup>
                  {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
                </Field>
              )}
            />
          </FieldGroup>
          <DialogFooter>
            <Button disabled={mutation.isPending} onClick={() => closeDialog()} variant="outline">
              Отмена
            </Button>
            <Button disabled={mutation.isPending} type="submit">
              {mutation.isPending && <Spinner data-icon="inline-start" />}
              {mutation.isPending ? 'Смена пароля…' : 'Сменить пароль'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
