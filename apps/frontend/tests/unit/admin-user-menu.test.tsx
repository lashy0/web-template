import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SidebarProvider } from '@web-app/ui/components/sidebar'

import { AdminUserMenu } from '@/components/Admin/AdminUserMenu'
import { currentUserQueryKey, type AuthenticatedUser } from '@/features/auth/auth-api'

const currentUser: AuthenticatedUser = {
  id: 'user-id',
  name: 'Администратор',
  login: 'admin',
  role: 'administrator',
}

describe('User menu', () => {
  it('opens the account menu with the logout action', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    queryClient.setQueryData(currentUserQueryKey, currentUser)
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockReturnValue({
        matches: false,
        addEventListener: vi.fn<() => void>(),
        removeEventListener: vi.fn<() => void>(),
      }),
    )
    const user = userEvent.setup()

    render(
      <QueryClientProvider client={queryClient}>
        <SidebarProvider>
          <AdminUserMenu user={currentUser} />
        </SidebarProvider>
      </QueryClientProvider>,
    )

    await user.click(screen.getByTestId('user-menu'))

    expect(await screen.findByRole('menuitem', { name: 'Выйти' })).toBeVisible()
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
})
