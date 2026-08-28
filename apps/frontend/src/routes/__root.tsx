import { Outlet, createRootRouteWithContext } from '@tanstack/react-router'

import { AppDevtools } from '@/app/devtools'
import type { RouterContext } from '@/app/router'
import ErrorComponent from '@/components/Common/ErrorComponent'
import NotFound from '@/components/Common/NotFound'

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
  errorComponent: ErrorComponent,
  notFoundComponent: NotFound,
})

function RootLayout() {
  return (
    <>
      <Outlet />
      <AppDevtools />
    </>
  )
}
