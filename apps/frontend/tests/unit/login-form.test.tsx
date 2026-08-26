import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({ restartLoginFlow: vi.fn<() => void>() }))

vi.mock('@/features/auth/login-flow', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/auth/login-flow')>()
  return { ...actual, restartLoginFlow: mocks.restartLoginFlow }
})

import { LoginForm } from '@/components/Auth/LoginForm'
import { ERROR_VALIDATION_INVALID_CREDENTIALS } from '@/features/auth/login-flow'

const flow = {
  id: 'login-flow-id',
  type: 'browser',
  ui: {
    action: '/self-service/login?flow=login-flow-id',
    method: 'POST',
    messages: [],
    nodes: [
      {
        type: 'input',
        messages: [],
        attributes: {
          disabled: false,
          name: 'csrf_token',
          node_type: 'input',
          type: 'hidden',
          value: 'csrf-token',
        },
      },
      {
        type: 'input',
        messages: [],
        attributes: {
          disabled: false,
          name: 'identifier',
          node_type: 'input',
          required: true,
          type: 'text',
          value: 'operator',
        },
      },
      {
        type: 'input',
        messages: [],
        attributes: {
          disabled: false,
          name: 'password',
          node_type: 'input',
          required: true,
          type: 'password',
        },
      },
      {
        type: 'input',
        messages: [],
        attributes: {
          disabled: false,
          name: 'method',
          node_type: 'input',
          type: 'submit',
          value: 'password',
        },
      },
    ],
  },
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  mocks.restartLoginFlow.mockReset()
})

describe('LoginForm', () => {
  it('shows a loading state before the flow arrives', () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => undefined)))

    render(<LoginForm flowId="login-flow-id" />)

    expect(screen.getByRole('status', { name: 'Загрузка формы входа' })).toHaveAttribute(
      'aria-busy',
      'true',
    )
  })

  it('shows a recovery page and restarts the login flow when loading fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockRejectedValue(new TypeError('Network unavailable')),
    )
    const user = userEvent.setup()

    render(<LoginForm flowId="login-flow-id" />)

    expect(
      await screen.findByRole('heading', { name: 'Не удалось открыть страницу входа' }),
    ).toBeVisible()
    expect(screen.getByTestId('login-load-error')).toBeInTheDocument()
    expect(screen.queryByText('Не удалось загрузить форму входа.')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Логин')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Попробовать снова' }))

    expect(mocks.restartLoginFlow).toHaveBeenCalledOnce()
  })

  it('uses labels, browser autocomplete values, and an accessible password switch', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(jsonResponse(flow)))
    const user = userEvent.setup()

    render(<LoginForm flowId="login-flow-id" />)

    const login = await screen.findByLabelText('Логин')
    const password = screen.getByLabelText('Пароль')
    const passwordSwitch = screen.getByRole('button', { name: 'Показать пароль' })

    expect(login).toHaveAttribute('autocomplete', 'username')
    expect(login).not.toHaveAttribute('placeholder')
    expect(password).toHaveAttribute('autocomplete', 'current-password')
    expect(password).not.toHaveAttribute('placeholder')
    expect(password).toHaveAttribute('type', 'password')
    expect(passwordSwitch).toHaveAttribute('type', 'button')
    expect(passwordSwitch).toHaveAttribute('aria-pressed', 'false')

    await user.click(passwordSwitch)

    expect(password).toHaveAttribute('type', 'text')
    expect(screen.getByRole('button', { name: 'Скрыть пароль' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('validates blank fields locally without submitting to Kratos', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(jsonResponse(flow))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    render(<LoginForm flowId="login-flow-id" />)
    const login = await screen.findByLabelText('Логин')
    await user.clear(login)
    await user.click(screen.getByRole('button', { name: 'Войти' }))

    expect(await screen.findByText('Введите логин.')).toBeInTheDocument()
    expect(screen.getByText('Введите пароль.')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('disables a repeated submit, shows progress, and clears only the password after bad credentials', async () => {
    let resolveUpdate: ((value: Response) => void) | undefined
    const pendingUpdate = new Promise<Response>((resolve) => {
      resolveUpdate = resolve
    })
    vi.stubGlobal(
      'fetch',
      vi
        .fn<typeof fetch>()
        .mockResolvedValueOnce(jsonResponse(flow))
        .mockResolvedValueOnce(jsonResponse(flow))
        .mockReturnValueOnce(pendingUpdate)
        .mockResolvedValueOnce(
          jsonResponse(
            {
              ...flow,
              ui: {
                ...flow.ui,
                messages: [
                  {
                    id: ERROR_VALIDATION_INVALID_CREDENTIALS,
                    text: 'Unexpected source text',
                    type: 'error',
                  },
                ],
              },
            },
            400,
          ),
        ),
    )
    const user = userEvent.setup()

    render(<LoginForm flowId="login-flow-id" />)
    const login = await screen.findByLabelText('Логин')
    const password = screen.getByLabelText('Пароль')
    await user.clear(login)
    await user.type(login, 'operator')
    await user.type(password, 'wrong')
    await user.click(screen.getByRole('button', { name: 'Войти' }))

    expect(await screen.findByRole('button', { name: /Входим…/ })).toBeDisabled()
    expect(screen.getByRole('status', { name: 'Загрузка' })).toBeInTheDocument()

    resolveUpdate?.(
      jsonResponse(
        {
          ...flow,
          ui: {
            ...flow.ui,
            messages: [
              {
                id: ERROR_VALIDATION_INVALID_CREDENTIALS,
                text: 'Unexpected source text',
                type: 'error',
              },
            ],
          },
        },
        400,
      ),
    )

    const credentialsAlert = await screen.findByRole('alert')
    expect(credentialsAlert).toHaveTextContent('Неверный логин или пароль')
    expect(credentialsAlert.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
    expect(login).toHaveValue('operator')
    expect(password).toHaveValue('')

    await user.type(password, 'retry')

    expect(screen.queryByText('Неверный логин или пароль')).not.toBeInTheDocument()
  })

  it('shows a submit network error without leaving the form', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn<typeof fetch>()
        .mockResolvedValueOnce(jsonResponse(flow))
        .mockResolvedValueOnce(jsonResponse(flow))
        .mockRejectedValueOnce(new TypeError('Network unavailable')),
    )
    const user = userEvent.setup()

    render(<LoginForm flowId="login-flow-id" />)
    const login = await screen.findByLabelText('Логин')
    const password = screen.getByLabelText('Пароль')
    await user.clear(login)
    await user.type(login, 'operator')
    await user.type(password, 'secret')
    await user.click(screen.getByRole('button', { name: 'Войти' }))

    expect(
      await screen.findByText('Не удалось выполнить вход. Попробуйте ещё раз.'),
    ).toBeInTheDocument()
    expect(login).toHaveValue('operator')
    expect(password).toHaveValue('secret')
  })
})

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}
