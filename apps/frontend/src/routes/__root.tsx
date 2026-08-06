import { Link, Outlet, createRootRouteWithContext } from '@tanstack/react-router'
import type { ErrorComponentProps } from '@tanstack/react-router'
import { Button, buttonVariants } from '@web-app/ui/components/button'
import { cn } from '@web-app/ui/lib/utils'

import { APP_NAME } from '@/app/config'
import { AppDevtools } from '@/app/devtools'
import type { RouterContext } from '@/app/router'

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
  errorComponent: RootErrorPage,
  notFoundComponent: NotFoundPage,
})

function RootLayout() {
  return (
    <div className="flex min-h-svh flex-col">
      <header className="border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center px-4 sm:px-6">
          <Link className="font-semibold tracking-tight" to="/">
            {APP_NAME}
          </Link>
        </div>
      </header>
      <main className="flex flex-1">
        <Outlet />
      </main>
      <footer className="border-t">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center px-4 text-sm text-muted-foreground sm:px-6">
          {APP_NAME}
        </div>
      </footer>
      <AppDevtools />
    </div>
  )
}

export function NotFoundPage() {
  return (
    <CenteredMessage title="Page not found">
      <p className="max-w-md text-pretty text-muted-foreground">
        The page you requested does not exist.
      </p>
      <Link className={cn(buttonVariants(), 'mt-6')} to="/">
        Back to home
      </Link>
    </CenteredMessage>
  )
}

export function RootErrorPage({ error }: ErrorComponentProps) {
  return (
    <CenteredMessage title="Something went wrong">
      <p className="max-w-md text-pretty text-muted-foreground">
        The application could not render this page. Reload it to try again.
      </p>
      {import.meta.env.DEV ? (
        <pre className="mt-6 max-w-2xl overflow-auto rounded-lg border bg-muted p-4 text-left text-xs">
          {error.message}
        </pre>
      ) : null}
      <Button className="mt-6" onClick={() => window.location.reload()}>
        Reload
      </Button>
    </CenteredMessage>
  )
}

function CenteredMessage({
  children,
  title,
}: Readonly<{
  children: React.ReactNode
  title: string
}>) {
  return (
    <section className="mx-auto flex w-full max-w-6xl flex-1 flex-col items-center justify-center px-4 py-16 text-center sm:px-6">
      <h1 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h1>
      <div className="mt-3 flex flex-col items-center">{children}</div>
    </section>
  )
}
