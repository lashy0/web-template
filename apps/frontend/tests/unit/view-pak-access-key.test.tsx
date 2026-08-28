import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ViewPakAccessKey } from '@/components/Pak/Paks/ViewPakAccessKey'

const api = vi.hoisted(() => ({
  getPakAccessKey: vi.fn<(pakId: string) => Promise<string>>(),
}))

vi.mock('@/features/paks/paks-api', () => ({
  getPakAccessKey: api.getPakAccessKey,
}))

const pak = {
  archivedAt: null,
  code: 'PAK-01',
  id: 'pak-1',
  kind: 'OTK_LINE' as const,
  lastSeenAt: null,
  oauthClientId: 'pak-1',
  status: 'active' as const,
}

function renderDialog(open: boolean) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ViewPakAccessKey onOpenChange={vi.fn()} open={open} pak={pak} />
    </QueryClientProvider>,
  )
}

describe('ViewPakAccessKey', () => {
  it('loads the key when a controlled dialog is opened', async () => {
    api.getPakAccessKey.mockResolvedValue('secret')
    const screen = renderDialog(false)

    screen.rerender(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <ViewPakAccessKey onOpenChange={vi.fn()} open pak={pak} />
      </QueryClientProvider>,
    )

    await waitFor(() => expect(api.getPakAccessKey).toHaveBeenCalledWith('pak-1'))
  })
})

afterEach(() => vi.clearAllMocks())
