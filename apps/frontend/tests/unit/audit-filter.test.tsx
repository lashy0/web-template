import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'

import { AuditFilter } from '@/components/Common/AuditFilter'

describe('AuditFilter', () => {
  afterEach(cleanup)

  it('restores the applied period after closing changed dates without applying', async () => {
    const user = userEvent.setup()

    render(
      <AuditFilter onApply={() => undefined} value={{ from: '2026-08-10', to: '2026-08-12' }} />,
    )

    await user.click(screen.getByRole('button', { name: /Период:/ }))
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
})
