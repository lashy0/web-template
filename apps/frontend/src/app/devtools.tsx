import { lazy, Suspense } from 'react'

const QueryDevtools = import.meta.env.DEV
  ? lazy(() =>
      import('@tanstack/react-query-devtools').then(({ ReactQueryDevtools }) => ({
        default: ReactQueryDevtools,
      })),
    )
  : null

const RouterDevtools = import.meta.env.DEV
  ? lazy(() =>
      import('@tanstack/react-router-devtools').then(({ TanStackRouterDevtools }) => ({
        default: TanStackRouterDevtools,
      })),
    )
  : null

export function AppDevtools() {
  if (!QueryDevtools || !RouterDevtools) {
    return null
  }

  return (
    <Suspense fallback={null}>
      <QueryDevtools buttonPosition="bottom-left" />
      <RouterDevtools position="bottom-right" />
    </Suspense>
  )
}
