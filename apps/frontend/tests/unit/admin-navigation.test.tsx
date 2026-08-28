import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SidebarProvider } from '@web-app/ui/components/sidebar'

import { AdminNavigation } from '@/components/Admin/AdminNavigation'

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, to, ...props }: React.ComponentProps<'a'> & { to?: string }) => (
    <a href={to ?? '/'} {...props}>
      {children}
    </a>
  ),
  useRouterState: () => ({ location: { pathname: '/admin/user/users' } }),
}))

describe('AdminNavigation', () => {
  it('collapses and expands the users subsection', async () => {
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
      <SidebarProvider>
        <AdminNavigation />
      </SidebarProvider>,
    )

    expect(screen.getByRole('link', { name: 'Список' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Список' })).toHaveAttribute(
      'href',
      '/admin/user/users',
    )
    expect(screen.getByRole('link', { name: 'Аудит' })).toHaveAttribute('href', '/admin/user/audit')

    await user.click(screen.getByRole('button', { name: 'Пользователи' }))

    expect(screen.queryByRole('link', { name: 'Список' })).not.toBeInTheDocument()
  })

  it('links the collapsed users icon to the user list and renders its tooltip', () => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockReturnValue({
        matches: false,
        addEventListener: vi.fn<() => void>(),
        removeEventListener: vi.fn<() => void>(),
      }),
    )

    render(
      <SidebarProvider defaultOpen={false}>
        <AdminNavigation />
      </SidebarProvider>,
    )

    const usersLink = screen.getByRole('link', { name: 'Пользователи' })
    expect(usersLink).toHaveAttribute('href', '/admin/user/users')
    expect(screen.getByRole('tooltip', { name: 'Пользователи' })).toHaveTextContent(
      'Пользователи',
    )
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
})
