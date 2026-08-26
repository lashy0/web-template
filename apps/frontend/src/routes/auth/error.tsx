import { createFileRoute, redirect } from '@tanstack/react-router'
import { Button } from '@web-app/ui/components/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@web-app/ui/components/card'

export const Route = createFileRoute('/auth/error')({
  beforeLoad: redirectAuthenticatedUser,
  component: AuthErrorPage,
})

export async function redirectAuthenticatedUser() {
  const response = await fetch('/sessions/whoami', { credentials: 'include' })

  if (response.ok) {
    throw redirect({ to: '/' })
  }
}

export function AuthErrorPage() {
  return (
    <section className="flex min-h-svh w-full items-center justify-center bg-muted/40 px-4 py-8">
      <div className="w-full max-w-md">
        <Card variant="auth">
          <CardHeader className="items-center text-center">
            <CardTitle as="h1">Сессия истекла</CardTitle>
            <CardDescription>Время действия формы входа закончилось.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-center text-sm text-muted-foreground">
              Начните вход заново, чтобы получить новую безопасную форму.
            </p>
          </CardContent>
          <CardFooter>
            <Button className="w-full" render={<a href="/self-service/login/browser" />} size="lg">
              Войти снова
            </Button>
          </CardFooter>
        </Card>
      </div>
    </section>
  )
}
