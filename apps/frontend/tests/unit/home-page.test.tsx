import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { AccessDeniedPage } from '@/routes/_layout/index'

describe('AccessDeniedPage', () => {
  it('informs a signed-in user that no sections are available', () => {
    render(<AccessDeniedPage />)

    expect(screen.getByRole('heading', { level: 1, name: 'Нет доступа' })).toBeInTheDocument()
    expect(
      screen.getByText('Для вашей учётной записи пока нет доступных разделов.'),
    ).toBeInTheDocument()
  })
})

afterEach(() => {
  cleanup()
})
