import { cleanup, render, screen } from '@testing-library/react'
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

  it('lists production orders before batches', async () => {
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

    await user.click(screen.getByRole('button', { name: 'Производство' }))

    const batches = screen.getByRole('link', { name: 'Партии' })
    const orders = screen.getByRole('link', { name: 'Заказы' })
    expect(batches).toHaveAttribute('href', '/admin/production/batches')
    expect(orders).toHaveAttribute('href', '/admin/production/production-orders')
    expect(orders.compareDocumentPosition(batches) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('opens collapsed navigation on hover and keeps it open while entering the menu', async () => {
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

    const user = userEvent.setup()
    const trigger = screen.getByRole('button', { name: 'Пользователи' })
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()

    await user.hover(trigger)
    const listItem = await screen.findByRole('menuitem', { name: 'Список' })
    expect(listItem).toHaveAttribute('href', '/admin/user/users')
    expect(listItem).toHaveAttribute('aria-current', 'page')
    await user.hover(listItem)
    expect(screen.getByRole('menuitem', { name: 'Аудит' })).toHaveAttribute(
      'href',
      '/admin/user/audit',
    )

    await user.keyboard('{Escape}')
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()

    trigger.focus()
    await user.keyboard('{ArrowDown}')
    expect(await screen.findByRole('menuitem', { name: 'Список' })).toHaveFocus()
    await user.keyboard('{ArrowDown}')
    expect(screen.getByRole('menuitem', { name: 'Аудит' })).toHaveFocus()
  })

  it('replaces the previous flyout when hovering another section', async () => {
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
      <SidebarProvider defaultOpen={false}>
        <AdminNavigation />
      </SidebarProvider>,
    )

    await user.hover(screen.getByRole('button', { name: 'Дефекты' }))
    expect(await screen.findByRole('menuitem', { name: 'Группы' })).toBeVisible()
    await user.hover(screen.getByRole('button', { name: 'КГ' }))
    expect(await screen.findByRole('menuitem', { name: 'Префиксы' })).toBeVisible()
    expect(screen.getAllByRole('menu')).toHaveLength(1)
    expect(screen.queryByRole('menuitem', { name: 'Группы' })).not.toBeInTheDocument()

    await user.hover(screen.getByRole('menuitem', { name: 'Версии' }))
    expect(screen.getByRole('menuitem', { name: 'Префиксы' })).toBeVisible()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
