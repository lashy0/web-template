import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AuthErrorPage, Route } from '@/routes/auth/error'

describe('AuthErrorPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('provides a browser navigation link to start a fresh login flow', () => {
    render(<AuthErrorPage />)

    expect(screen.getByRole('link', { name: 'Войти снова' })).toHaveAttribute(
      'href',
      '/self-service/login/browser',
    )
  })

  it('redirects an authenticated user to the application home page', async () => {
    const beforeLoad = Route.options.beforeLoad
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 200 })))

    expect(beforeLoad).toBeTypeOf('function')
    await expect(beforeLoad?.({} as never)).rejects.toMatchObject({
      options: { to: '/' },
    })

    expect(fetch).toHaveBeenCalledWith('/sessions/whoami', { credentials: 'include' })
  })

  it('allows a user without a session to open the error page', async () => {
    const beforeLoad = Route.options.beforeLoad
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 401 })))

    await expect(beforeLoad?.({} as never)).resolves.toBeUndefined()
  })
})
