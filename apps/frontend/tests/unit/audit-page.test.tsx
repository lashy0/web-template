import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({ listUserAudit: vi.fn() }))

vi.mock('@/features/users/users-api', () => ({ listUserAudit: mocks.listUserAudit }))

import { Audit } from '@/routes/_layout/admin/user/audit'
import PendingAudit from '@/components/User/Audit/PendingAudit'

function renderAudit() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <Audit />
    </QueryClientProvider>,
  )
}

describe('Audit', () => {
  afterEach(cleanup)

  beforeEach(() => {
    mocks.listUserAudit.mockReset()
  })

  it('keeps the page title visible while audit data is loading', () => {
    mocks.listUserAudit.mockReturnValue(new Promise(() => undefined))

    renderAudit()

    expect(screen.getByLabelText('Загрузка аудита пользователей')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Аудит пользователей' })).toBeVisible()
  })

  it('shows the page title in the route-loading skeleton', () => {
    render(<PendingAudit showPageHeader />)

    expect(screen.getByRole('heading', { name: 'Аудит пользователей' })).toBeVisible()
    expect(screen.getByLabelText('Загрузка аудита пользователей')).toBeVisible()
  })

  it('shows an error instead of an endless skeleton when the audit request fails', async () => {
    mocks.listUserAudit.mockRejectedValue(new Error('Migration has not been applied'))

    renderAudit()

    expect(await screen.findByRole('alert')).toHaveTextContent('Не удалось загрузить данные')
    expect(screen.queryByLabelText('Загрузка аудита пользователей')).not.toBeInTheDocument()
  })

  it('retries loading audit data after an error', async () => {
    const user = userEvent.setup()
    mocks.listUserAudit
      .mockRejectedValueOnce(new Error('Migration has not been applied'))
      .mockResolvedValueOnce({ items: [], page: 1, pageSize: 25, total: 0 })

    renderAudit()

    await user.click(await screen.findByRole('button', { name: 'Повторить' }))

    expect(await screen.findByText('Нет данных.')).toBeVisible()
    expect(mocks.listUserAudit).toHaveBeenCalledTimes(2)
  })

  it('applies a selected period to the audit query', async () => {
    const user = userEvent.setup()
    mocks.listUserAudit.mockResolvedValue({ items: [], page: 1, pageSize: 25, total: 0 })

    renderAudit()

    await screen.findByText('Нет данных.')
    await user.click(screen.getByRole('button', { name: 'Период' }))
    expect(screen.getByRole('grid')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Последние 7 дней' }))
    await user.click(screen.getByRole('button', { name: 'Применить' }))

    expect(await screen.findByText('Ничего не найдено')).toBeVisible()
    expect(screen.getByText('Попробуйте изменить параметры поиска.')).toBeVisible()

    await waitFor(() => {
      expect(mocks.listUserAudit).toHaveBeenLastCalledWith(
        expect.objectContaining({
          createdFrom: expect.stringMatching(/^\d{4}-\d{2}-\d{2}T/),
          createdTo: expect.stringMatching(/^\d{4}-\d{2}-\d{2}T/),
        }),
      )
    })
  })
})
