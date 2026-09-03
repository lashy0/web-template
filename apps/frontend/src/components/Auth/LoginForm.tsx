import { AlertCircleIcon, EyeIcon, EyeOffIcon } from 'lucide-react'
import { useState } from 'react'
import { Alert, AlertTitle } from '@web-app/ui/components/alert'
import { Button } from '@web-app/ui/components/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@web-app/ui/components/card'
import { Field, FieldError, FieldGroup } from '@web-app/ui/components/field'
import { Input } from '@web-app/ui/components/input'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@web-app/ui/components/input-group'
import { Label } from '@web-app/ui/components/label'
import { Spinner } from '@web-app/ui/components/spinner'

import { PendingLogin } from '@/components/Auth/PendingLogin'
import { usePasswordLoginForm } from '@/features/auth/use-password-login-form'

export function LoginForm({ flowId }: Readonly<{ flowId?: string }>) {
  const [isPasswordVisible, setIsPasswordVisible] = useState(false)
  const { clearFormError, flow, form, hasLoadError, retryLoad, submit } =
    usePasswordLoginForm(flowId)
  const {
    formState: { errors, isSubmitting },
    register,
  } = form

  const loginError = errors.login?.message ?? flow?.login.messages[0]
  const passwordError = errors.password?.message ?? flow?.password.messages[0]
  const formError = errors.root?.message ?? flow?.messages[0]

  if (hasLoadError) {
    return <LoginLoadError onRetry={retryLoad} />
  }

  return (
    <section className="flex min-h-svh w-full items-center justify-center bg-muted/40 px-4 py-8">
      <div className="w-full max-w-md">
        <Card variant="auth">
          <CardHeader className="text-center">
            <CardTitle as="h1">Вход в систему</CardTitle>
            <CardDescription>Введите ваши учётные данные</CardDescription>
          </CardHeader>
          <CardContent>
            {flow ? (
              <form className="flex flex-col gap-5" noValidate onSubmit={submit}>
                {formError ? (
                  <Alert variant="destructiveSubtle">
                    <AlertCircleIcon aria-hidden="true" />
                    <AlertTitle>{formError}</AlertTitle>
                  </Alert>
                ) : null}
                <FieldGroup>
                  <Field data-invalid={Boolean(loginError) || undefined}>
                    <Label className="cursor-pointer" htmlFor="login">
                      Логин
                    </Label>
                    <Input
                      aria-describedby={loginError ? 'login-error' : undefined}
                      aria-invalid={Boolean(loginError) || undefined}
                      autoComplete="username"
                      disabled={flow.login.disabled || isSubmitting}
                      id="login"
                      size="lg"
                      type="text"
                      variant="auth"
                      {...register('login', { onChange: clearFormError })}
                    />
                    {loginError ? <FieldError id="login-error">{loginError}</FieldError> : null}
                  </Field>
                  <Field data-invalid={Boolean(passwordError) || undefined}>
                    <Label className="cursor-pointer" htmlFor="password">
                      Пароль
                    </Label>
                    <InputGroup size="lg" variant="auth">
                      <InputGroupInput
                        aria-describedby={passwordError ? 'password-error' : undefined}
                        aria-invalid={Boolean(passwordError) || undefined}
                        autoComplete="current-password"
                        disabled={flow.password.disabled || isSubmitting}
                        id="password"
                        size="lg"
                        type={isPasswordVisible ? 'text' : 'password'}
                        variant="auth"
                        {...register('password', { onChange: clearFormError })}
                      />
                      <InputGroupAddon>
                        <InputGroupButton
                          aria-label={isPasswordVisible ? 'Скрыть пароль' : 'Показать пароль'}
                          aria-pressed={isPasswordVisible}
                          disabled={isSubmitting}
                          onClick={() => setIsPasswordVisible((visible) => !visible)}
                          type="button"
                        >
                          {isPasswordVisible ? (
                            <EyeOffIcon data-icon="inline-end" />
                          ) : (
                            <EyeIcon data-icon="inline-end" />
                          )}
                        </InputGroupButton>
                      </InputGroupAddon>
                    </InputGroup>
                    {passwordError ? (
                      <FieldError id="password-error">{passwordError}</FieldError>
                    ) : null}
                  </Field>
                </FieldGroup>
                <Button disabled={isSubmitting} size="lg" type="submit">
                  {isSubmitting ? <Spinner data-icon="inline-start" /> : null}
                  {isSubmitting ? 'Входим…' : 'Войти'}
                </Button>
              </form>
            ) : (
              <PendingLogin />
            )}
          </CardContent>
          <CardFooter>
            <p>Если забыли пароль, обратитесь к администратору системы.</p>
          </CardFooter>
        </Card>
      </div>
    </section>
  )
}

function LoginLoadError({ onRetry }: Readonly<{ onRetry: () => void }>) {
  return (
    <section
      className="flex min-h-svh flex-col items-center justify-center p-4"
      data-testid="login-load-error"
    >
      <h1 className="z-10 mb-2 text-center text-2xl font-bold">
        Не удалось открыть страницу входа
      </h1>
      <p className="z-10 mb-4 text-center text-lg text-muted-foreground">
        Сессия входа устарела или сервис временно недоступен.
      </p>
      <div className="z-10">
        <Button className="mt-4" onClick={onRetry} size="lg">
          Попробовать снова
        </Button>
      </div>
    </section>
  )
}
