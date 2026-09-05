import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ViewPakAccessKey } from '@/components/Pak/Paks/ViewPakAccessKey'

const api = vi.hoisted(() => ({
  getPakAccessKey: vi.fn<(pakId: string) => Promise<string>>(),
  rotatePakAccessKey: vi.fn<(pakId: string) => Promise<string>>(),
}))

vi.mock('@/features/paks/paks-api', () => ({
  getPakAccessKey: api.getPakAccessKey,
  pakKindLabels: { otk_line: 'Линия ОТК' },
  rotatePakAccessKey: api.rotatePakAccessKey,
}))

const pak = {
  archivedAt: null,
  code: 'PAK-01',
  id: 'pak-1',
  kind: 'otk_line' as const,
  lastSeenAt: null,
  oauthClientId: 'pak-1',
  status: 'active' as const,
}

function renderDialog(open: boolean) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ViewPakAccessKey onOpenChange={vi.fn<(open: boolean) => void>()} open={open} pak={pak} />
    </QueryClientProvider>,
  )
}

describe('ViewPakAccessKey', () => {
  it('loads the key when a controlled dialog is opened', async () => {
    api.getPakAccessKey.mockResolvedValue('secret')
    const view = renderDialog(false)

    view.rerender(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <ViewPakAccessKey onOpenChange={vi.fn<(open: boolean) => void>()} open pak={pak} />
      </QueryClientProvider>,
    )

    await waitFor(() => expect(api.getPakAccessKey).toHaveBeenCalledWith('pak-1'))
  })

  it('reveals the loaded key and rotates it after inline confirmation', async () => {
    const writeText = vi.fn<(value: string) => Promise<void>>().mockResolvedValue()
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })
    api.getPakAccessKey.mockResolvedValue('old-secret')
    api.rotatePakAccessKey.mockResolvedValue('new-secret')
    renderDialog(true)

    await screen.findByText('Данные ПАК')
    await screen.findByText('••••••••••••••••')
    expect(screen.queryByText('old-secret')).not.toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Показать ключ доступа'))
    expect(screen.getByText('old-secret')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Ротировать ключ'))
    expect(screen.getByText('Старый ключ перестанет работать.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Ротировать' }))
    await waitFor(() => expect(api.rotatePakAccessKey).toHaveBeenCalledWith('pak-1'))
    await waitFor(() => expect(writeText).toHaveBeenLastCalledWith('new-secret'))
    expect(await screen.findByText('••••••••••••••••')).toBeInTheDocument()
    expect(screen.queryByText('new-secret')).not.toBeInTheDocument()
  })

  it('copies the actual values while keeping the access key hidden', async () => {
    const writeText = vi.fn<(value: string) => Promise<void>>().mockResolvedValue()
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })
    api.getPakAccessKey.mockResolvedValue('secret')
    renderDialog(true)

    await screen.findByText('••••••••••••••••')
    expect(screen.queryByText('secret')).not.toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Копировать Client ID'))
    await waitFor(() => expect(writeText).toHaveBeenLastCalledWith('pak-1'))
    expect(screen.getByLabelText('Копировать Client ID').querySelector('svg')).toHaveClass(
      'lucide-check',
    )

    fireEvent.click(screen.getByLabelText('Копировать ключ доступа'))
    await waitFor(() => expect(writeText).toHaveBeenLastCalledWith('secret'))
    expect(screen.getByLabelText('Копировать ключ доступа').querySelector('svg')).toHaveClass(
      'lucide-check',
    )
    expect(screen.queryByText('secret')).not.toBeInTheDocument()
  })
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})
