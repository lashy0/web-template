import { afterEach, describe, expect, it, vi } from 'vitest'

import { createBrowserLogoutUrl } from '@/features/auth/logout-flow'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('browser logout flow', () => {
  it('requests a one-time logout URL instead of navigating to the flow endpoint', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse({ logout_url: '/self-service/logout?token=one-time-token' }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(createBrowserLogoutUrl()).resolves.toBe(
      '/self-service/logout?token=one-time-token',
    )
    expect(fetchMock).toHaveBeenCalledWith(
      `${window.location.origin}/self-service/logout/browser`,
      expect.objectContaining({ credentials: 'include', method: 'GET' }),
    )
  })
})

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    headers: { 'Content-Type': 'application/json' },
  })
}
