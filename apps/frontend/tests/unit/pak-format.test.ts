import { describe, expect, it } from 'vitest'

import { pakCodeForMessage } from '@/features/paks/pak-format'

describe('pakCodeForMessage', () => {
  it('shortens a long PAK code for a notification', () => {
    expect(pakCodeForMessage('PAK-123456789012345678901234567890123')).toBe(
      'PAK-123456789012345678901234567…',
    )
  })

  it('preserves a short PAK code', () => {
    expect(pakCodeForMessage('PAK-Test')).toBe('PAK-Test')
  })
})
