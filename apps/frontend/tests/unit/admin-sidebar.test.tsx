import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SidebarProvider } from '@web-app/ui/components/sidebar'

import { AdminSidebar } from '@/components/Admin/AdminSidebar'
import { currentUserQueryKey, type AuthenticatedUser } from '@/features/auth/auth-api'

const currentUser: AuthenticatedUser = {
  id: 'user-id',
  name: 'Администратор',
  login: 'admin',
  role: 'administrator',
}

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, to, ...props }: React.ComponentProps<'a'> & { to?: string }) => (
    <a href={to ?? '/'} {...props}>
      {children}
    </a>
  ),
  useRouterState: () => ({ location: { pathname: '/admin/user/users' } }),
}))

describe('AdminSidebar', () => {
  it('collapses from its header and expands again', async () => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockReturnValue({
        matches: false,
        addEventListener: vi.fn<() => void>(),
        removeEventListener: vi.fn<() => void>(),
      }),
    )
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    queryClient.setQueryData(currentUserQueryKey, currentUser)
    const user = userEvent.setup()

    render(
      <QueryClientProvider client={queryClient}>
        <SidebarProvider>
          <AdminSidebar currentUser={currentUser} />
        </SidebarProvider>
      </QueryClientProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Свернуть боковую панель' }))

    expect(screen.getByRole('button', { name: 'Развернуть боковую панель' })).toBeVisible()
    expect(document.querySelector('[data-slot="sidebar"]')).toHaveAttribute(
      'data-state',
      'collapsed',
    )

    await user.click(screen.getByRole('button', { name: 'Развернуть боковую панель' }))

    expect(screen.getByRole('button', { name: 'Свернуть боковую панель' })).toBeVisible()
  })

  it('does not render the desktop collapse tooltip in the mobile drawer', async () => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockReturnValue({
        matches: true,
        addEventListener: vi.fn<() => void>(),
        removeEventListener: vi.fn<() => void>(),
      }),
    )
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    queryClient.setQueryData(currentUserQueryKey, currentUser)

    render(
      <QueryClientProvider client={queryClient}>
        <SidebarProvider defaultOpen={false}>
          <AdminSidebar currentUser={currentUser} />
        </SidebarProvider>
      </QueryClientProvider>,
    )

    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).toBeNull()
    })
  })
})

afterEach(() => {
  document.cookie = 'sidebar_state=; path=/; max-age=0'
  vi.unstubAllGlobals()
})
