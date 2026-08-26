import { Outlet, createFileRoute, redirect } from '@tanstack/react-router'

import { AppShell } from '@/components/AppShell'
import { RequestError, currentUserQueryOptions } from '@/features/auth/auth-api'

export const Route = createFileRoute('/_layout')({
  beforeLoad: async ({ context }) => {
    try {
      const currentUser = await context.queryClient.fetchQuery(currentUserQueryOptions)
      return { currentUser }
    } catch (error) {
      if (error instanceof RequestError && error.status === 401) {
        throw redirect({ to: '/login', search: { flow: undefined, return_to: undefined } })
      }
      throw error
    }
  },
  component: ProtectedLayout,
})

function ProtectedLayout() {
  const { currentUser } = Route.useRouteContext()

  if (currentUser.role === 'administrator') return <Outlet />

  return (
    <AppShell currentUser={currentUser}>
      <Outlet />
    </AppShell>
  )
}
