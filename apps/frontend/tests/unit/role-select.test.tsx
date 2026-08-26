import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'

import { AddUser } from '@/components/User/Users/AddUser'

afterEach(() => {
  cleanup()
})

describe('New user role select', () => {
  it('shows the localized name for the selected default role', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <AddUser />
      </QueryClientProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Добавить' }))

    const selectedValue = document.querySelector('[data-slot="select-value"]')
    expect(selectedValue).toHaveTextContent('Оператор')

    await user.click(screen.getByRole('combobox'))
    await user.click(screen.getByRole('option', { name: 'Менеджер' }))

    expect(selectedValue).toHaveTextContent('Менеджер')
  })

  it('allows the password to be shown temporarily', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <AddUser />
      </QueryClientProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Добавить' }))

    const password = screen.getByLabelText('Пароль')
    expect(password).toHaveAttribute('type', 'password')

    await user.click(screen.getByRole('button', { name: 'Показать пароль' }))

    await waitFor(() => expect(screen.getByLabelText('Пароль')).toHaveAttribute('type', 'text'))
    expect(screen.getByRole('button', { name: 'Скрыть пароль' })).toBeVisible()
  })
})
