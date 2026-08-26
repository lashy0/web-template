import { createFileRoute } from '@tanstack/react-router'

import { LoginForm } from '@/components/Auth/LoginForm'

export const Route = createFileRoute('/login')({
  validateSearch: (search: Record<string, unknown>) => ({
    flow: typeof search.flow === 'string' ? search.flow : undefined,
    return_to: typeof search.return_to === 'string' ? search.return_to : undefined,
  }),
  component: LoginPage,
})

function LoginPage() {
  const { flow } = Route.useSearch()
  return <LoginForm flowId={flow} />
}
