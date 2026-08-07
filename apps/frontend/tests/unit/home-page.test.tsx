import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { HomePage } from '@/routes/index'

describe('HomePage', () => {
  it('renders the neutral application shell content', () => {
    render(<HomePage />)

    expect(screen.getByRole('heading', { level: 1, name: 'Web App' })).toBeInTheDocument()
    expect(screen.getByText('Ready for the first product flow.')).toBeInTheDocument()
  })
})
