import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AuditFilter } from '@/components/Common/AuditFilter'

function mockViewport(compact = false) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockReturnValue({
      matches: compact,
      addEventListener: vi.fn<() => void>(),
      removeEventListener: vi.fn<() => void>(),
    }),
  )
}

describe('AuditFilter', () => {
  beforeEach(() => {
    mockViewport()
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 8, 8, 12))
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('restores the applied period after closing changed dates without applying', async () => {
    const user = userEvent.setup()
    render(
      <AuditFilter onApply={() => undefined} value={{ from: '2026-08-10', to: '2026-08-12' }} />,
    )
    await user.click(screen.getByRole('button', { name: /Период:/ }))
    expect(screen.getAllByRole('grid')).toHaveLength(2)
    await user.click(screen.getByRole('button', { name: 'Сегодня' }))
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('grid')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Период:/ }))
    expect(
      document.querySelector('[data-day="10.08.2026"][data-range-start="true"]'),
    ).toBeInTheDocument()
    expect(
      document.querySelector('[data-day="12.08.2026"][data-range-end="true"]'),
    ).toBeInTheDocument()
  })

  it.each([
    ['Сегодня', '2026-09-08', '2026-09-08'],
    ['Вчера', '2026-09-07', '2026-09-07'],
    ['Последние 7 дней', '2026-09-02', '2026-09-08'],
    ['Последние 30 дней', '2026-08-10', '2026-09-08'],
    ['Текущий месяц', '2026-09-01', '2026-09-08'],
    ['Прошлый месяц', '2026-08-01', '2026-08-31'],
  ])('applies %s only after confirmation', async (label, from, to) => {
    const user = userEvent.setup()
    const onApply = vi.fn<(period: { from: string; to: string } | null) => void>()
    render(<AuditFilter onApply={onApply} value={null} />)
    await user.click(screen.getByRole('button', { name: 'Период' }))
    expect(screen.getByRole('button', { name: 'Применить' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: label }))
    expect(onApply).not.toHaveBeenCalled()
    expect(
      document.querySelector(
        `[data-day="${new Date(`${from}T12:00:00`).toLocaleDateString()}"][data-range-start="true"]`,
      ),
    ).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Применить' }))
    expect(onApply).toHaveBeenCalledWith({ from, to })
    expect(screen.queryByRole('grid')).not.toBeInTheDocument()
  })

  it('uses one month on narrow screens and resets the applied filter', async () => {
    mockViewport(true)
    const user = userEvent.setup()
    const onApply = vi.fn<(period: { from: string; to: string } | null) => void>()
    render(<AuditFilter onApply={onApply} value={{ from: '2026-09-02', to: '2026-09-08' }} />)
    expect(screen.getByRole('button', { name: /Период:/ })).toHaveTextContent('с 2 по 8 сентября')
    await user.click(screen.getByRole('button', { name: /Период:/ }))
    expect(screen.getAllByRole('grid')).toHaveLength(1)
    await user.click(screen.getByRole('button', { name: 'Сбросить' }))
    expect(onApply).toHaveBeenCalledWith(null)
  })
})
