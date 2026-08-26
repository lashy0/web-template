import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AddUser } from '@/components/User/Users/AddUser'
import { UserActionsMenu } from '@/components/User/Users/UserActionsMenu'
import {
  RequestError,
  type CreateUserInput,
  type UpdateUserInput,
  type User,
} from '@/features/users/users-api'

const { createUserMock, updateUserMock, updateUserPasswordMock } = vi.hoisted(() => ({
  createUserMock: vi.fn<(input: CreateUserInput) => Promise<User>>(),
  updateUserMock: vi.fn<(userId: string, input: UpdateUserInput) => Promise<User>>(),
  updateUserPasswordMock: vi.fn<(userId: string, password: string) => Promise<void>>(),
}))

vi.mock('@/features/users/users-api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/features/users/users-api')>()),
  createUser: createUserMock,
  updateUser: updateUserMock,
  updateUserPassword: updateUserPasswordMock,
}))

vi.mock('@/hooks/useAuth', () => ({
  default: () => ({ user: { id: 'current-user' } }),
}))

afterEach(() => {
  cleanup()
  createUserMock.mockReset()
  updateUserMock.mockReset()
  updateUserPasswordMock.mockReset()
})

describe('UserActionsMenu', () => {
  it('keeps the edit dialog open after selecting the edit action', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <UserActionsMenu
          user={{
            id: 'another-user',
            authState: 'active',
            archivedAt: null,
            login: 'another.user',
            name: 'Другой пользователь',
            role: 'operator',
          }}
        />
      </QueryClientProvider>,
    )

    await user.click(
      screen.getByRole('button', { name: 'Действия с пользователем Другой пользователь' }),
    )
    await user.click(await screen.findByRole('menuitem', { name: 'Изменить' }))

    expect(screen.getByRole('heading', { name: 'Изменить пользователя' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Сохранить' })).toBeDisabled()

    await user.type(screen.getByLabelText('Имя'), ' 2')

    expect(screen.getByRole('button', { name: 'Сохранить' })).toBeEnabled()
  })

  it('offers permanent deletion from the actions menu', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <UserActionsMenu
          user={{
            archivedAt: null,
            id: 'another-user',
            authState: 'active',
            login: 'another.user',
            name: 'Другой пользователь',
            role: 'operator',
          }}
        />
      </QueryClientProvider>,
    )

    await user.click(
      screen.getByRole('button', { name: 'Действия с пользователем Другой пользователь' }),
    )
    await user.click(await screen.findByRole('menuitem', { name: 'Удалить' }))

    expect(screen.getByRole('heading', { name: 'Удалить пользователя навсегда?' })).toBeVisible()
  })

  it('changes a user password from the actions menu', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    updateUserPasswordMock.mockResolvedValueOnce()

    render(
      <QueryClientProvider client={queryClient}>
        <UserActionsMenu
          user={{
            archivedAt: null,
            id: 'another-user',
            authState: 'active',
            login: 'another.user',
            name: 'Другой пользователь',
            role: 'operator',
          }}
        />
      </QueryClientProvider>,
    )

    await user.click(
      screen.getByRole('button', { name: 'Действия с пользователем Другой пользователь' }),
    )
    await user.click(await screen.findByRole('menuitem', { name: 'Сменить пароль' }))
    await user.type(screen.getByLabelText('Новый пароль'), 'secure-password')
    await user.type(screen.getByLabelText('Повторите пароль'), 'different-password')

    expect(await screen.findByRole('alert')).toHaveTextContent('Пароли не совпадают.')

    await user.clear(screen.getByLabelText('Повторите пароль'))
    await user.type(screen.getByLabelText('Повторите пароль'), 'secure-password')
    await user.click(screen.getByRole('button', { name: 'Сменить пароль' }))

    expect(updateUserPasswordMock).toHaveBeenCalledWith('another-user', 'secure-password')
  })

  it('allows user creation with the initial form values', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <AddUser />
      </QueryClientProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Добавить' }))

    expect(screen.getByRole('button', { name: 'Создать' })).toBeEnabled()
  })

  it('disables autocomplete except for the generated-password field', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <AddUser />
      </QueryClientProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Добавить' }))

    expect(screen.getByLabelText('Имя')).toHaveAttribute('autocomplete', 'off')
    expect(screen.getByLabelText('Логин')).toHaveAttribute('autocomplete', 'off')
    expect(screen.getByLabelText('Пароль')).toHaveAttribute('autocomplete', 'new-password')
  })

  it('keeps the error border on the password group rather than its inner input', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <AddUser />
      </QueryClientProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Добавить' }))
    await user.type(screen.getByLabelText('Пароль'), 'short')

    expect(screen.getByLabelText('Пароль')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Пароль')).toHaveClass(
      'aria-invalid:border-0',
      'aria-invalid:ring-0',
    )
  })

  it('shows an existing-login error next to the login field when editing a user', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    updateUserMock.mockRejectedValueOnce(new RequestError(409, 'login_already_exists'))

    render(
      <QueryClientProvider client={queryClient}>
        <UserActionsMenu
          user={{
            id: 'another-user',
            authState: 'active',
            archivedAt: null,
            login: 'another.user',
            name: 'Другой пользователь',
            role: 'operator',
          }}
        />
      </QueryClientProvider>,
    )

    await user.click(
      screen.getByRole('button', { name: 'Действия с пользователем Другой пользователь' }),
    )
    await user.click(await screen.findByRole('menuitem', { name: 'Изменить' }))

    const login = screen.getByLabelText('Логин')
    await user.clear(login)
    await user.type(login, 'existing.login')
    await user.click(screen.getByRole('button', { name: 'Сохранить' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Этот логин уже занят. Выберите другой.',
    )
    expect(login).toHaveFocus()

    await user.type(login, '2')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows an existing-login error next to the login field when creating a user', async () => {
    const user = userEvent.setup()
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    createUserMock.mockRejectedValueOnce(new RequestError(409, 'login_already_exists'))

    render(
      <QueryClientProvider client={queryClient}>
        <AddUser />
      </QueryClientProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Добавить' }))
    await user.type(screen.getByLabelText('Имя'), 'Новый пользователь')
    const login = screen.getByLabelText('Логин')
    await user.type(login, 'existing.login')
    await user.type(screen.getByLabelText('Пароль'), 'secure-password')
    await user.click(screen.getByRole('button', { name: 'Создать' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Этот логин уже занят. Выберите другой.',
    )
    expect(login).toHaveFocus()
  })
})
