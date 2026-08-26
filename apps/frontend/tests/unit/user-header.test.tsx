import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { Header } from '@/components/Header'
import { currentUserQueryKey, type AuthenticatedUser } from '@/features/auth/auth-api'

const currentUser: AuthenticatedUser = {
  id: 'user-id',
  name: 'Иван Иванов',
  login: 'ivanov',
  role: 'manager',
}

describe('Header', () => {
  it('shows the current user and opens the account menu', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    queryClient.setQueryData(currentUserQueryKey, currentUser)
    const user = userEvent.setup()

    render(
      <QueryClientProvider client={queryClient}>
        <Header currentUser={currentUser} />
      </QueryClientProvider>,
    )

    expect(screen.getByText('Иван Иванов')).toBeVisible()
    expect(screen.getByText('Менеджер')).toBeVisible()

    expect(screen.getByTestId('user-menu')).toHaveAccessibleName('Меню пользователя: Иван Иванов')

    await user.click(screen.getByTestId('user-menu'))

    expect(await screen.findByText('ivanov')).toBeVisible()
    expect(await screen.findByRole('menuitem', { name: 'Выйти' })).toBeVisible()
  })
})
