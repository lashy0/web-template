import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { EyeIcon, EyeOffIcon, PlusIcon } from 'lucide-react'
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
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@web-app/ui/components/input-group'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@web-app/ui/components/select'
import { Switch } from '@web-app/ui/components/switch'
import { Spinner } from '@web-app/ui/components/spinner'

import {
  createUser,
  isLoginAlreadyExistsError,
  roleLabels,
  roleOptions,
  type CreateUserInput,
  type Role,
} from '@/features/users/users-api'
import { createUserSchema } from '@/features/users/user-form-schema'
import useCustomToast from '@/hooks/useCustomToast'

const initialForm: CreateUserInput = {
  active: true,
  login: '',
  name: '',
  password: '',
  role: 'operator',
}

export function AddUser() {
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const form = useForm<CreateUserInput>({
    defaultValues: initialForm,
    mode: 'onChange',
    resolver: zodResolver(createUserSchema),
  })
  const { showErrorToast, showSuccessToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: createUser,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['users'] })
      resetAndClose()
      showSuccessToast('Пользователь создан', 'Учётная запись успешно добавлена.')
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
      showErrorToast('Не удалось создать пользователя', 'Проверьте данные и попробуйте ещё раз.')
    },
  })

  function resetAndClose() {
    form.reset(initialForm)
    setIsOpen(false)
    setShowPassword(false)
  }

  function submit(data: CreateUserInput) {
    mutation.mutate(data)
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
          onSubmit={form.handleSubmit(submit)}
        >
          <DialogHeader>
            <DialogTitle>Новый пользователь</DialogTitle>
            <DialogDescription>Задайте учётные данные и назначьте роль.</DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Controller
              control={form.control}
              name="name"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor="new-user-name">
                    Имя
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    autoComplete="off"
                    id="new-user-name"
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
                  <FieldLabel className="cursor-pointer" htmlFor="new-user-login">
                    Логин
                  </FieldLabel>
                  <Input
                    {...field}
                    aria-invalid={fieldState.invalid}
                    autoCapitalize="none"
                    autoComplete="off"
                    id="new-user-login"
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
              name="password"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor="new-user-password">
                    Пароль
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupInput
                      {...field}
                      aria-invalid={fieldState.invalid}
                      autoComplete="new-password"
                      id="new-user-password"
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
              name="role"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel className="cursor-pointer" htmlFor="new-user-role">
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
                      id="new-user-role"
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
            <Controller
              control={form.control}
              name="active"
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid} orientation="horizontal">
                  <FieldContent>
                    <FieldLabel className="cursor-pointer" htmlFor="new-user-active">
                      Активировать учётную запись
                    </FieldLabel>
                    {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
                  </FieldContent>
                  <Switch
                    aria-invalid={fieldState.invalid}
                    checked={field.value}
                    id="new-user-active"
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
              {mutation.isPending && <Spinner data-icon="inline-start" />}
              {mutation.isPending ? 'Создание…' : 'Создать'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
